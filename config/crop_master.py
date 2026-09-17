"""
AgriSense AI - Crop Master Registry
=====================================

This is the single source of truth for which crops the system can make
VALIDATED recommendations/yield estimates for, and which it cannot.

CRITICAL HONESTY RULE (per project requirements):
The underlying ML model is trained on the public Crop Recommendation
Dataset, which covers 22 crops. Several crops that Andhra Pradesh and
Telangana farmers actually grow - Chilli, Tobacco, Wheat, Sugarcane,
Turmeric, Groundnut - are NOT present in that dataset.

Rather than silently mapping these to a similar crop, aggregating them
under a generic category, or fabricating plausible-looking numbers,
this registry marks them explicitly as UNSUPPORTED. The application
must show a clear "insufficient validated data" message for these
crops rather than a prediction.

data_availability values:
    HIGH        - Strong representation in the training dataset
    MODERATE    - Present but with fewer observations
    UNSUPPORTED - Not present in the training dataset at all;
                  no recommendation or yield estimate is generated
"""
from typing import Dict, List, Optional

# Crops actually present in the Crop Recommendation Dataset used to train
# ml/train_crop_model.py (verified against the trained model's class list).
_DATASET_CROPS = {
    "rice": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "maize": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "cotton": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "jute": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "coconut": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "coffee": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "papaya": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "orange": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "apple": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "muskmelon": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "watermelon": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "grapes": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "mango": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "banana": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "pomegranate": {"observation_count_est": "~100 rows", "data_availability": "HIGH"},
    "lentil": {"observation_count_est": "~100 rows", "data_availability": "MODERATE"},
    "blackgram": {"observation_count_est": "~100 rows", "data_availability": "MODERATE"},
    "mungbean": {"observation_count_est": "~100 rows", "data_availability": "MODERATE"},
    "mothbeans": {"observation_count_est": "~100 rows", "data_availability": "MODERATE"},
    "pigeonpeas": {"observation_count_est": "~100 rows", "data_availability": "MODERATE"},
    "kidneybeans": {"observation_count_est": "~100 rows", "data_availability": "MODERATE"},
    "chickpea": {"observation_count_est": "~100 rows", "data_availability": "MODERATE"},
}

# Crops the project brief mandates for AP/Telangana relevance, that are NOT
# present in the training dataset. Listed explicitly so the UI can show
# them (farmers will ask about them) while being fully honest that no
# validated prediction exists yet.
_UNSUPPORTED_MANDATORY_CROPS = {
    "chilli": {
        "reason": "Not present in the crop-recommendation training dataset used by this system.",
        "real_world_data_note": "District-level area/production/yield statistics for Chilli exist in "
                                 "government sources (e.g. Directorate of Economics & Statistics, "
                                 "data.gov.in), but have not yet been integrated into a validated "
                                 "recommendation/yield model for this application.",
    },
    "tobacco": {
        "reason": "Not present in the crop-recommendation training dataset used by this system.",
        "real_world_data_note": "Government production statistics exist but are not yet integrated "
                                 "into a validated model here.",
    },
    "wheat": {
        "reason": "Not present in the crop-recommendation training dataset used by this system.",
        "real_world_data_note": "Government production statistics exist but are not yet integrated "
                                 "into a validated model here.",
    },
    "sugarcane": {
        "reason": "Not present in the crop-recommendation training dataset used by this system.",
        "real_world_data_note": "Government production statistics exist but are not yet integrated "
                                 "into a validated model here.",
    },
    "turmeric": {
        "reason": "Not present in the crop-recommendation training dataset used by this system.",
        "real_world_data_note": "Government production statistics exist but are not yet integrated "
                                 "into a validated model here.",
    },
    "groundnut": {
        "reason": "Not present in the crop-recommendation training dataset used by this system.",
        "real_world_data_note": "Government production statistics exist but are not yet integrated "
                                 "into a validated model here.",
    },
}

