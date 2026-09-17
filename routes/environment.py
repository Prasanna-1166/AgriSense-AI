"""
Environment and weather routes for AgriSense AI
"""
from flask import Blueprint, jsonify, request

from services import environment_service, weather_service
from utils.validation import validate_coordinates

environment_bp = Blueprint("environment", __name__)


@environment_bp.route("/api/environment", methods=["POST"])
def get_environment():
    """
    Build a complete environment profile (climate + soil) for a location.
    Used by Quick and Assisted modes to auto-populate values.
    """
    data = request.get_json(silent=True) or {}

    try:
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Please provide valid numeric lat and lon."}), 400

    valid, msg = validate_coordinates(lat, lon)
    if not valid:
        return jsonify({"error": msg}), 400

    try:
        profile = environment_service.build_environment_profile(lat, lon)
        return jsonify(profile), 200
    except Exception as e:
        return jsonify({"error": f"Could not build environment profile: {str(e)}"}), 500


@environment_bp.route("/api/soil", methods=["POST"])
def get_soil():
    """Get soil profile only for a location."""
    from services import soil_service

    data = request.get_json(silent=True) or {}

    try:
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Please provide valid numeric lat and lon."}), 400

    valid, msg = validate_coordinates(lat, lon)
    if not valid:
        return jsonify({"error": msg}), 400

    try:
        soil_profile = soil_service.get_soil_profile(lat, lon)
        soil_type = soil_service.get_soil_type_estimate(lat, lon)
        return jsonify({"soil": soil_profile, "soil_type_estimate": soil_type}), 200
    except Exception as e:
        return jsonify({"error": f"Could not retrieve soil data: {str(e)}"}), 500


@environment_bp.route("/api/weather", methods=["GET"])
def get_weather():
    """Get current weather and 7-day forecast for a location."""
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Please provide valid numeric lat and lon query parameters."}), 400

    valid, msg = validate_coordinates(lat, lon)
    if not valid:
        return jsonify({"error": msg}), 400

    try:
        weather = weather_service.fetch_current_weather(lat, lon)
        return jsonify(weather), 200
    except Exception as e:
        return jsonify({"error": f"Could not retrieve weather data: {str(e)}"}), 500
