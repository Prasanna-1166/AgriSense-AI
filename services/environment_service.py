"""
Environment orchestration service for AgriSense AI

Combines weather, climate, and soil services into a unified environment
profile for a given location, and computes an overall data quality
assessment. This is the core service behind Quick and Assisted prediction
modes.
"""
import logging
from typing import Dict, Optional

from services import weather_service, soil_service
from utils.validation import DataQualityAssessor

log = logging.getLogger(__name__)


def build_environment_profile(lat: float, lon: float) -> Dict:
    """
    Build a complete environment profile for a location: climate + soil,
    each with source/status/confidence metadata.
    
    Never raises on service failure - individual services already
    degrade gracefully, and this function aggregates whatever is
    available.
    """
    profile = {
        "location": {"lat": lat, "lon": lon},
        "climate": {},
        "soil": {},
        "elevation": None,
    }

    # Elevation
    try:
        elevation_data = weather_service.fetch_elevation(lat, lon)
        profile["elevation"] = elevation_data
    except Exception as e:
        log.warning(f"Elevation fetch error: {e}")
        profile["elevation"] = {
            "value": None, "unit": "m", "source": "unavailable",
            "status": "fallback", "confidence": "low"
        }

    # Climate (temperature, humidity, rainfall)
    try:
        climate_data = weather_service.fetch_climate_averages(lat, lon)
        profile["climate"] = climate_data
    except Exception as e:
        log.warning(f"Climate fetch error: {e}")
        profile["climate"] = {}

    # Soil (N, P, K, pH)
    try:
        soil_data = soil_service.get_soil_profile(lat, lon)
        profile["soil"] = soil_data
    except Exception as e:
        log.warning(f"Soil fetch error: {e}")
        profile["soil"] = {}

    # Soil type estimate
    try:
        profile["soil_type_estimate"] = soil_service.get_soil_type_estimate(lat, lon)
    except Exception:
        profile["soil_type_estimate"] = None

    # Compute data quality
    profile["data_quality"] = compute_data_quality(profile)

    return profile


def compute_data_quality(profile: Dict) -> Dict:
    """Compute overall data quality assessment from the environment profile."""
    data_sources = {}

    climate = profile.get("climate", {})
    for key in ["temperature", "rainfall", "humidity"]:
        item = climate.get(key)
        if item and "status" in item:
            data_sources[f"climate_{key}"] = item["status"]

    soil = profile.get("soil", {})
    for key in ["N", "P", "K", "ph"]:
        item = soil.get(key)
        if item and "status" in item:
            data_sources[f"soil_{key}"] = item["status"]

    elevation = profile.get("elevation", {})
    if elevation and "status" in elevation:
        data_sources["elevation"] = elevation["status"]

    if not data_sources:
        return {
            "overall": "low",
            "confidence": 0.2,
            "soil_status": "unavailable",
            "climate_status": "unavailable",
        }

    # Determine soil and climate overall status
    soil_statuses = [v for k, v in data_sources.items() if k.startswith("soil_")]
    climate_statuses = [v for k, v in data_sources.items() if k.startswith("climate_")]

    soil_status = _worst_status(soil_statuses)
    climate_status = _worst_status(climate_statuses)

    return DataQualityAssessor.assess(data_sources, soil_status, climate_status)


def _worst_status(statuses: list) -> str:
    """Return the 'worst' (least reliable) status from a list."""
    if not statuses:
        return "unavailable"
    if "fallback" in statuses:
        return "fallback"
    if "estimated" in statuses:
        return "estimated"
    if "retrieved" in statuses:
        return "retrieved"
    return "unavailable"


def merge_with_user_overrides(profile: Dict, user_values: Dict) -> Dict:
    """
    Merge an environment profile with user-provided override values
    (Assisted/Expert modes). User values always take precedence and
    are marked as 'manual' status.
    """
    merged = {}

    # Climate
    climate = profile.get("climate", {})
    for feat, api_key in [("temperature", "temperature"), ("humidity", "humidity"), ("rainfall", "rainfall")]:
        if feat in user_values and user_values[feat] is not None:
            merged[feat] = {
                "value": user_values[feat],
                "unit": {"temperature": "°C", "humidity": "%", "rainfall": "mm/year"}[feat],
                "source": "User provided",
                "status": "manual",
                "confidence": "high"
            }
        elif api_key in climate:
            merged[feat] = climate[api_key]
        else:
            merged[feat] = None

    # Soil
    soil = profile.get("soil", {})
    for feat in ["N", "P", "K", "ph"]:
        if feat in user_values and user_values[feat] is not None:
            merged[feat] = {
                "value": user_values[feat],
                "unit": "kg/ha" if feat != "ph" else "pH",
                "source": "User provided",
                "status": "manual",
                "confidence": "high"
            }
        elif feat in soil:
            merged[feat] = soil[feat]
        else:
            merged[feat] = None

    return merged


def extract_prediction_values(merged_profile: Dict) -> Dict:
    """Extract simple key:value pairs ready for ML prediction from merged profile."""
    values = {}
    for feat in ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]:
        item = merged_profile.get(feat)
        if item and item.get("value") is not None:
            values[feat] = float(item["value"])
    return values
