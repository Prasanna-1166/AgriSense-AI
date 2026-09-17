"""
AgriSense AI - Farm profile routes

Optional, local, no-authentication farm profile storage so a returning
user can reuse a saved location/farm size/irrigation/soil setup ("My Farm").
Not required to use the app - Planning Mode works without ever saving one.
"""
import json
import logging
import os

from flask import Blueprint, jsonify, request

from config.settings import DATA_DIR

log = logging.getLogger(__name__)

farm_bp = Blueprint("farm", __name__)

_PROFILE_PATH = os.path.join(DATA_DIR, "farm_profile.json")


def _load_profile():
    if not os.path.exists(_PROFILE_PATH):
        return None
    try:
        with open(_PROFILE_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Failed to load farm profile: {e}")
        return None


def _save_profile(data):
    try:
        with open(_PROFILE_PATH, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        log.warning(f"Failed to save farm profile: {e}")
        return False


@farm_bp.route("/api/farm/profile", methods=["GET"])
def get_farm_profile():
    """Get the saved farm profile, if any. Farm profiles are optional."""
    profile = _load_profile()
    if profile is None:
        return jsonify({"exists": False, "profile": None}), 200
    return jsonify({"exists": True, "profile": profile}), 200


@farm_bp.route("/api/farm/profile", methods=["POST"])
def save_farm_profile():
    """Save (or overwrite) the local farm profile."""
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "No profile data provided."}), 400

    allowed_fields = {
        "location", "state", "district", "area_ha", "irrigation", "water_source",
        "current_crop", "crop_stage", "soil", "growing_season", "previous_crop",
    }
    profile = {k: v for k, v in data.items() if k in allowed_fields}

    success = _save_profile(profile)
    if success:
        return jsonify({"status": "saved", "profile": profile}), 200
    return jsonify({"error": "Could not save farm profile."}), 500


@farm_bp.route("/api/farm/profile", methods=["DELETE"])
def delete_farm_profile():
    """Delete the saved farm profile."""
    if os.path.exists(_PROFILE_PATH):
        try:
            os.remove(_PROFILE_PATH)
        except OSError as e:
            log.warning(f"Failed to delete farm profile: {e}")
            return jsonify({"error": "Could not delete farm profile."}), 500
    return jsonify({"status": "deleted"}), 200
