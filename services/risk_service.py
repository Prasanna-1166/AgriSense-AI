"""
AgriSense AI - Risk Intelligence Service
===========================================

Provides a transparent, RULE-BASED risk layer. This deliberately does NOT
claim a calibrated probability of crop failure - no validated model for
that exists in this system. Instead it produces Low/Moderate/High/Data
unavailable labels from documented, inspectable rules comparing forecast
weather against typical crop needs and rainfall/temperature thresholds.
"""
from typing import Dict, List, Optional


# Documented thresholds. These are general agronomic heuristics, not
# crop-specific field-validated failure-probability models.
HEAVY_RAIN_THRESHOLD_MM_DAY = 50.0
DROUGHT_WARNING_RAINFALL_MM_YEAR = 400.0
HEAT_STRESS_THRESHOLD_C = 40.0
COLD_STRESS_THRESHOLD_C = 8.0


def assess_rainfall_risk(forecast_7day: Optional[Dict], annual_rainfall_mm: Optional[float]) -> Dict:
    """Assess rainfall-related risk from forecast and annual rainfall estimate."""
    if not forecast_7day or not forecast_7day.get("precipitation"):
        return {
            "category": "rainfall",
            "level": "Data unavailable",
            "explanation": "7-day precipitation forecast is not available for this location.",
            "rule": None,
        }

    precip = [p for p in forecast_7day["precipitation"] if p is not None]
    max_daily = max(precip) if precip else 0
    total_week = sum(precip) if precip else 0

    if max_daily >= HEAVY_RAIN_THRESHOLD_MM_DAY:
        return {
            "category": "rainfall",
            "level": "High",
            "explanation": f"Forecast shows a day with {max_daily:.0f} mm precipitation, "
                           f"at or above the {HEAVY_RAIN_THRESHOLD_MM_DAY:.0f} mm/day heavy-rain threshold used by this system.",
            "rule": f"max_daily_precip_mm >= {HEAVY_RAIN_THRESHOLD_MM_DAY}",
        }

    if annual_rainfall_mm is not None and annual_rainfall_mm < DROUGHT_WARNING_RAINFALL_MM_YEAR:
        return {
            "category": "rainfall",
            "level": "Moderate",
            "explanation": f"Estimated annual rainfall ({annual_rainfall_mm:.0f} mm) is below the "
                           f"{DROUGHT_WARNING_RAINFALL_MM_YEAR:.0f} mm/year threshold this system treats as a dry-conditions warning.",
            "rule": f"annual_rainfall_mm < {DROUGHT_WARNING_RAINFALL_MM_YEAR}",
        }

    return {
        "category": "rainfall",
        "level": "Low",
        "explanation": f"7-day forecast and rainfall estimate do not cross this system's heavy-rain or drought-warning thresholds.",
        "rule": None,
    }


def assess_temperature_risk(forecast_7day: Optional[Dict]) -> Dict:
    """Assess temperature-related risk from the 7-day forecast."""
    if not forecast_7day or not forecast_7day.get("temp_max"):
        return {
            "category": "temperature",
            "level": "Data unavailable",
            "explanation": "7-day temperature forecast is not available for this location.",
            "rule": None,
        }

    temp_max = [t for t in forecast_7day["temp_max"] if t is not None]
    temp_min = [t for t in forecast_7day["temp_min"] if t is not None]

    max_of_max = max(temp_max) if temp_max else None
    min_of_min = min(temp_min) if temp_min else None

    if max_of_max is not None and max_of_max >= HEAT_STRESS_THRESHOLD_C:
        return {
            "category": "temperature",
            "level": "High",
            "explanation": f"Forecast maximum temperature ({max_of_max:.1f}°C) is at or above the "
                           f"{HEAT_STRESS_THRESHOLD_C:.0f}°C heat-stress threshold used by this system.",
            "rule": f"max_temp_c >= {HEAT_STRESS_THRESHOLD_C}",
        }

    if min_of_min is not None and min_of_min <= COLD_STRESS_THRESHOLD_C:
        return {
            "category": "temperature",
            "level": "Moderate",
            "explanation": f"Forecast minimum temperature ({min_of_min:.1f}°C) is at or below the "
                           f"{COLD_STRESS_THRESHOLD_C:.0f}°C cold-stress threshold used by this system.",
            "rule": f"min_temp_c <= {COLD_STRESS_THRESHOLD_C}",
        }

    return {
        "category": "temperature",
        "level": "Low",
        "explanation": "Forecast temperatures do not cross this system's heat-stress or cold-stress thresholds.",
        "rule": None,
    }


def assess_irrigation_risk(irrigation: str, rainfall_risk_level: str) -> Dict:
    """Assess irrigation-related concern given irrigation availability and rainfall risk."""
    if irrigation == "none" and rainfall_risk_level == "Moderate":
        return {
            "category": "irrigation",
            "level": "Moderate",
            "explanation": "No irrigation is available and rainfall appears limited - water stress is a realistic concern.",
            "rule": "irrigation == none AND rainfall_risk == Moderate",
        }
    if irrigation == "none" and rainfall_risk_level == "High":
        return {
            "category": "irrigation",
            "level": "High",
            "explanation": "No irrigation is available and heavy-rain risk is flagged - waterlogging risk without drainage control.",
            "rule": "irrigation == none AND rainfall_risk == High",
        }
    return {
        "category": "irrigation",
        "level": "Low",
        "explanation": "Available irrigation and current rainfall risk do not indicate an elevated concern.",
        "rule": None,
    }


def assess_data_availability_risk(data_quality_overall: str, crop_supported: bool) -> Dict:
    """Flag risk arising from limited data availability itself."""
    if not crop_supported:
        return {
            "category": "data_availability",
            "level": "Data unavailable",
            "explanation": "This crop has no validated model coverage in this system - no recommendation-based risk assessment is possible.",
            "rule": None,
        }
    if data_quality_overall in ("low", "fallback"):
        return {
            "category": "data_availability",
            "level": "Moderate",
            "explanation": "Several inputs for this analysis are estimated or fallback values rather than measured - treat results with more caution.",
            "rule": "data_quality.overall in (low, fallback)",
        }
    return {
        "category": "data_availability",
        "level": "Low",
        "explanation": "Most inputs for this analysis were retrieved or measured rather than estimated.",
        "rule": None,
    }


def build_risk_summary(
    forecast_7day: Optional[Dict],
    annual_rainfall_mm: Optional[float],
    irrigation: str,
    data_quality_overall: str,
    crop_supported: bool
) -> List[Dict]:
    """Build the complete risk summary for a farm analysis."""
    rainfall_risk = assess_rainfall_risk(forecast_7day, annual_rainfall_mm)
    temperature_risk = assess_temperature_risk(forecast_7day)
    irrigation_risk = assess_irrigation_risk(irrigation, rainfall_risk["level"])
    data_risk = assess_data_availability_risk(data_quality_overall, crop_supported)

    return [rainfall_risk, temperature_risk, irrigation_risk, data_risk]
