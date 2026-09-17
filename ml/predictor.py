"""
Prediction service for AgriSense AI

Loads trained models and provides inference. Models are trained
separately (see ml/train_crop_model.py, ml/train_yield_model.py) and
are ONLY loaded here - never retrained during application startup or
on a web request.
"""
import json
import logging
import os
import threading
from typing import Dict, List, Optional

import joblib
import numpy as np

from config.settings import (
    CROP_MODEL_PATH, YIELD_MODEL_PATH, METADATA_PATH, MODEL_DIR,
    CROP_FEATURES, YIELD_FEATURES, CROPS, CROP_EMOJIS
)
from ml.explainability import explain_crop, get_feature_importance

log = logging.getLogger(__name__)

_lock = threading.Lock()


class ModelBundle:
    """Container for loaded models and metadata."""

    def __init__(self):
        self.crop_model = None
        self.yield_model = None
        self.crop_stats = {}
        self.metadata = {}
        self.loaded = False
        self.load_errors = []


_models = ModelBundle()


def get_models() -> ModelBundle:
    """Get the loaded model bundle (thread-safe singleton access)."""
    global _models
    if not _models.loaded:
        with _lock:
            if not _models.loaded:
                load_models()
    return _models


def load_models() -> ModelBundle:
    """
    Load trained models from disk. Does NOT train models.
    
    If models are missing, sets appropriate error state that routes
    can check and report to the user (rather than crashing).
    """
    global _models
    bundle = ModelBundle()

    # Load crop model
    if os.path.exists(CROP_MODEL_PATH):
        try:
            bundle.crop_model = joblib.load(CROP_MODEL_PATH)
            log.info(f"Loaded crop model from {CROP_MODEL_PATH}")
        except Exception as e:
            error_msg = f"Failed to load crop model: {e}"
            log.error(error_msg)
            bundle.load_errors.append(error_msg)
    else:
        error_msg = f"Crop model not found at {CROP_MODEL_PATH}. Run: python -m ml.train_crop_model"
        log.warning(error_msg)
        bundle.load_errors.append(error_msg)

    # Load yield model
    if os.path.exists(YIELD_MODEL_PATH):
        try:
            bundle.yield_model = joblib.load(YIELD_MODEL_PATH)
            log.info(f"Loaded yield model from {YIELD_MODEL_PATH}")
        except Exception as e:
            error_msg = f"Failed to load yield model: {e}"
            log.error(error_msg)
            bundle.load_errors.append(error_msg)
    else:
        error_msg = f"Yield model not found at {YIELD_MODEL_PATH}. Run: python -m ml.train_yield_model"
        log.warning(error_msg)
        bundle.load_errors.append(error_msg)

    # Load crop stats (for explanations)
    crop_stats_path = os.path.join(MODEL_DIR, "crop_stats.json")
    if os.path.exists(crop_stats_path):
        try:
            with open(crop_stats_path, "r") as f:
                bundle.crop_stats = json.load(f)
            log.info("Loaded crop statistics")
        except Exception as e:
            log.warning(f"Failed to load crop stats: {e}")

    # Load metadata
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r") as f:
                bundle.metadata = json.load(f)
            log.info("Loaded model metadata")
        except Exception as e:
            log.warning(f"Failed to load metadata: {e}")

    bundle.loaded = True
    _models = bundle
    return bundle


def reload_models() -> ModelBundle:
    """Force reload of models (e.g., after retraining)."""
    global _models
    with _lock:
        _models = ModelBundle()
        return load_models()


def is_ready() -> bool:
    """Check if models are loaded and ready for prediction."""
    bundle = get_models()
    return bundle.crop_model is not None and bundle.yield_model is not None


def get_status() -> Dict:
    """Get model status for health check."""
    bundle = get_models()
    return {
        "crop_model_loaded": bundle.crop_model is not None,
        "yield_model_loaded": bundle.yield_model is not None,
        "crop_stats_loaded": bool(bundle.crop_stats),
        "ready": is_ready(),
        "errors": bundle.load_errors,
        "metadata": bundle.metadata
    }


