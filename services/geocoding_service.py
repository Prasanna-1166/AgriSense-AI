"""
Geocoding service for AgriSense AI

Wraps OpenStreetMap Nominatim for location search and reverse geocoding.
Respects Nominatim's usage policy (max ~1 request/second) with self-imposed
rate limiting. Never crashes on API failure - always returns a clear error
that the route layer can handle gracefully.
"""
import logging
import threading
import time
from typing import Dict, List, Optional

import requests

from config.settings import NOMINATIM_BASE_URL, GEOCODE_TIMEOUT, NOMINATIM_RATE_LIMIT

log = logging.getLogger(__name__)

_rate_lock = threading.Lock()
_last_request_time = [0.0]

HEADERS = {
    "User-Agent": "AgriSense-AI/2.0 (educational agricultural application)"
}


def _rate_limit():
    """Enforce Nominatim's fair-use rate limit (self-imposed, ~1 req/sec)."""
    with _rate_lock:
        elapsed = time.time() - _last_request_time[0]
        if elapsed < NOMINATIM_RATE_LIMIT:
            time.sleep(NOMINATIM_RATE_LIMIT - elapsed)
        _last_request_time[0] = time.time()


def search_location(query: str, limit: int = 6) -> Dict:
    """
    Search for a location by name using Nominatim.
    
    Returns:
        Dict with 'results' list and optional 'error' message.
        Never raises - always returns gracefully.
    """
    if not query or not query.strip():
        return {"results": [], "error": "Please enter a location to search."}

    _rate_limit()

    try:
        response = requests.get(
            f"{NOMINATIM_BASE_URL}/search",
            params={
                "q": query.strip(),
                "format": "json",
                "limit": limit,
                "addressdetails": 1,
            },
            headers=HEADERS,
            timeout=GEOCODE_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data:
            try:
                results.append({
                    "display_name": item.get("display_name", ""),
                    "lat": float(item.get("lat")),
                    "lon": float(item.get("lon")),
                    "type": item.get("type", ""),
                    "importance": item.get("importance", 0),
                })
            except (ValueError, TypeError):
                continue

        if not results:
            return {"results": [], "error": "No locations found. Try a different search term or use coordinates directly."}

        return {"results": results, "error": None}

    except requests.exceptions.Timeout:
        log.warning(f"Nominatim search timeout for query: {query}")
        return {"results": [], "error": "Location search timed out. Try entering coordinates manually."}
    except requests.exceptions.RequestException as e:
        log.warning(f"Nominatim search failed: {e}")
        return {"results": [], "error": "Location search is currently unavailable. Try entering coordinates manually."}
    except Exception as e:
        log.error(f"Unexpected geocoding error: {e}")
        return {"results": [], "error": "An unexpected error occurred during search."}


def reverse_geocode(lat: float, lon: float) -> Dict:
    """
    Reverse geocode coordinates to a location name.
    
    Returns:
        Dict with 'result' (display_name info) and optional 'error'.
        Never raises - always returns gracefully.
    """
    _rate_limit()

    try:
        response = requests.get(
            f"{NOMINATIM_BASE_URL}/reverse",
            params={
                "lat": lat,
                "lon": lon,
                "format": "json",
                "zoom": 10,
                "addressdetails": 1,
            },
            headers=HEADERS,
            timeout=GEOCODE_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        if "display_name" in data:
            return {
                "result": {
                    "display_name": data.get("display_name", ""),
                    "address": data.get("address", {}),
                },
                "error": None
            }
        else:
            return {"result": None, "error": "No location name found for these coordinates."}

    except requests.exceptions.Timeout:
        log.warning(f"Nominatim reverse timeout for {lat},{lon}")
        return {"result": None, "error": "Reverse geocoding timed out."}
    except requests.exceptions.RequestException as e:
        log.warning(f"Nominatim reverse failed: {e}")
        return {"result": None, "error": "Reverse geocoding is currently unavailable."}
    except Exception as e:
        log.error(f"Unexpected reverse geocoding error: {e}")
        return {"result": None, "error": "An unexpected error occurred."}
