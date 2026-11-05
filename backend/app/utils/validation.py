"""Shared input validation: one place that knows what a valid district / phone / season is."""
import re
from typing import Annotated

from fastapi import HTTPException, Query, status
from pydantic import AfterValidator

from app.utils.satellite import DISTRICTS

ECOCASH_RE = re.compile(r"^(\+263|0)7[1-9]\d{7}$")


def check_district(v: str) -> str:
    if v not in DISTRICTS:
        raise ValueError(f"Unknown district '{v}'. Valid: {', '.join(sorted(DISTRICTS))}")
    return v


def check_ecocash(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    v = v.replace(" ", "")
    if not ECOCASH_RE.match(v):
        raise ValueError("EcoCash number must be a Zimbabwean mobile number, e.g. 0771234567 or +263771234567")
    return v


def check_season(v: str) -> str:
    m = re.match(r"^(\d{4})-(\d{2})$", v)
    if not m or (int(m.group(1)) + 1) % 100 != int(m.group(2)):
        raise ValueError("Season must look like '2026-27' (second part = following year)")
    return v


# Pydantic field types for request bodies
District = Annotated[str, AfterValidator(check_district)]
Season = Annotated[str, AfterValidator(check_season)]


def district_query(district: str | None = Query(None)) -> str | None:
    """FastAPI dependency: optional ?district= that must be a known district."""
    if district is not None and district not in DISTRICTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown district '{district}'")
    return district


def required_district(district: str = Query(...)) -> str:
    """FastAPI dependency: mandatory ?district= that must be a known district (422 otherwise)."""
    if district not in DISTRICTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Unknown district '{district}'. Valid: {', '.join(sorted(DISTRICTS))}")
    return district


def mask_phone(phone: str | None) -> str | None:
    """Validators see enough to recognise a repeat reporter, not enough to contact them."""
    if not phone:
        return None
    return f"{phone[:5]}***{phone[-2:]}" if len(phone) > 8 else "***"