def predict_recommendations(
    feature_values: Dict[str, float],
    area_ha: float,
    irrigation: str,
    top_n: int = 5
) -> Dict:
    """
    Run crop recommendation and yield prediction.
    
    Args:
        feature_values: dict with N, P, K, temperature, humidity, ph, rainfall
        area_ha: farm area in hectares
        irrigation: "none", "partial", or "full"
        top_n: number of top crops to return
    
    Returns:
        Dict with ranked_crops and feature_importance
    """
    bundle = get_models()

    if bundle.crop_model is None or bundle.yield_model is None:
        raise RuntimeError(
            "Models not available. Please run training scripts: "
            "python -m ml.train_crop_model && python -m ml.train_yield_model"
        )

    X = np.array([[feature_values[f] for f in CROP_FEATURES]])

    proba = bundle.crop_model.predict_proba(X)[0]
    classes = list(bundle.crop_model.classes_)
    ranked_idx = np.argsort(proba)[::-1][:top_n]

    irrigation_map = {"none": 0, "partial": 1, "full": 2}
    irrigation_numeric = irrigation_map.get(irrigation, 1)

    results = []
    for idx in ranked_idx:
        crop = classes[idx]
        suitability_pct = round(float(proba[idx]) * 100, 1)

        crop_idx = CROPS.index(crop) if crop in CROPS else 0
        yield_features = feature_values.copy()
        yield_features["crop_index"] = crop_idx
        yield_features["irrigation"] = irrigation_numeric

        yX = np.array([[yield_features[f] for f in YIELD_FEATURES]])
        predicted_yield = float(bundle.yield_model.predict(yX)[0])
        predicted_yield = max(predicted_yield, 0.0)

        explanation = explain_crop(crop, feature_values, bundle.crop_stats)

        # Calculate defensible yield range (based on model uncertainty)
        # Use tree variance from the RandomForest for a rough range
        try:
            tree_predictions = np.array([
                tree.predict(yX)[0] for tree in bundle.yield_model.estimators_
            ])
            yield_std = float(np.std(tree_predictions))
            yield_low = max(0, predicted_yield - yield_std)
            yield_high = predicted_yield + yield_std
        except Exception:
            yield_low = predicted_yield * 0.85
            yield_high = predicted_yield * 1.15

        results.append({
            "crop": crop,
            "icon": CROP_EMOJIS.get(crop, "🌱"),
            "suitability_pct": suitability_pct,
            "predicted_yield_t_per_ha": round(predicted_yield, 2),
            "yield_range_t_per_ha": {
                "low": round(yield_low, 2),
                "high": round(yield_high, 2)
            },
            "predicted_total_production_t": round(predicted_yield * area_ha, 2),
            "yield_unit": "tonnes/hectare",
            "explanation": explanation,
        })

    feature_importance = get_feature_importance(bundle.crop_model, CROP_FEATURES)

    return {
        "ranked_crops": results,
        "feature_importance": feature_importance,
        "top_crop": results[0] if results else None
    }


def predict_for_specific_crop(
    feature_values: Dict[str, float],
    crop: str,
    area_ha: float,
    irrigation: str
) -> Optional[Dict]:
    """
    Used by Current Farm Mode: evaluate suitability/yield for a SPECIFIC
    crop the farmer already has, rather than ranking all crops.

    Returns None if the crop is not one the model was trained on (caller
    is expected to have already checked config.crop_master.is_crop_supported
    and to show an "insufficient validated data" message instead of calling
    this function in that case).
    """
    bundle = get_models()
    if bundle.crop_model is None or bundle.yield_model is None:
        raise RuntimeError(
            "Models not available. Please run training scripts: "
            "python -m ml.train_crop_model && python -m ml.train_yield_model"
        )

    classes = list(bundle.crop_model.classes_)
    if crop not in classes:
        return None

    X = np.array([[feature_values[f] for f in CROP_FEATURES]])
    proba = bundle.crop_model.predict_proba(X)[0]
    crop_idx_in_classes = classes.index(crop)
    suitability_pct = round(float(proba[crop_idx_in_classes]) * 100, 1)

    irrigation_map = {"none": 0, "partial": 1, "full": 2}
    irrigation_numeric = irrigation_map.get(irrigation, 1)
    crop_idx = CROPS.index(crop) if crop in CROPS else 0

    yield_features = feature_values.copy()
    yield_features["crop_index"] = crop_idx
    yield_features["irrigation"] = irrigation_numeric
    yX = np.array([[yield_features[f] for f in YIELD_FEATURES]])
    predicted_yield = max(float(bundle.yield_model.predict(yX)[0]), 0.0)

    explanation = explain_crop(crop, feature_values, bundle.crop_stats)

    return {
        "crop": crop,
        "icon": CROP_EMOJIS.get(crop, "🌱"),
        "suitability_pct": suitability_pct,
        "predicted_yield_t_per_ha": round(predicted_yield, 2),
        "predicted_total_production_t": round(predicted_yield * area_ha, 2),
        "yield_unit": "tonnes/hectare",
        "explanation": explanation,
    }
