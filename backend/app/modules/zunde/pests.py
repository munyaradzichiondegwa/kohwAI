"""Controlled vocabulary for pest sightings.

Free-text species names ("Fall Armyworm" vs "fall army worm") never match each other, so the
outbreak rule (3 reports of the same species in a district) could never fire reliably.
"""
from typing import Annotated
from pydantic import AfterValidator

PEST_SPECIES = [
    "Fall Armyworm", "African Armyworm", "Spotted Stem Borer", "Cutworm", "Aphids",
    "Red Locust", "Quelea (birds)", "Termites", "Other",
]
_CANON = {s.lower(): s for s in PEST_SPECIES}


def canonical_species(v: str) -> str:
    key = " ".join(v.strip().lower().split())
    if key not in _CANON:
        raise ValueError(f"Unknown pest species '{v}'. Choose one of: {', '.join(PEST_SPECIES)}")
    return _CANON[key]


PestSpecies = Annotated[str, AfterValidator(canonical_species)]
