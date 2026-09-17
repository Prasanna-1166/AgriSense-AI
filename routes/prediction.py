"""
AgriSense AI - Prediction routes (Planning Mode)

Implements the three Planning Mode input tiers:
  - Quick: location only, everything else auto-retrieved/estimated
  - Assisted (default): location auto-fills, user can override any value
  - Expert: full manual soil-test entry

Current Farm Mode (situational analysis for an existing crop) lives in
routes/current_farm.py.
"""
import logging
from flask import Blueprint, jsonify, request

from services import environment_service, weather_service, risk_service
from ml.predictor import predict_recommendations, is_ready, get_models
from ml.explainability import generate_farm_insights
from utils.validation import validate_coordinates, validate_farm_inputs
from utils.helpers import MetricsCalculator, generate_prediction_id, get_timestamp
from config.settings import CROP_FEATURES

log = logging.getLogger(__name__)

prediction_bp = Blueprint("prediction", __name__)


def _model_not_ready_response():
    return jsonify({
        "error": "Prediction models are not yet trained. Please run: "
                 "python -m ml.train_crop_model && python -m ml.train_yield_model"
    }), 503


def _run_prediction(feature_values: dict, area_ha: float, irrigation: str, location: dict,
                     data_quality: dict, mode: str) -> dict:
    """Shared prediction execution logic for all modes."""
    result = predict_recommendations(feature_values, area_ha, irrigation, top_n=5)

    top_crop = result["top_crop"]
    water_info = {}
    insights = []

    if top_crop:
        water_info = MetricsCalculator.calculate_water_requirement(
            top_crop["predicted_yield_t_per_ha"],
            feature_values.get("rainfall", 0),
            top_crop["crop"],
            irrigation
        )
        insights = generate_farm_insights(
            top_crop["crop"],
            top_crop["suitability_pct"],
            top_crop["explanation"],
            water_info,
            data_quality
        )

    # Risk intelligence - rule-based, using forecast weather where a location is known
    forecast_7day = None
    if location.get("lat") is not None and location.get("lon") is not None:
        try:
            weather = weather_service.fetch_current_weather(location["lat"], location["lon"])
            forecast_7day = weather.get("forecast_7day")
        except Exception:
            forecast_7day = None

    risks = risk_service.build_risk_summary(
        forecast_7day=forecast_7day,
        annual_rainfall_mm=feature_values.get("rainfall"),
        irrigation=irrigation,
        data_quality_overall=data_quality.get("overall", "moderate"),
        crop_supported=bool(top_crop),
    )

    response = {
        "mode": mode,
        "prediction_id": generate_prediction_id(),
        "timestamp": get_timestamp(),
        "location": location,
        "input_values": feature_values,
        "farm": {"area_ha": area_ha, "irrigation": irrigation},
        "data_quality": data_quality,
        "ranked_crops": result["ranked_crops"],
        "top_crop": top_crop,
        "feature_importance": result["feature_importance"],
        "water_requirement": water_info,
        "insights": insights,
        "risks": risks,
    }
    return response


@prediction_bp.route("/api/predict/quick", methods=["POST"])
def predict_quick():
    """
    MODE 1: Quick Location Prediction
    User provides only a location; everything else is auto-retrieved/estimated.
    """
    if not is_ready():
        return _model_not_ready_response()

    data = request.get_json(silent=True) or {}

    try:
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Please provide valid numeric lat and lon."}), 400

    valid, msg = validate_coordinates(lat, lon)
    if not valid:
        return jsonify({"error": msg}), 400

    area_ha = float(data.get("area_ha", 1.0))
    irrigation = str(data.get("irrigation", "partial")).lower()
    if irrigation not in ["none", "partial", "full"]:
        irrigation = "partial"

    try:
        profile = environment_service.build_environment_profile(lat, lon)
        merged = environment_service.merge_with_user_overrides(profile, {})
        feature_values = environment_service.extract_prediction_values(merged)

        missing = [f for f in CROP_FEATURES if f not in feature_values]
        if missing:
            return jsonify({
                "error": f"Could not determine values for: {', '.join(missing)}. "
                         "Try Assisted or Expert mode to provide these manually."
            }), 422

        response = _run_prediction(
            feature_values, area_ha, irrigation,
            {"lat": lat, "lon": lon}, profile["data_quality"], "quick"
        )
        response["environment_profile"] = merged
        response["elevation"] = profile.get("elevation")
        response["soil_type_estimate"] = profile.get("soil_type_estimate")
        return jsonify(response), 200

    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        log.error(f"Quick prediction error: {e}")
        return jsonify({"error": "Prediction failed due to an unexpected error."}), 500


