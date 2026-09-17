"""
Health check route for AgriSense AI
"""
from flask import Blueprint, jsonify
from datetime import datetime, timezone

from ml.predictor import get_status
from config.settings import APP_VERSION, APP_NAME

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint - reports model status and app info."""
    model_status = get_status()

    overall_status = "ok" if model_status["ready"] else "degraded"

    return jsonify({
        "status": overall_status,
        "app": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models": model_status,
    }), 200 if model_status["ready"] else 503
