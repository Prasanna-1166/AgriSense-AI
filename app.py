#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AgriSense AI - Agricultural Decision-Support Platform
=========================================================

Main Flask application entry point.

This module ONLY loads pre-trained models and wires up routes - it never
retrains models on startup. To train models, run:

    python -m ml.train_crop_model
    python -m ml.train_yield_model

Environment variables (all optional):
    AGRISENSE_HOST           Host to bind to (default: 127.0.0.1)
    AGRISENSE_PORT           Port to bind to (default: 5000)
    AGRISENSE_DEBUG          Set to "1" to enable Flask debug mode
    AGRISENSE_FORCE_RETRAIN  Set to "1" to force retraining on startup (not recommended)

Run with:
    python app.py
"""
import logging
import os
import sys

from flask import Flask, render_template, jsonify, request

from config.settings import (
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG, APP_NAME, APP_VERSION, FORCE_RETRAIN
)
from utils.logging_config import setup_logging

# Setup logging first
setup_logging()
log = logging.getLogger(__name__)


def create_app():
    """Application factory for AgriSense AI."""
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload limit (soil reports)

    # Register blueprints
    from routes.health import health_bp
    from routes.location import location_bp
    from routes.environment import environment_bp
    from routes.prediction import prediction_bp
    from routes.history import history_bp
    from routes.crops import crops_bp
    from routes.soil import soil_bp
    from routes.farm import farm_bp
    from routes.current_farm import current_farm_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(location_bp)
    app.register_blueprint(environment_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(crops_bp)
    app.register_blueprint(soil_bp)
    app.register_blueprint(farm_bp)
    app.register_blueprint(current_farm_bp)

    # Frontend route
    @app.route("/")
    def index():
        return render_template("index.html", app_name=APP_NAME, app_version=APP_VERSION)

    # Global error handlers - never show stack traces to normal users
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "error": {"code": "NOT_FOUND", "message": "Endpoint not found."}
            }), 404
        return render_template("index.html", app_name=APP_NAME, app_version=APP_VERSION), 200

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({
            "success": False,
            "error": {"code": "FILE_TOO_LARGE", "message": "Uploaded file is too large."}
        }), 413

    @app.errorhandler(500)
    def server_error(e):
        log.error(f"Internal server error: {e}")
        return jsonify({
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred. Please try again."}
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        log.error(f"Unhandled exception: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {"code": "UNEXPECTED_ERROR", "message": "An unexpected error occurred. Please try again."}
        }), 500

    return app


def check_models_status():
    """Check and report model status at startup without training."""
    from ml.predictor import get_status
    status = get_status()

    log.info("=" * 60)
    log.info(f"{APP_NAME} v{APP_VERSION} - Model Status")
    log.info("=" * 60)
    log.info(f"Crop model loaded:  {status['crop_model_loaded']}")
    log.info(f"Yield model loaded: {status['yield_model_loaded']}")

    if not status["ready"]:
        log.warning("-" * 60)
        log.warning("MODELS NOT READY. Predictions will fail until trained.")
        log.warning("Run these commands to train the models:")
        log.warning("  python -m ml.train_crop_model")
        log.warning("  python -m ml.train_yield_model")
        log.warning("-" * 60)
    else:
        log.info("Models ready for predictions.")

    from config.crop_master import SUPPORTED_CROP_IDS, UNSUPPORTED_CROP_IDS
    log.info(f"Crop Master: {len(SUPPORTED_CROP_IDS)} supported crops, "
              f"{len(UNSUPPORTED_CROP_IDS)} flagged as data-unavailable "
              f"({', '.join(UNSUPPORTED_CROP_IDS)})")
    log.info("=" * 60)

    return status["ready"]


app = create_app()

if __name__ == "__main__":
    if FORCE_RETRAIN:
        log.warning("AGRISENSE_FORCE_RETRAIN=1 detected. Training models now...")
        from ml.train_crop_model import train as train_crop
        from ml.train_yield_model import train as train_yield
        train_crop()
        train_yield()
        from ml.predictor import reload_models
        reload_models()

    check_models_status()

    log.info(f"Starting {APP_NAME} v{APP_VERSION} on http://{FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
