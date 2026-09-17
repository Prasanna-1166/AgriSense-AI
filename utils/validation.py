"""
Input validation utilities for AgriSense AI
"""
from typing import Dict, List, Tuple, Any
import logging

log = logging.getLogger(__name__)


def validate_coordinates(lat: float, lon: float) -> Tuple[bool, str]:
    """Validate latitude and longitude values."""
    try:
        lat = float(lat)
        lon = float(lon)
        if not (-90 <= lat <= 90):
            return False, "Latitude must be between -90 and 90"
        if not (-180 <= lon <= 180):
            return False, "Longitude must be between -180 and 180"
        return True, ""
    except (ValueError, TypeError):
        return False, "Invalid latitude or longitude format"


def validate_feature_values(features: Dict[str, float], feature_list: List[str]) -> Tuple[bool, str, Dict[str, float]]:
    """Validate and normalize feature values for prediction."""
    cleaned = {}
    
    for feature in feature_list:
        if feature not in features:
            return False, f"Missing feature: {feature}", {}
        
        try:
            value = float(features[feature])
        except (ValueError, TypeError):
            return False, f"Invalid value for {feature}", {}
        
        # Feature-specific validation
        if feature == "ph":
            if not (2 <= value <= 12):
                return False, f"pH must be between 2 and 12, got {value}", {}
        elif feature == "temperature":
            if not (-10 <= value <= 55):
                return False, f"Temperature must be between -10 and 55°C, got {value}", {}
        elif feature == "humidity":
            if not (0 <= value <= 100):
                return False, f"Humidity must be between 0 and 100%, got {value}", {}
        elif feature in ["N", "P", "K"]:
            if value < 0 or value > 300:
                return False, f"{feature} must be between 0 and 300 kg/ha, got {value}", {}
        elif feature == "rainfall":
            if value < 0 or value > 6000:
                return False, f"Rainfall must be between 0 and 6000 mm/year, got {value}", {}
        
        cleaned[feature] = value
    
    return True, "", cleaned


def validate_farm_inputs(data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate farm-related inputs."""
    cleaned = {}
    
    try:
        # Area
        if "area_ha" in data:
            area = float(data["area_ha"])
            if area <= 0 or area > 10000:
                return False, "Farm area must be between 0.01 and 10000 hectares", {}
            cleaned["area_ha"] = area
        else:
            cleaned["area_ha"] = 1.0  # Default
        
        # Irrigation
        if "irrigation" in data:
            irr = str(data["irrigation"]).lower()
            if irr not in ["none", "partial", "full"]:
                return False, "Invalid irrigation type", {}
            cleaned["irrigation"] = irr
        else:
            cleaned["irrigation"] = "partial"  # Default
        
        # Soil type
        if "soil_type" in data:
            cleaned["soil_type"] = str(data.get("soil_type", "")).strip() or None
        
        # Growing season
        if "growing_season" in data:
            cleaned["growing_season"] = str(data.get("growing_season", "")).strip() or None
        
        # Previous crop
        if "previous_crop" in data:
            cleaned["previous_crop"] = str(data.get("previous_crop", "")).strip() or None
        
        return True, "", cleaned
    
    except (ValueError, TypeError) as e:
        return False, f"Invalid farm input: {str(e)}", {}


def validate_prediction_mode(mode: str) -> Tuple[bool, str]:
    """Validate prediction mode."""
    valid_modes = ["quick", "assisted", "expert"]
    if mode not in valid_modes:
        return False, f"Invalid prediction mode. Must be one of: {', '.join(valid_modes)}"
    return True, ""


def validate_recommendation_payload(payload: Dict[str, Any], crop_features: List[str]) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate complete recommendation payload."""
    required_fields = crop_features + ["area_ha"]
    
    # Check all required fields present
    for field in required_fields:
        if field not in payload:
            return False, f"Missing required field: {field}", {}
    
    # Validate coordinates if provided
    if "lat" in payload and "lon" in payload:
        valid, msg = validate_coordinates(payload["lat"], payload["lon"])
        if not valid:
            return False, msg, {}
    
    # Validate features
    valid, msg, features = validate_feature_values(payload, crop_features)
    if not valid:
        return False, msg, {}
    
    # Validate farm inputs
    valid, msg, farm_inputs = validate_farm_inputs(payload)
    if not valid:
        return False, msg, {}
    
    # Combine all validated data
    cleaned = features.copy()
    cleaned.update(farm_inputs)
    if "lat" in payload:
        cleaned["lat"] = float(payload["lat"])
    if "lon" in payload:
        cleaned["lon"] = float(payload["lon"])
    
    return True, "", cleaned


class DataQualityAssessor:
    """Assess overall data quality and confidence levels."""
    
    @staticmethod
    def assess(data_sources: Dict[str, str], soil_status: str, climate_status: str) -> Dict[str, Any]:
        """
        Assess data quality based on sources and availability.
        
        Args:
            data_sources: dict with data source types ("retrieved", "estimated", "fallback")
            soil_status: overall soil data status
            climate_status: overall climate data status
        
        Returns:
            Quality assessment dict with overall rating and details
        """
        retrieved_count = sum(1 for v in data_sources.values() if v == "retrieved")
        estimated_count = sum(1 for v in data_sources.values() if v == "estimated")
        fallback_count = sum(1 for v in data_sources.values() if v == "fallback")
        total = len(data_sources)
        
        # Calculate quality score
        retrieved_pct = (retrieved_count / total * 100) if total > 0 else 0
        estimated_pct = (estimated_count / total * 100) if total > 0 else 0
        fallback_pct = (fallback_count / total * 100) if total > 0 else 0
        
        # Determine overall quality level
        if fallback_count > 0:
            overall_quality = "low"
            confidence = 0.3
        elif estimated_pct > 50:
            overall_quality = "moderate"
            confidence = 0.5
        elif retrieved_pct >= 70:
            overall_quality = "high"
            confidence = 0.8
        else:
            overall_quality = "moderate"
            confidence = 0.5
        
        return {
            "overall": overall_quality,
            "confidence": confidence,
            "retrieved_pct": round(retrieved_pct, 1),
            "estimated_pct": round(estimated_pct, 1),
            "fallback_pct": round(fallback_pct, 1),
            "soil_status": soil_status,
            "climate_status": climate_status,
            "details": {
                "retrieved": retrieved_count,
                "estimated": estimated_count,
                "fallback": fallback_count,
            }
        }
