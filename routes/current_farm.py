"""
AgriSense AI - Current Farm Mode routes

"I have a farm/crop already. Help me understand the current situation."

Unlike Planning Mode, this does NOT rank alternative crops - it evaluates
the farmer's EXISTING crop against current conditions, weather, and (if
provided) soil data, and returns a yield estimate only when the crop has
validated model coverage per the Crop Master registry.

Disease detection is explicitly a future module and is NOT implemented
here - no placeholder/fake disease detection is exposed.
"""
import logging
from flask import Blueprint, jsonify, request

from services import environment_service, weather_service, risk_service
from ml.predictor import predict_for_specific_crop, is_ready
from ml.explainability import generate_farm_insights
from utils.validation import validate_coordinates, validate_farm_inputs
from utils.helpers import MetricsCalculator, generate_prediction_id, get_timestamp
from config.settings import CROP_FEATURES
from config.crop_master import get_crop_info, is_crop_supported

log = logging.getLogger(__name__)

current_farm_bp = Blueprint("current_farm", __name__)


@current_farm_bp.route("/api/farm/analyze-current", methods=["POST"])
def analyze_current_farm():
    """
    Analyze the farmer's current crop situation.

    Body: {
        lat, lon, current_crop, crop_stage (optional), area_ha, irrigation,
        soil (optional dict of manual soil values),
        <any of the 7 crop features to override auto-retrieved values>
    }
    """
    data = request.get_json(silent=True) or {}

    current_crop = str(data.get("current_crop", "")).strip().lower()
    if not current_crop:
        return jsonify({"error": "Please provide 'current_crop'."}), 400

    crop_info = get_crop_info(current_crop)
    if not crop_info:
        return jsonify({"error": f"'{current_crop}' is not in the crop registry. "
                                  f"See /api/crops for the supported list."}), 404

    try:
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Please provide valid numeric lat and lon."}), 400

    valid, msg = validate_coordinates(lat, lon)
    if not valid:
        return jsonify({"error": msg}), 400

    valid, msg, farm_inputs = validate_farm_inputs(data)
    if not valid:
        return jsonify({"error": msg}), 400

    area_ha = farm_inputs.get("area_ha", 1.0)
    irrigation = farm_inputs.get("irrigation", "partial")
    crop_stage = str(data.get("crop_stage", "")).strip() or None

    # Always fetch weather/climate/soil - this is useful regardless of
    # whether the crop itself is model-supported.
    try:
        profile = environment_service.build_environment_profile(lat, lon)
    except Exception as e:
        log.error(f"Environment profile error: {e}")
        profile = {"climate": {}, "soil": {}, "elevation": None, "data_quality": {"overall": "low"}}

    user_overrides = {}
    for feat in CROP_FEATURES:
        if feat in data and data[feat] not in (None, ""):
            try:
                user_overrides[feat] = float(data[feat])
            except (ValueError, TypeError):
                return jsonify({"error": f"Invalid value provided for {feat}."}), 400

    merged = environment_service.merge_with_user_overrides(profile, user_overrides)
    feature_values = environment_service.extract_prediction_values(merged)

    weather = weather_service.fetch_current_weather(lat, lon)

    response = {
        "prediction_id": generate_prediction_id(),
        "timestamp": get_timestamp(),
        "location": {"lat": lat, "lon": lon},
        "current_crop": current_crop,
        "crop_stage": crop_stage,
        "farm": {"area_ha": area_ha, "irrigation": irrigation},
        "environment_profile": merged,
        "elevation": profile.get("elevation"),
        "weather": {
            "current": weather.get("current"),
            "forecast_7day": weather.get("forecast_7day"),
        },
        "data_quality": profile.get("data_quality", {}),
    }

    if not is_crop_supported(current_crop):
        response["suitability_available"] = False
        response["yield_available"] = False
        response["message"] = (
            f"This system does not have validated recommendation/yield data for "
            f"{crop_info['display_name']}. {crop_info.get('reason', '')} "
            f"{crop_info.get('real_world_data_note', '')}"
        )
        response["insights"] = [{
            "type": "info", "icon": "ℹ",
            "text": f"Weather and soil information above are still shown, but no crop-suitability "
                    f"or yield estimate is available for {crop_info['display_name']} in this system."
        }]
        response["risks"] = risk_service.build_risk_summary(
            forecast_7day=weather.get("forecast_7day"),
            annual_rainfall_mm=feature_values.get("rainfall"),
            irrigation=irrigation,
            data_quality_overall=response["data_quality"].get("overall", "moderate"),
            crop_supported=False,
        )
        return jsonify(response), 200

    if not is_ready():
        response["suitability_available"] = False
        response["yield_available"] = False
        response["message"] = "Prediction models are not yet trained on this server."
        return jsonify(response), 503

    missing = [f for f in CROP_FEATURES if f not in feature_values]
    if missing:
        response["suitability_available"] = False
        response["yield_available"] = False
        response["message"] = f"Could not determine values for: {', '.join(missing)}. Provide them manually."
        return jsonify(response), 422

    try:
        crop_result = predict_for_specific_crop(feature_values, current_crop, area_ha, irrigation)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503

    water_info = MetricsCalculator.calculate_water_requirement(
        crop_result["predicted_yield_t_per_ha"],
        feature_values.get("rainfall", 0),
        current_crop,
        irrigation
    )
    insights = generate_farm_insights(
        current_crop,
        crop_result["suitability_pct"],
        crop_result["explanation"],
        water_info,
        response["data_quality"]
    )

    response["suitability_available"] = True
    response["yield_available"] = True
    response["crop_analysis"] = crop_result
    response["water_requirement"] = water_info
    response["insights"] = insights
    response["risks"] = risk_service.build_risk_summary(
        forecast_7day=weather.get("forecast_7day"),
        annual_rainfall_mm=feature_values.get("rainfall"),
        irrigation=irrigation,
        data_quality_overall=response["data_quality"].get("overall", "moderate"),
        crop_supported=True,
    )

    return jsonify(response), 200
