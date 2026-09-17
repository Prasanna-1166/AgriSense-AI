"""
Soil data service for AgriSense AI

Investigates location-based soil data via SoilGrids/ISRIC (a real,
publicly available global soil property mapping service). Because
SoilGrids does not directly provide N/P/K in the exact units this
model expects, and does not cover all locations reliably, this service
implements a documented, honest fallback chain:

    SoilGrids (pH, organic carbon -> used to inform estimates)
          |
    Regional/latitude-based estimation
          |
    Manual soil entry (user provides values)

IMPORTANT: SoilGrids provides MODELED soil property values, not
laboratory measurements. This is clearly labeled throughout. Nitrogen,
Phosphorus, and Potassium (N/P/K) as required by the crop model are NOT
directly measurable from satellite/geospatial data at the precision
needed - so N/P/K are always estimated/fallback values unless the user
supplies real soil test results (Expert mode).

External API failures NEVER break the application - they simply lower
the confidence level and fall through the chain.
"""
import logging
from typing import Dict, Optional

import requests

from config.settings import SOILGRIDS_BASE_URL, API_TIMEOUT, CACHE_DIR, DEFAULT_SOIL_VALUES
from utils.cache import SimpleCache

log = logging.getLogger(__name__)

_cache = SimpleCache(CACHE_DIR, ttl_seconds=86400)  # 24 hour cache (soil changes slowly)


def fetch_soilgrids_ph(lat: float, lon: float) -> Optional[Dict]:
    """
    Fetch modeled soil pH from SoilGrids/ISRIC (0-5cm depth, mean value).
    
    Returns None if unavailable - caller should fall through the chain.
    SoilGrids pH values are reported as pH*10 (to avoid decimals in their
    raster format), so we divide by 10.
    """
    cache_key = f"soilgrids_ph_{lat:.3f}_{lon:.3f}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            f"{SOILGRIDS_BASE_URL}/properties/query",
            params={
                "lat": lat,
                "lon": lon,
                "property": "phh2o",
                "depth": "0-5cm",
                "value": "mean"
            },
            timeout=API_TIMEOUT,
            headers={"User-Agent": "AgriSense-AI/2.0 (educational agricultural application)"}
        )
        response.raise_for_status()
        data = response.json()

        layers = data.get("properties", {}).get("layers", [])
        for layer in layers:
            if layer.get("name") == "phh2o":
                depths = layer.get("depths", [])
                for depth in depths:
                    if depth.get("label") == "0-5cm":
                        mean_val = depth.get("values", {}).get("mean")
                        if mean_val is not None:
                            ph_value = round(mean_val / 10.0, 2)
                            result = {
                                "value": ph_value,
                                "unit": "pH",
                                "source": "SoilGrids / ISRIC (modeled, 0-5cm depth)",
                                "status": "estimated",
                                "confidence": "moderate"
                            }
                            _cache.set(cache_key, result)
                            return result
        return None

    except requests.exceptions.Timeout:
        log.warning(f"SoilGrids timeout for {lat},{lon}")
        return None
    except Exception as e:
        log.warning(f"SoilGrids fetch failed for {lat},{lon}: {e}")
        return None


def fetch_soilgrids_nitrogen(lat: float, lon: float) -> Optional[Dict]:
    """
    Fetch modeled soil nitrogen (total N, g/kg) from SoilGrids.
    Used as an INDICATOR to help scale N estimates - not a direct
    replacement for the N/P/K units this model's training dataset uses.
    """
    cache_key = f"soilgrids_n_{lat:.3f}_{lon:.3f}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            f"{SOILGRIDS_BASE_URL}/properties/query",
            params={
                "lat": lat,
                "lon": lon,
                "property": "nitrogen",
                "depth": "0-5cm",
                "value": "mean"
            },
            timeout=API_TIMEOUT,
            headers={"User-Agent": "AgriSense-AI/2.0 (educational agricultural application)"}
        )
        response.raise_for_status()
        data = response.json()

        layers = data.get("properties", {}).get("layers", [])
        for layer in layers:
            if layer.get("name") == "nitrogen":
                depths = layer.get("depths", [])
                for depth in depths:
                    if depth.get("label") == "0-5cm":
                        mean_val = depth.get("values", {}).get("mean")
                        if mean_val is not None:
                            # SoilGrids reports in cg/kg (centigrams/kg); convert to g/kg
                            n_gkg = round(mean_val / 100.0, 2)
                            result = {
                                "value": n_gkg,
                                "unit": "g/kg (total N indicator)",
                                "source": "SoilGrids / ISRIC (modeled, 0-5cm depth)",
                                "status": "estimated",
                                "confidence": "low"
                            }
                            _cache.set(cache_key, result)
                            return result
        return None

    except Exception as e:
        log.warning(f"SoilGrids nitrogen fetch failed for {lat},{lon}: {e}")
        return None


def _regional_npk_estimate(lat: float, lon: float) -> Dict:
    """
    Regional fallback estimate for N/P/K based on broad climatic zone.
    Clearly labeled as a coarse fallback, never a measurement.
    """
    abs_lat = abs(lat)

    if abs_lat < 23.5:
        # Tropical - often more weathered, lower native fertility
        n, p, k = 45, 30, 35
    elif abs_lat < 35:
        # Subtropical
        n, p, k = 55, 38, 42
    else:
        # Temperate
        n, p, k = 60, 40, 45

    return {"N": n, "P": p, "K": k}


