"""
AgriSense AI - Soil routes

Manual soil-test validation, and soil-report upload/extraction (PDF/image).
Extraction results are NEVER auto-trusted - the response always requires
frontend confirmation before values are used in a recommendation.
"""
import logging
import os

from flask import Blueprint, jsonify, request

from services.soil_service import validate_manual_soil_values, build_no_soil_test_response
from services import soil_extraction_service
from config.settings import DATA_DIR

log = logging.getLogger(__name__)

soil_bp = Blueprint("soil_routes", __name__)

_UPLOAD_DIR = os.path.join(DATA_DIR, "uploads", "soil_reports")


@soil_bp.route("/api/soil/validate", methods=["POST"])
def validate_soil():
    """Validate user-supplied Soil Health Card style values."""
    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify(build_no_soil_test_response()), 200

    result = validate_manual_soil_values(data)
    return jsonify(result), 200


@soil_bp.route("/api/soil/extract", methods=["POST"])
def extract_soil():
    """
    Accept an uploaded soil test report (PDF/PNG/JPG) and attempt structured
    extraction. Extracted values ALWAYS require user confirmation before use.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided. Use multipart/form-data with a 'file' field."}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    file.seek(0, os.SEEK_END)
    size_bytes = file.tell()
    file.seek(0)

    validation = soil_extraction_service.validate_upload(file.filename, size_bytes)
    if not validation["valid"]:
        return jsonify({"error": validation["error"]}), 400

    store_path = soil_extraction_service.safe_store_path(_UPLOAD_DIR, file.filename)

    try:
        file.save(store_path)
    except Exception as e:
        log.error(f"Failed to save uploaded soil report: {e}")
        return jsonify({"error": "Could not save the uploaded file. Please try again."}), 500

    try:
        result = soil_extraction_service.extract_soil_report(store_path)
    finally:
        # Do not retain the raw uploaded document after extraction attempt.
        try:
            os.remove(store_path)
        except OSError:
            pass

    return jsonify(result), 200