CROP_DISPLAY_NAMES = {
    "rice": "Rice", "maize": "Maize (Corn)", "cotton": "Cotton", "jute": "Jute",
    "coconut": "Coconut", "coffee": "Coffee", "papaya": "Papaya", "orange": "Orange",
    "apple": "Apple", "muskmelon": "Muskmelon", "watermelon": "Watermelon",
    "grapes": "Grapes", "mango": "Mango", "banana": "Banana", "pomegranate": "Pomegranate",
    "lentil": "Lentil", "blackgram": "Black Gram", "mungbean": "Mung Bean",
    "mothbeans": "Moth Beans", "pigeonpeas": "Pigeon Pea", "kidneybeans": "Kidney Beans",
    "chickpea": "Chickpea", "chilli": "Chilli", "tobacco": "Tobacco", "wheat": "Wheat",
    "sugarcane": "Sugarcane", "turmeric": "Turmeric", "groundnut": "Groundnut",
}

CROP_CATEGORY = {
    "rice": "cereal", "maize": "cereal", "wheat": "cereal",
    "cotton": "fiber", "jute": "fiber",
    "chilli": "horticulture", "turmeric": "horticulture", "tobacco": "commercial",
    "sugarcane": "commercial", "groundnut": "oilseed",
    "coconut": "plantation", "coffee": "plantation", "mango": "horticulture",
    "banana": "horticulture", "papaya": "horticulture", "orange": "horticulture",
    "apple": "horticulture", "muskmelon": "horticulture", "watermelon": "horticulture",
    "grapes": "horticulture", "pomegranate": "horticulture",
    "lentil": "pulse", "blackgram": "pulse", "mungbean": "pulse", "mothbeans": "pulse",
    "pigeonpeas": "pulse", "kidneybeans": "pulse", "chickpea": "pulse",
}


def build_crop_master() -> Dict[str, Dict]:
    """Build the complete crop master registry."""
    registry = {}

    for crop_id, meta in _DATASET_CROPS.items():
        registry[crop_id] = {
            "crop_id": crop_id,
            "display_name": CROP_DISPLAY_NAMES.get(crop_id, crop_id.capitalize()),
            "category": CROP_CATEGORY.get(crop_id, "other"),
            "data_availability": meta["data_availability"],
            "supported_for_recommendation": True,
            "supported_for_yield": True,
            "source": "Public Crop Recommendation Dataset (N, P, K, temperature, humidity, pH, rainfall)",
            "observation_count_est": meta["observation_count_est"],
        }

    for crop_id, meta in _UNSUPPORTED_MANDATORY_CROPS.items():
        registry[crop_id] = {
            "crop_id": crop_id,
            "display_name": CROP_DISPLAY_NAMES.get(crop_id, crop_id.capitalize()),
            "category": CROP_CATEGORY.get(crop_id, "other"),
            "data_availability": "UNSUPPORTED",
            "supported_for_recommendation": False,
            "supported_for_yield": False,
            "reason": meta["reason"],
            "real_world_data_note": meta["real_world_data_note"],
        }

    return registry


CROP_MASTER = build_crop_master()

SUPPORTED_CROP_IDS = [c for c, v in CROP_MASTER.items() if v["supported_for_recommendation"]]
UNSUPPORTED_CROP_IDS = [c for c, v in CROP_MASTER.items() if not v["supported_for_recommendation"]]


def get_crop_info(crop_id: str) -> Optional[Dict]:
    """Get crop master info for a given crop id."""
    return CROP_MASTER.get(crop_id.lower())


def is_crop_supported(crop_id: str) -> bool:
    """Check whether a crop has validated recommendation/yield support."""
    info = get_crop_info(crop_id)
    return bool(info and info.get("supported_for_recommendation"))


def list_crops(category: Optional[str] = None) -> List[Dict]:
    """List all crops in the master registry, optionally filtered by category."""
    crops = list(CROP_MASTER.values())
    if category:
        crops = [c for c in crops if c.get("category") == category]
    return sorted(crops, key=lambda c: c["display_name"])
