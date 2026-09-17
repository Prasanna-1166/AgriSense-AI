"""
Weather and climate service for AgriSense AI

Wraps the free, keyless Open-Meteo API for current weather, forecast,
and climate averages. Implements caching, timeouts, and graceful
fallback to editable default estimates - never crashes the app.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

import requests

from config.settings import OPENMETEO_BASE_URL, WEATHER_TIMEOUT, CACHE_DIR
from utils.cache import SimpleCache

log = logging.getLogger(__name__)

_cache = SimpleCache(CACHE_DIR, ttl_seconds=3600)  # 1 hour cache


def _latitude_climate_default(lat: float) -> Dict:
    """
    Rough latitude-based climate default when Open-Meteo is unavailable.
    Clearly labeled as a fallback estimate, never presented as measured.
    """
    abs_lat = abs(lat)
    if abs_lat < 15:
        # Tropical
        temp, humidity, rainfall = 27.0, 78.0, 1800.0
    elif abs_lat < 30:
        # Subtropical
        temp, humidity, rainfall = 24.0, 65.0, 1000.0
    elif abs_lat < 45:
        # Temperate
        temp, humidity, rainfall = 15.0, 60.0, 700.0
    elif abs_lat < 60:
        # Cool temperate
        temp, humidity, rainfall = 8.0, 65.0, 600.0
    else:
        # Polar/subpolar
        temp, humidity, rainfall = -2.0, 70.0, 400.0

    return {"temperature": temp, "humidity": humidity, "rainfall": rainfall}


def fetch_elevation(lat: float, lon: float) -> Dict:
    """Fetch elevation for coordinates."""
    cache_key = f"elev_{lat:.3f}_{lon:.3f}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            f"{OPENMETEO_BASE_URL}/elevation",
            params={"latitude": lat, "longitude": lon},
            timeout=WEATHER_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        elevation = data.get("elevation", [None])[0]

        result = {
            "value": elevation,
            "unit": "m",
            "source": "Open-Meteo Elevation API",
            "status": "retrieved" if elevation is not None else "fallback",
            "confidence": "high" if elevation is not None else "low"
        }
        _cache.set(cache_key, result)
        return result

    except Exception as e:
        log.warning(f"Elevation fetch failed: {e}")
        return {
            "value": None,
            "unit": "m",
            "source": "unavailable",
            "status": "fallback",
            "confidence": "low"
        }


def fetch_current_weather(lat: float, lon: float) -> Dict:
    """Fetch current weather conditions."""
    cache_key = f"weather_{lat:.3f}_{lon:.3f}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            f"{OPENMETEO_BASE_URL}/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration",
                "forecast_days": 7,
                "timezone": "auto"
            },
            timeout=WEATHER_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        daily = data.get("daily", {})

        result = {
            "current": {
                "temperature_c": current.get("temperature_2m"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "precipitation_mm": current.get("precipitation"),
                "wind_speed_kmh": current.get("wind_speed_10m"),
                "weather_code": current.get("weather_code"),
            },
            "forecast_7day": {
                "dates": daily.get("time", []),
                "temp_max": daily.get("temperature_2m_max", []),
                "temp_min": daily.get("temperature_2m_min", []),
                "precipitation": daily.get("precipitation_sum", []),
                "evapotranspiration": daily.get("et0_fao_evapotranspiration", []),
            },
            "source": "Open-Meteo",
            "status": "retrieved",
            "confidence": "high",
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }
        _cache.set(cache_key, result)
        return result

    except requests.exceptions.Timeout:
        log.warning(f"Weather fetch timeout for {lat},{lon}")
        return {"current": None, "forecast_7day": None, "source": "unavailable",
                "status": "fallback", "confidence": "low", "error": "Weather service timed out"}
    except Exception as e:
        log.warning(f"Weather fetch failed: {e}")
        return {"current": None, "forecast_7day": None, "source": "unavailable",
                "status": "fallback", "confidence": "low", "error": "Weather service unavailable"}


def fetch_climate_averages(lat: float, lon: float) -> Dict:
    """
    Fetch climate averages using Open-Meteo's climate/archive data.
    Falls back to latitude-based estimates if unavailable.
    """
    cache_key = f"climate_{lat:.3f}_{lon:.3f}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        # Use recent 90-day archive as a proxy for "typical" conditions
        response = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": _get_date_days_ago(90),
                "end_date": _get_date_days_ago(1),
                "daily": "temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean",
                "timezone": "auto"
            },
            timeout=WEATHER_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        daily = data.get("daily", {})

        temps = [t for t in daily.get("temperature_2m_mean", []) if t is not None]
        precip = [p for p in daily.get("precipitation_sum", []) if p is not None]
        humidity = [h for h in daily.get("relative_humidity_2m_mean", []) if h is not None]

        if not temps:
            raise ValueError("No temperature data returned")

        avg_temp = sum(temps) / len(temps)
        # Annualize rainfall from 90-day sample
        avg_annual_rainfall = (sum(precip) / len(precip)) * 365 if precip else None
        avg_humidity = sum(humidity) / len(humidity) if humidity else None

        result = {
            "temperature": {
                "value": round(avg_temp, 1),
                "unit": "°C",
                "source": "Open-Meteo (90-day archive average)",
                "status": "retrieved",
                "confidence": "high"
            },
            "rainfall": {
                "value": round(avg_annual_rainfall, 1) if avg_annual_rainfall else None,
                "unit": "mm/year",
                "source": "Open-Meteo (90-day archive, annualized)",
                "status": "estimated",
                "confidence": "moderate"
            },
            "humidity": {
                "value": round(avg_humidity, 1) if avg_humidity else None,
                "unit": "%",
                "source": "Open-Meteo (90-day archive average)",
                "status": "retrieved",
                "confidence": "high"
            }
        }
        _cache.set(cache_key, result)
        return result

    except Exception as e:
        log.warning(f"Climate averages fetch failed for {lat},{lon}: {e}")
        # Fallback to latitude-based estimate
        defaults = _latitude_climate_default(lat)
        return {
            "temperature": {
                "value": defaults["temperature"],
                "unit": "°C",
                "source": "Latitude-based regional estimate",
                "status": "fallback",
                "confidence": "low"
            },
            "rainfall": {
                "value": defaults["rainfall"],
                "unit": "mm/year",
                "source": "Latitude-based regional estimate",
                "status": "fallback",
                "confidence": "low"
            },
            "humidity": {
                "value": defaults["humidity"],
                "unit": "%",
                "source": "Latitude-based regional estimate",
                "status": "fallback",
                "confidence": "low"
            }
        }


def _get_date_days_ago(days: int) -> str:
    """Get date string N days ago."""
    from datetime import timedelta
    d = datetime.now(timezone.utc) - timedelta(days=days)
    return d.strftime("%Y-%m-%d")
