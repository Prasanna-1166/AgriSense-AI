"""
Prediction history routes for AgriSense AI

Stores recent predictions locally (simple JSON-file-based storage,
per the "don't introduce a database unless it materially improves
the project" guidance - SQLite would be equivalent complexity here,
so a simple JSON store is used for this lightweight history feature).
"""
import logging
from flask import Blueprint, jsonify, request

from utils.cache import PredictionHistory
from config.settings import DATA_DIR
import os

log = logging.getLogger(__name__)

history_bp = Blueprint("history", __name__)

_history_path = os.path.join(DATA_DIR, "prediction_history.json")
_history = PredictionHistory(_history_path)


@history_bp.route("/api/history", methods=["GET"])
def get_history():
    """Get recent prediction history."""
    limit = request.args.get("limit", default=20, type=int)
    limit = max(1, min(limit, 100))

    predictions = _history.get_recent(limit)
    stats = _history.get_stats()

    return jsonify({
        "predictions": list(reversed(predictions)),  # most recent first
        "stats": stats
    }), 200


@history_bp.route("/api/history", methods=["POST"])
def add_history():
    """Add a prediction to history."""
    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify({"error": "No prediction data provided."}), 400

    # Store a condensed version of the prediction
    entry = {
        "id": data.get("prediction_id"),
        "timestamp": data.get("timestamp"),
        "location": data.get("location"),
        "mode": data.get("mode"),
        "recommended_crop": data.get("top_crop", {}).get("crop") if data.get("top_crop") else None,
        "suitability_pct": data.get("top_crop", {}).get("suitability_pct") if data.get("top_crop") else None,
        "estimated_yield": data.get("top_crop", {}).get("predicted_yield_t_per_ha") if data.get("top_crop") else None,
        "farm_area_ha": data.get("farm", {}).get("area_ha"),
        "total_production": data.get("top_crop", {}).get("predicted_total_production_t") if data.get("top_crop") else None,
        "data_quality": data.get("data_quality", {}).get("overall") if data.get("data_quality") else None,
    }

    success = _history.add(entry)

    if success:
        return jsonify({"status": "saved", "entry": entry}), 201
    else:
        return jsonify({"error": "Failed to save prediction to history."}), 500


@history_bp.route("/api/history/<prediction_id>", methods=["DELETE"])
def delete_history_item(prediction_id):
    """Delete a specific prediction from history."""
    success = _history.delete(prediction_id)

    if success:
        return jsonify({"status": "deleted", "id": prediction_id}), 200
    else:
        return jsonify({"error": "Prediction not found in history."}), 404


@history_bp.route("/api/history", methods=["DELETE"])
def clear_history():
    """Clear all prediction history."""
    success = _history.clear()

    if success:
        return jsonify({"status": "cleared"}), 200
    else:
        return jsonify({"error": "Failed to clear history."}), 500
