"""
Rules-based symptom-to-condition triage (decision tree) used by USSD, the web app and the API.

!! CLINICAL / AGRONOMIC CONTENT IN THIS FILE HAS NOT BEEN SIGNED OFF. !!
It must be reviewed and approved by Agritex (crops) and Zimbabwe Veterinary Services
(livestock) before any public launch. Coverage is deliberately small and honest:
crops = maize + sorghum, animals = cattle + poultry. Anything else returns
`known=False` with a "contact your officer" action — never a guess.

Single source of truth: symptom/crop/animal menus (labels AND codes) live here so USSD, API
and web can never disagree about what "symptom 3" means.

Helplines come from settings (VET_SERVICES_CONTACT / AGRITEX_CONTACT). We never ship a
phone number nobody has verified; when unset the text says "your nearest ... office".
"""
from app.core.config import settings

# (code, full label for web/API, short label for USSD)
CROP_SYMPTOMS = [
    ("1", "Yellowing / discoloured leaves", "Yellow leaves"),
    ("2", "Wilting despite watering", "Wilting"),
    ("3", "Chewed leaves / visible pests", "Holes/chewed leaves"),
    ("4", "Grey or white powdery spots", "White/grey powder"),
    ("5", "Stunted growth / weeds around roots", "Stunted growth"),
]
LIVESTOCK_SYMPTOMS = [
    ("1", "Skin nodules / lumps", "Skin lumps"),
    ("2", "Coughing / laboured breathing", "Coughing/breathing"),
    ("3", "Blisters on mouth or feet", "Mouth/foot blisters"),
    ("4", "Lethargy / tick infestation", "Lethargy/ticks"),
    ("5", "Sudden death / bleeding from openings", "Sudden death/bleeding"),
]
# Only what the rules below actually cover.
CROPS = [("1", "Maize"), ("2", "Sorghum / Small grains")]
ANIMALS = [("1", "Cattle"), ("4", "Poultry")]


def vet_contact() -> str:
    n = (settings.VET_SERVICES_CONTACT or "").strip()
    return f"Vet Services {n}" if n else "your nearest Veterinary office"


def agritex_contact() -> str:
    n = (settings.AGRITEX_CONTACT or "").strip()
    return f"Agritex {n}" if n else "your Agritex officer"


class RulesEngine:
    # (symptom_code, crop_code) -> conditions + full action text + short USSD text
    CROP_RULES: dict = {
        ("1", "1"): {"disease1": "Maize Streak Virus", "disease2": "Nitrogen Deficiency",
                     "action": "Remove infected plants. Apply fertiliser. Plant resistant varieties next season.",
                     "ussd": "Remove infected plants; feed with fertiliser."},
        ("1", "2"): {"disease1": "Ergot", "disease2": "Leaf Rust",
                     "action": "Remove infected heads. Apply recommended fungicide.",
                     "ussd": "Remove infected heads; use fungicide."},
        ("2", "1"): {"disease1": "Drought Stress", "disease2": "Root Rot",
                     "action": "Check soil moisture. Improve drainage. Contact Agritex.",
                     "ussd": "Check soil moisture and drainage."},
        ("3", "1"): {"disease1": "Fall Armyworm", "disease2": "Spotted Stem Borer",
                     "action": "Apply recommended pesticide within 24h. Check neighbouring fields.",
                     "ussd": "Spray recommended pesticide within 24h."},
        ("4", "1"): {"disease1": "Gray Leaf Spot", "disease2": "Powdery Mildew",
                     "action": "Apply fungicide. Improve air circulation. Rotate crops.",
                     "ussd": "Apply fungicide; rotate crops."},
        ("5", "1"): {"disease1": "Striga (Witchweed)", "disease2": "Soil Compaction",
                     "action": "Hand-weed Striga. Apply herbicide. Use resistant varieties.",
                     "ussd": "Hand-weed Striga; use resistant seed."},
    }

    LIVESTOCK_RULES: dict = {
        ("1", "1"): {"disease": "Lumpy Skin Disease", "notifiable": True,
                     "action": "ISOLATE immediately. Vaccinate herd. Report to {vet}.",
                     "ussd": "ISOLATE animal. Report to {vet}."},
        ("2", "1"): {"disease": "Bovine Respiratory Disease", "notifiable": False,
                     "action": "Isolate sick animals. Provide shelter. Contact {vet}.",
                     "ussd": "Isolate sick animals; contact {vet}."},
        ("3", "1"): {"disease": "Foot and Mouth Disease", "notifiable": True,
                     "action": "NOTIFIABLE: Restrict movement. Report to {vet} immediately.",
                     "ussd": "Restrict movement. Report to {vet} NOW."},
        ("4", "1"): {"disease": "Anaplasmosis", "notifiable": False,
                     "action": "Treat only on {vet} advice (antibiotics need a vet). Control ticks.",
                     "ussd": "Control ticks; ask {vet} about treatment."},
        ("5", "1"): {"disease": "Anthrax", "notifiable": True,
                     "action": "NOTIFIABLE EMERGENCY: Do not touch or open the carcass. Contact {vet} NOW.",
                     "ussd": "Do NOT touch carcass. Contact {vet} NOW."},
        ("1", "4"): {"disease": "Fowl Pox", "notifiable": False,
                     "action": "Isolate affected birds. Improve housing. Ask {vet} about vaccination.",
                     "ussd": "Isolate birds; ask {vet} about vaccine."},
        ("2", "4"): {"disease": "Newcastle Disease", "notifiable": False,
                     "action": "Isolate sick birds and disinfect housing. Ask {vet} about vaccination and reporting.",
                     "ussd": "Isolate birds; contact {vet}."},
    }

    def diagnose_crop(self, symptom: str, crop: str) -> dict:
        rule = self.CROP_RULES.get((symptom, crop))
        if rule:
            return {**rule, "known": True}
        return {"disease1": "Unknown condition", "disease2": None, "known": False,
                "action": f"No guidance for this combination yet. Contact {agritex_contact()} for a field assessment.",
                "ussd": f"No guidance yet. Ask {agritex_contact()}."}

    def diagnose_livestock(self, symptom: str, animal: str) -> dict:
        rule = self.LIVESTOCK_RULES.get((symptom, animal))
        if rule:
            v = vet_contact()
            return {**rule, "action": rule["action"].format(vet=v), "ussd": rule["ussd"].format(vet=v), "known": True}
        return {"disease": "Unknown condition", "notifiable": False, "known": False,
                "action": f"No guidance for this combination yet. Contact {vet_contact()} for assessment.",
                "ussd": f"No guidance yet. Contact {vet_contact()}."}
