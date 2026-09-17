"""
Explainability module for AgriSense AI

Provides "Why this crop?" explanations and feature importance analysis,
strictly derived from the actual trained model - never fabricated.
"""
import logging
import numpy as np
from typing import Dict, List, Optional

from config.settings import CROP_FEATURES, FEATURE_LABELS

log = logging.getLogger(__name__)


def explain_crop(crop: str, feature_values: Dict[str, float], crop_stats: Dict) -> Dict:
    """
    Build a human-readable 'why this crop' checklist and limiting factor,
    comparing input feature values against that crop's typical (mean +/- std)
    range from the actual training data.

    This never invents explanations disconnected from the model - all
    comparisons are drawn directly from computed statistics of the real
    training dataset.
    """
    stats = crop_stats.get(crop)
    if not stats:
        return {"checklist": [], "limiting_factor": None}

    checklist = []
    worst_feat, worst_z = None, 0.0

    for feat in CROP_FEATURES:
        mu = stats[feat]["mean"]
        sigma = max(stats[feat]["std"], 0.01)  # avoid div by zero
        z = abs((feature_values[feat] - mu) / sigma)
        label = FEATURE_LABELS[feat]

        if z <= 1.0:
            checklist.append({
                "ok": True,
                "text": f"Suitable {label.lower()}",
                "feature": feat,
                "z_score": round(z, 2)
            })
        elif z <= 2.0:
            checklist.append({
                "ok": None,
                "text": f"Borderline {label.lower()} - a bit outside the typical range",
                "feature": feat,
                "z_score": round(z, 2)
            })
        else:
            checklist.append({
                "ok": False,
                "text": f"{label} is well outside this crop's typical range",
                "feature": feat,
                "z_score": round(z, 2)
            })

        if z > worst_z:
            worst_z, worst_feat = z, feat

    limiting_factor = None
    if worst_feat is not None and worst_z > 1.0:
        mu = stats[worst_feat]["mean"]
        direction = "higher" if feature_values[worst_feat] < mu else "lower"
        limiting_factor = {
            "feature": worst_feat,
            "label": FEATURE_LABELS[worst_feat],
            "text": f"{FEATURE_LABELS[worst_feat]} is notably {direction} than what this crop typically prefers.",
            "z_score": round(worst_z, 2)
        }

    return {"checklist": checklist, "limiting_factor": limiting_factor}


def get_feature_importance(model, feature_names: List[str] = None) -> List[Dict]:
    """
    Extract feature importance directly from the trained model.
    Never invents importance values disconnected from the model.
    """
    if feature_names is None:
        feature_names = CROP_FEATURES

    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return []

    total = float(np.sum(importances)) or 1.0
    feature_importance = []

    for feat, imp in sorted(zip(feature_names, importances), key=lambda t: -t[1]):
        label = FEATURE_LABELS.get(feat, feat)
        feature_importance.append({
            "feature": feat,
            "label": label,
            "importance_pct": round(float(imp) / total * 100, 1)
        })

    return feature_importance


def generate_farm_insights(
    crop: str,
    suitability_pct: float,
    explanation: Dict,
    water_info: Dict,
    data_quality: Dict
) -> List[Dict]:
    """
    Generate actionable insights based on prediction results.
    
    Insights are phrased as recommendations/indicators, not guarantees,
    and never provide unsafe or overly specific agronomic instructions.
    """
    insights = []

    # Suitability-based insight
    if suitability_pct >= 80:
        insights.append({
            "type": "positive",
            "icon": "✓",
            "text": f"Conditions appear well-suited for {crop.capitalize()} based on the model."
        })
    elif suitability_pct >= 50:
        insights.append({
            "type": "neutral",
            "icon": "◐",
            "text": f"{crop.capitalize()} shows moderate suitability - review the limiting factors below."
        })
    else:
        insights.append({
            "type": "caution",
            "icon": "⚠",
            "text": f"{crop.capitalize()} shows lower suitability for these conditions - consider alternatives."
        })

    # Limiting factor insight
    limiting = explanation.get("limiting_factor")
    if limiting:
        insights.append({
            "type": "caution",
            "icon": "⚠",
            "text": f"{limiting['label']} may be a limiting factor for this crop."
        })

    # Water/irrigation insight
    if water_info:
        insights.append({
            "type": "info",
            "icon": "💧",
            "text": f"Water requirement: {water_info.get('adequacy', 'Review irrigation needs.')}"
        })

    # Data quality insight
    overall_quality = data_quality.get("overall", "moderate")
    if overall_quality == "low":
        insights.append({
            "type": "caution",
            "icon": "⚠",
            "text": "Data confidence is low. Consider providing manual soil test values for more reliable results."
        })
    elif overall_quality == "moderate":
        insights.append({
            "type": "info",
            "icon": "ℹ",
            "text": "Some values are estimated. Soil testing would improve prediction accuracy."
        })

    # Always include the general recommendation
    insights.append({
        "type": "info",
        "icon": "🧪",
        "text": "Consider laboratory soil testing before final planting decisions for best accuracy."
    })

    return insights