def get_soil_profile(lat: float, lon: float) -> Dict:
    """
    Get complete soil profile with graceful fallback chain:
    
        SoilGrids (pH, N indicator)
              |
        Regional/latitude-based estimation (N, P, K)
              |
        Default fallback values
    
    Returns a dict with N, P, K, ph - each with value/unit/source/status/confidence.
    N, P, K are ALWAYS estimates from this pipeline (never claimed as
    laboratory measurements) since no reliable public API provides
    precise field-level N/P/K in the required units globally.
    """
    profile = {}

    # --- pH: try SoilGrids first ---
    ph_data = fetch_soilgrids_ph(lat, lon)
    if ph_data:
        profile["ph"] = ph_data
    else:
        regional = _regional_npk_estimate(lat, lon)
        profile["ph"] = {
            "value": DEFAULT_SOIL_VALUES["ph"],
            "unit": "pH",
            "source": "Regional fallback estimate",
            "status": "fallback",
            "confidence": "low"
        }

    # --- N, P, K: SoilGrids nitrogen indicator can adjust regional baseline ---
    regional = _regional_npk_estimate(lat, lon)
    nitrogen_indicator = fetch_soilgrids_nitrogen(lat, lon)

    if nitrogen_indicator and nitrogen_indicator.get("value") is not None:
        # Use the indicator to scale the regional N estimate up/down
        # (SoilGrids total N in g/kg doesn't map 1:1 to kg/ha plant-available N,
        # so this is used only as a directional adjustment, clearly labeled)
        indicator_val = nitrogen_indicator["value"]
        scale_factor = min(max(indicator_val / 1.5, 0.6), 1.6)  # bounded adjustment
        n_value = round(regional["N"] * scale_factor)
        profile["N"] = {
            "value": n_value,
            "unit": "kg/ha (estimated)",
            "source": "Regional estimate, adjusted by SoilGrids total-N indicator",
            "status": "estimated",
            "confidence": "low"
        }
    else:
        profile["N"] = {
            "value": regional["N"],
            "unit": "kg/ha (estimated)",
            "source": "Regional/climatic zone estimate",
            "status": "fallback",
            "confidence": "low"
        }

    profile["P"] = {
        "value": regional["P"],
        "unit": "kg/ha (estimated)",
        "source": "Regional/climatic zone estimate",
        "status": "fallback",
        "confidence": "low"
    }

    profile["K"] = {
        "value": regional["K"],
        "unit": "kg/ha (estimated)",
        "source": "Regional/climatic zone estimate",
        "status": "fallback",
        "confidence": "low"
    }

    return profile


# ==========================================================================
# Soil Health Card - manual entry support
# ==========================================================================
#
# These parameters mirror the fields shown on India's Soil Health Card.
# Only parameters the user actually supplies are used/displayed - this
# module never fabricates a Soil Health Card value.

SOIL_HEALTH_CARD_PARAMS = {
    "ph": {"label": "pH", "unit": "", "range": (2.0, 12.0)},
    "ec": {"label": "Electrical Conductivity (EC)", "unit": "dS/m", "range": (0.0, 20.0)},
    "organic_carbon": {"label": "Organic Carbon (OC)", "unit": "%", "range": (0.0, 5.0)},
    "N": {"label": "Nitrogen (N)", "unit": "kg/ha", "range": (0.0, 500.0)},
    "P": {"label": "Phosphorus (P)", "unit": "kg/ha", "range": (0.0, 300.0)},
    "K": {"label": "Potassium (K)", "unit": "kg/ha", "range": (0.0, 500.0)},
    "sulphur": {"label": "Sulphur (S)", "unit": "ppm", "range": (0.0, 100.0)},
    "zinc": {"label": "Zinc (Zn)", "unit": "ppm", "range": (0.0, 20.0)},
    "iron": {"label": "Iron (Fe)", "unit": "ppm", "range": (0.0, 50.0)},
    "manganese": {"label": "Manganese (Mn)", "unit": "ppm", "range": (0.0, 50.0)},
    "copper": {"label": "Copper (Cu)", "unit": "ppm", "range": (0.0, 20.0)},
    "boron": {"label": "Boron (B)", "unit": "ppm", "range": (0.0, 10.0)},
}


def validate_manual_soil_values(values: Dict) -> Dict:
    """
    Validate user-supplied Soil Health Card style values. Only fields the
    user actually provided are validated/returned - never invents missing
    fields.

    Returns:
        {"valid": {...}, "errors": [...]}
    """
    valid = {}
    errors = []

    for field, raw_value in (values or {}).items():
        spec = SOIL_HEALTH_CARD_PARAMS.get(field)
        if spec is None:
            errors.append(f"Unknown soil parameter: {field}")
            continue
        try:
            v = float(raw_value)
        except (TypeError, ValueError):
            errors.append(f"Invalid value for {spec['label']}: {raw_value}")
            continue

        lo, hi = spec["range"]
        if not (lo <= v <= hi):
            errors.append(f"{spec['label']} value {v} is outside the plausible range ({lo}-{hi})")
            continue

        valid[field] = {
            "value": v,
            "unit": spec["unit"],
            "source": "User-entered soil test",
            "status": "USER_ENTERED",
            "confidence": "high",
        }

    return {"valid": valid, "errors": errors}


def build_no_soil_test_response() -> Dict:
    """Explicit 'no soil test available' response - never silently estimated."""
    return {
        "available": False,
        "message": "No soil test available. Recommendations will proceed using location-based "
                    "estimates only, clearly labeled as estimates.",
    }


def get_soil_type_estimate(lat: float, lon: float) -> Optional[str]:
    """
    Best-effort soil type label based on broad climatic zone.
    This is a rough indicator only, not a soil survey result.
    """
    abs_lat = abs(lat)
    if abs_lat < 10:
        return "Laterite (estimated)"
    elif abs_lat < 23.5:
        return "Alluvial / Red soil (estimated)"
    elif abs_lat < 35:
        return "Loamy (estimated)"
    else:
        return "Mixed temperate soil (estimated)"