@prediction_bp.route("/api/predict/assisted", methods=["POST"])
def predict_assisted():
    """
    MODE 2 (DEFAULT): Smart Assisted Prediction
    Location auto-fills environment/soil; user may override any value.
    """
    if not is_ready():
        return _model_not_ready_response()

    data = request.get_json(silent=True) or {}

    try:
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Please provide valid numeric lat and lon."}), 400

    valid, msg = validate_coordinates(lat, lon)
    if not valid:
        return jsonify({"error": msg}), 400

    area_ha = float(data.get("area_ha", 1.0))
    irrigation = str(data.get("irrigation", "partial")).lower()
    if irrigation not in ["none", "partial", "full"]:
        irrigation = "partial"

    # Collect user overrides for any of the 7 features
    user_overrides = {}
    for feat in CROP_FEATURES:
        if feat in data and data[feat] not in (None, ""):
            try:
                user_overrides[feat] = float(data[feat])
            except (ValueError, TypeError):
                return jsonify({"error": f"Invalid value provided for {feat}."}), 400

    try:
        profile = environment_service.build_environment_profile(lat, lon)
        merged = environment_service.merge_with_user_overrides(profile, user_overrides)
        feature_values = environment_service.extract_prediction_values(merged)

        missing = [f for f in CROP_FEATURES if f not in feature_values]
        if missing:
            return jsonify({
                "error": f"Could not determine values for: {', '.join(missing)}. "
                         "Please provide them manually."
            }), 422

        # Recompute data quality including manual overrides
        data_quality = profile["data_quality"]
        if user_overrides:
            manual_count = len(user_overrides)
            total_count = len(CROP_FEATURES)
            if manual_count >= total_count * 0.5:
                data_quality = dict(data_quality)
                data_quality["overall"] = "high" if manual_count == total_count else "moderate"
                data_quality["confidence"] = 0.9 if manual_count == total_count else 0.7

        response = _run_prediction(
            feature_values, area_ha, irrigation,
            {"lat": lat, "lon": lon}, data_quality, "assisted"
        )
        response["environment_profile"] = merged
        response["elevation"] = profile.get("elevation")
        response["soil_type_estimate"] = profile.get("soil_type_estimate")
        return jsonify(response), 200

    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        log.error(f"Assisted prediction error: {e}")
        return jsonify({"error": "Prediction failed due to an unexpected error."}), 500


@prediction_bp.route("/api/predict/expert", methods=["POST"])
def predict_expert():
    """
    MODE 3: Expert / Soil Test Mode
    Full manual entry of all values - highest input accuracy, no
    auto-retrieval assumptions.
    """
    if not is_ready():
        return _model_not_ready_response()

    data = request.get_json(silent=True) or {}

    feature_values = {}
    for feat in CROP_FEATURES:
        if feat not in data:
            return jsonify({"error": f"Expert mode requires all fields. Missing: {feat}"}), 400
        try:
            feature_values[feat] = float(data[feat])
        except (ValueError, TypeError):
            return jsonify({"error": f"Invalid value for {feat}."}), 400

    valid, msg, farm_inputs = validate_farm_inputs(data)
    if not valid:
        return jsonify({"error": msg}), 400

    area_ha = farm_inputs.get("area_ha", 1.0)
    irrigation = farm_inputs.get("irrigation", "partial")

    location = {}
    if "lat" in data and "lon" in data:
        try:
            location = {"lat": float(data["lat"]), "lon": float(data["lon"])}
        except (ValueError, TypeError):
            location = {}

    # Expert mode = all values manual = highest data quality
    data_quality = {
        "overall": "high",
        "confidence": 0.95,
        "soil_status": "manual",
        "climate_status": "manual",
        "details": {"retrieved": 0, "estimated": 0, "fallback": 0, "manual": len(CROP_FEATURES)}
    }

    try:
        response = _run_prediction(
            feature_values, area_ha, irrigation, location, data_quality, "expert"
        )
        return jsonify(response), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        log.error(f"Expert prediction error: {e}")
        return jsonify({"error": "Prediction failed due to an unexpected error."}), 500


@prediction_bp.route("/api/predict", methods=["POST"])
def predict_generic():
    """
    Generic prediction endpoint - routes to the appropriate mode handler
    based on the 'mode' field in the request body (defaults to assisted).
    """
    data = request.get_json(silent=True) or {}
    mode = str(data.get("mode", "assisted")).lower()

    if mode == "quick":
        return predict_quick()
    elif mode == "expert":
        return predict_expert()
    else:
        return predict_assisted()
