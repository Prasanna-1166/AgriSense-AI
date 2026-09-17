"""
AgriSense AI - Location routes
"""
from flask import Blueprint, jsonify, request

from services import geocoding_service
from utils.validation import validate_coordinates
from config.geography import get_states, get_districts, match_state_from_address, match_district_from_address

location_bp = Blueprint("location", __name__)


@location_bp.route("/api/location/states", methods=["GET"])
def states():
    """List Indian states for the manual location fallback."""
    return jsonify({"states": get_states()}), 200


@location_bp.route("/api/location/districts", methods=["GET"])
def districts():
    """List districts for a given state (full lists maintained for AP/Telangana)."""
    state = request.args.get("state", "")
    if not state:
        return jsonify({"districts": [], "error": "Provide a 'state' query parameter."}), 400
    return jsonify({"districts": get_districts(state)}), 200


@location_bp.route("/api/location/resolve", methods=["GET"])
def resolve():
    """
    Resolve GPS coordinates to a state/district via reverse geocoding, for
    the 'We found your location as District X, State Y. Is this correct?'
    confirmation flow.
    """
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Please provide valid numeric lat and lon."}), 400

    valid, msg = validate_coordinates(lat, lon)
    if not valid:
        return jsonify({"error": msg}), 400

    result = geocoding_service.reverse_geocode(lat, lon)
    if not result.get("result"):
        return jsonify({
            "resolved": False,
            "error": result.get("error") or "Could not resolve this location. Please select your state and district manually.",
        }), 200

    address = result["result"].get("address", {})
    state = match_state_from_address(address)
    district = match_district_from_address(address)

    return jsonify({
        "resolved": True,
        "display_name": result["result"].get("display_name", ""),
        "state": state,
        "district": district,
        "lat": lat,
        "lon": lon,
        "confirmation_prompt": f"We found your location as {district or 'your area'}, {state or 'your state'}. Is this correct?",
    }), 200


@location_bp.route("/api/location/search", methods=["GET"])
def search():
    """Search for a location by name."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": [], "error": "Please provide a search query (?q=...)"}), 400

    result = geocoding_service.search_location(query)
    status_code = 200 if not result.get("error") or result.get("results") else 200
    return jsonify(result), status_code


@location_bp.route("/api/location/reverse", methods=["GET"])
def reverse():
    """Reverse geocode coordinates to a location name."""
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"result": None, "error": "Please provide valid numeric lat and lon parameters."}), 400

    valid, msg = validate_coordinates(lat, lon)
    if not valid:
        return jsonify({"result": None, "error": msg}), 400

    result = geocoding_service.reverse_geocode(lat, lon)
    return jsonify(result), 200
