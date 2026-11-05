"""Export the triage rules to shared/rules/rules.json — the single source of truth for web and mobile.

    cd backend && python scripts/export_rules.py          # regenerate
    cd backend && python scripts/export_rules.py --check  # exit 1 if the committed file is stale (CI runs this via pytest)

The Python RulesEngine (app/modules/ussd/rules_engine.py) stays authoritative: USSD, the API and the
offline clients must give the same answer. Contact placeholders ({vet}) are resolved at runtime by each client.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.modules.ussd.rules_engine import RulesEngine, CROP_SYMPTOMS, LIVESTOCK_SYMPTOMS, CROPS, ANIMALS  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "shared" / "rules" / "rules.json"


def build() -> dict:
    sym = lambda rows: [{"code": c, "label": full, "short": short} for c, full, short in rows]
    opt = lambda rows: [{"code": c, "label": label} for c, label in rows]
    key = lambda k: f"{k[0]}|{k[1]}"            # "<symptom>|<crop-or-animal>"
    return {
        "_generated": "DO NOT EDIT BY HAND — run backend/scripts/export_rules.py",
        "cropSymptoms": sym(CROP_SYMPTOMS), "livestockSymptoms": sym(LIVESTOCK_SYMPTOMS),
        "cropTypes": opt(CROPS), "animalTypes": opt(ANIMALS),
        "cropRules": {key(k): v for k, v in RulesEngine.CROP_RULES.items()},
        "livestockRules": {key(k): v for k, v in RulesEngine.LIVESTOCK_RULES.items()},
    }


def render() -> str:
    return json.dumps(build(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    if "--check" in sys.argv:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == render()
        print("rules.json is up to date" if ok else "rules.json is STALE — run: python scripts/export_rules.py")
        sys.exit(0 if ok else 1)
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT}")
