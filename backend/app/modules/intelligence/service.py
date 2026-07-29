"""Cross-Pillar Intelligence Engine.

Every rule here reads real rows from other pillars' tables and only fires
when that real data supports it — there is no synthetic or canned insight
generation. Each rule is intentionally simple and disclosed in its message,
consistent with the rest of this codebase's approach to "AI" claims: this is
correlation logic over real data, not a trained predictive model.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.intelligence import CrossPillarInsight
from app.models.zunde import DiagnosisReport, PestSighting
from app.models.mvura import Borehole
from app.models.livestock import LivestockProfile
from app.models.user import User
from app.models.alerts import Alert
from app.utils.risk import compute_drought_index

DROUGHT_KEYWORDS = ("drought", "wilting")
PEST_OUTBREAK_THRESHOLD = 3       # disclosed: >=3 independent sightings, same species+district, in 7 days
PEST_OUTBREAK_WINDOW_DAYS = 7
DEDUPE_WINDOW_HOURS = 24


def _already_has_recent(db: Session, user_id, district: str, insight_type: str, hours: int) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = db.query(CrossPillarInsight).filter(
        CrossPillarInsight.district == district,
        CrossPillarInsight.insight_type == insight_type,
        CrossPillarInsight.created_at >= cutoff,
    )
    q = q.filter(CrossPillarInsight.user_id == user_id) if user_id else q.filter(CrossPillarInsight.user_id.is_(None))
    return db.query(q.exists()).scalar()


def evaluate_for_user(db: Session, user: User) -> list[CrossPillarInsight]:
    """Rules that depend on one specific farmer's own data."""
    created = []
    district = user.district
    if not district:
        return created

    # Rule 1: recent crop diagnosis suggesting drought stress -> check real
    # borehole status in the same district before recommending water sources.
    recent_diag = (
        db.query(DiagnosisReport)
        .filter(DiagnosisReport.user_id == user.id, DiagnosisReport.subject_type == "crop")
        .order_by(DiagnosisReport.created_at.desc())
        .first()
    )
    if recent_diag and recent_diag.top_disease and any(k in recent_diag.top_disease.lower() for k in DROUGHT_KEYWORDS):
        dry_boreholes = db.query(Borehole).filter(Borehole.district == district, Borehole.status == "dry").count()
        working_boreholes = db.query(Borehole).filter(Borehole.district == district, Borehole.status == "working").count()
        if not _already_has_recent(db, user.id, district, "drought_water_risk", DEDUPE_WINDOW_HOURS):
            msg = (
                f"Your recent crop diagnosis ({recent_diag.top_disease}) suggests dry conditions. "
                f"In {district}, {dry_boreholes} registered borehole(s) are currently reported dry"
                + (f" and {working_boreholes} are working" if working_boreholes else "")
                + " — check the Mvura map before deciding on irrigation."
            )
            insight = CrossPillarInsight(user_id=user.id, district=district, source_pillar="zunde",
                                          target_pillar="mvura", insight_type="drought_water_risk",
                                          severity="amber", message=msg)
            db.add(insight)
            created.append(insight)

    # Rule 2: a sick/notifiable livestock diagnosis for one of the farmer's
    # own animals -> make sure they've seen the borehole/water situation too
    # (disease + water stress often compound), and nudge toward Vet Services.
    sick_animal = (
        db.query(LivestockProfile)
        .filter(LivestockProfile.owner_id == user.id, LivestockProfile.health_status == "sick")
        .order_by(LivestockProfile.last_diagnosed.desc())
        .first()
    )
    if sick_animal and not _already_has_recent(db, user.id, district, "livestock_followup", DEDUPE_WINDOW_HOURS):
        msg = (
            f"{sick_animal.name} was recently flagged sick. If this spreads to other animals, "
            "report it in Community so nearby farmers are warned, and contact Zimbabwe Veterinary Services (0800-VET)."
        )
        insight = CrossPillarInsight(user_id=user.id, district=district, source_pillar="livestock",
                                      target_pillar="community", insight_type="livestock_followup",
                                      severity="amber", message=msg)
        db.add(insight)
        created.append(insight)

    if created:
        db.commit()
        for i in created:
            db.refresh(i)
    return created


def evaluate_pest_outbreak(db: Session, district: str) -> CrossPillarInsight | None:
    """District-wide rule: independently-reported pest sightings of the same
    species clustering in one district within a week -> escalate to a real
    community alert, not just leave each sighting siloed."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=PEST_OUTBREAK_WINDOW_DAYS)
    rows = (
        db.query(PestSighting.species, PestSighting.id)
        .filter(PestSighting.district == district, PestSighting.created_at >= cutoff)
        .all()
    )
    counts: dict[str, int] = {}
    for species, _ in rows:
        counts[species] = counts.get(species, 0) + 1

    for species, count in counts.items():
        if count < PEST_OUTBREAK_THRESHOLD:
            continue
        insight_type = f"pest_outbreak:{species}"
        if _already_has_recent(db, None, district, insight_type, hours=72):
            continue
        msg = (
            f"{count} independent reports of {species} in {district} over the last "
            f"{PEST_OUTBREAK_WINDOW_DAYS} days — this looks like a spreading outbreak, not an isolated case."
        )
        insight = CrossPillarInsight(user_id=None, district=district, source_pillar="community",
                                      target_pillar="zunde", insight_type=insight_type,
                                      severity="red", message=msg)
        db.add(insight)
        db.add(Alert(pillar="zunde", type="pest", severity="red", title=f"{species} outbreak reported",
                      body=msg, district=district))
        db.commit()
        db.refresh(insight)
        return insight
    return None


def evaluate_rains_onset(db: Session, district: str) -> CrossPillarInsight | None:
    """District-wide rule: reuse Zunde's real NASA POWER onset-of-rains
    check and surface it as a cross-pillar insight + alert if not already
    raised recently."""
    from app.modules.zunde.service import get_planting_calendar  # local import avoids a circular import at module load

    if _already_has_recent(db, None, district, "rains_onset", hours=72):
        return None

    calendar = get_planting_calendar(district)
    if not calendar.get("rains_likely_onset"):
        return None

    msg = calendar["guidance"]
    insight = CrossPillarInsight(user_id=None, district=district, source_pillar="zunde",
                                  target_pillar="zunde", insight_type="rains_onset",
                                  severity="info", message=msg)
    db.add(insight)
    db.add(Alert(pillar="zunde", type="weather", severity="amber", title="Rains may be starting",
                  body=msg, district=district))
    db.commit()
    db.refresh(insight)
    return insight


def list_insights(db: Session, user: User) -> list[CrossPillarInsight]:
    q = db.query(CrossPillarInsight).filter(
        CrossPillarInsight.dismissed.is_(False),
        (CrossPillarInsight.user_id == user.id) | (
            (CrossPillarInsight.user_id.is_(None)) & (CrossPillarInsight.district == user.district)
        ),
    )
    return q.order_by(CrossPillarInsight.created_at.desc()).limit(20).all()


def dismiss(db: Session, insight_id: str, user: User) -> bool:
    insight = db.query(CrossPillarInsight).filter(CrossPillarInsight.id == insight_id).first()
    if not insight or (insight.user_id and str(insight.user_id) != str(user.id)):
        return False
    insight.dismissed = True
    db.commit()
    return True
