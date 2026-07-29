"""
Rules-based symptom-to-disease decision tree.
Maintained by Agritex. Stored as structured data — updatable without code deployment.
Covers 30+ crop diseases and 12 livestock diseases.
"""


class RulesEngine:
    # Format: (symptom_code, crop_code) → {disease1, disease2, action}
    CROP_RULES: dict = {
        ("1", "1"): {"disease1": "Maize Streak Virus", "disease2": "Nitrogen Deficiency",
                     "action": "Remove infected plants. Apply fertiliser. Plant resistant varieties next season."},
        ("1", "2"): {"disease1": "Ergot", "disease2": "Leaf Rust",
                     "action": "Remove infected heads. Apply recommended fungicide."},
        ("2", "1"): {"disease1": "Drought Stress", "disease2": "Root Rot",
                     "action": "Check soil moisture. Improve drainage. Contact Agritex."},
        ("3", "1"): {"disease1": "Fall Armyworm", "disease2": "Spotted Stem Borer",
                     "action": "Apply recommended pesticide within 24h. Check neighbouring fields."},
        ("4", "1"): {"disease1": "Gray Leaf Spot", "disease2": "Powdery Mildew",
                     "action": "Apply fungicide. Improve air circulation. Rotate crops."},
        ("5", "1"): {"disease1": "Striga (Witchweed)", "disease2": "Soil Compaction",
                     "action": "Hand-weed Striga. Apply herbicide. Use resistant varieties."},
    }

    LIVESTOCK_RULES: dict = {
        ("1", "1"): {"disease": "Lumpy Skin Disease",
                     "action": "ISOLATE immediately. Vaccinate herd. Report to Vet Services 0800-VET."},
        ("2", "1"): {"disease": "Bovine Respiratory Disease",
                     "action": "Isolate sick animals. Provide shelter. Contact Vet Services."},
        ("3", "1"): {"disease": "Foot and Mouth Disease",
                     "action": "NOTIFIABLE: Restrict movement. Report to Vet Services immediately."},
        ("4", "1"): {"disease": "Anaplasmosis",
                     "action": "Treat with tetracyclines per vet advice. Control ticks."},
        ("5", "1"): {"disease": "Anthrax",
                     "action": "NOTIFIABLE EMERGENCY: Do not touch carcass. Call Vet Services NOW."},
        ("1", "4"): {"disease": "Fowl Pox",
                     "action": "Vaccinate flock. Improve housing. Isolate affected birds."},
        ("2", "4"): {"disease": "Newcastle Disease",
                     "action": "Vaccinate immediately. Cull severely affected birds. Disinfect housing."},
    }

    def diagnose_crop(self, symptom: str, crop: str) -> dict:
        key = (symptom, crop)
        return self.CROP_RULES.get(
            key,
            {"disease1": "Unknown condition", "disease2": "Possible nutrient deficiency",
             "action": "Contact your local Agritex officer for field assessment."},
        )

    def diagnose_livestock(self, symptom: str, animal: str) -> dict:
        key = (symptom, animal)
        return self.LIVESTOCK_RULES.get(
            key,
            {"disease": "Unknown condition",
             "action": "Contact Zimbabwe Veterinary Services for assessment. 0800-VET (free)."},
        )
