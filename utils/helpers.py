"""
Helper utilities for AgriSense AI
"""
import logging
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

log = logging.getLogger(__name__)


def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """Safely serialize object to JSON."""
    try:
        return json.dumps(obj, indent=indent, default=str)
    except Exception as e:
        log.error(f"JSON serialization error: {e}")
        return "{}"


def safe_json_loads(text: str) -> Dict[str, Any]:
    """Safely deserialize JSON."""
    try:
        return json.loads(text)
    except Exception as e:
        log.error(f"JSON deserialization error: {e}")
        return {}


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not isinstance(text, str):
        return str(text)
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with specified decimal places."""
    try:
        return f"{float(value):.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


def get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def generate_prediction_id() -> str:
    """Generate a unique prediction ID."""
    import time
    import hashlib
    content = f"{time.time()}".encode()
    return hashlib.md5(content).hexdigest()[:12]


def get_file_size_mb(filepath: str) -> float:
    """Get file size in MB."""
    if not os.path.exists(filepath):
        return 0.0
    return os.path.getsize(filepath) / (1024 * 1024)


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length."""
    if not isinstance(text, str):
        text = str(text)
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text


def format_confidence(confidence: float) -> str:
    """Format confidence level as human-readable text."""
    if confidence >= 0.8:
        return "High"
    elif confidence >= 0.6:
        return "Moderate"
    elif confidence >= 0.4:
        return "Low"
    else:
        return "Very Low"


def format_data_status(status: str) -> Dict[str, Any]:
    """Format data status with description."""
    status_map = {
        "retrieved": {
            "label": "Retrieved",
            "description": "Fetched from external source",
            "badge_class": "status-retrieved",
            "icon": "✓"
        },
        "estimated": {
            "label": "Estimated",
            "description": "Calculated from location data",
            "badge_class": "status-estimated",
            "icon": "≈"
        },
        "fallback": {
            "label": "Default",
            "description": "Using standard fallback value",
            "badge_class": "status-fallback",
            "icon": "◆"
        },
        "manual": {
            "label": "Manual",
            "description": "Provided by user",
            "badge_class": "status-manual",
            "icon": "✎"
        }
    }
    return status_map.get(status, {
        "label": "Unknown",
        "description": "Unknown data source",
        "badge_class": "status-unknown",
        "icon": "?"
    })


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9/5) + 32


def millimeters_to_inches(mm: float) -> float:
    """Convert millimeters to inches."""
    return mm / 25.4


class MetricsCalculator:
    """Calculate various agricultural metrics."""
    
    @staticmethod
    def calculate_water_requirement(
        predicted_yield_t_per_ha: float,
        rainfall_mm: float,
        crop: str,
        irrigation: str
    ) -> Dict[str, Any]:
        """
        Estimate water requirement based on crop and conditions.
        
        Returns:
            Dict with water requirement info
        """
        # Typical water requirements (mm) for crops
        crop_water_needs = {
            "rice": 1200, "wheat": 450, "maize": 600, "cotton": 700,
            "banana": 1200, "apple": 600, "grapes": 400, "mango": 600,
            "lentil": 200, "chickpea": 300, "coffee": 1500,
        }
        
        typical_need = crop_water_needs.get(crop, 600)
        available_from_rainfall = rainfall_mm
        
        if irrigation == "full":
            additional_needed = max(0, typical_need - available_from_rainfall)
            adequacy = "Rainfall + full irrigation should be adequate"
        elif irrigation == "partial":
            additional_needed = max(0, typical_need - available_from_rainfall * 0.7)
            if additional_needed > 0:
                adequacy = "Partial irrigation recommended"
            else:
                adequacy = "Rainfall appears sufficient with partial irrigation"
        else:  # none
            additional_needed = max(0, typical_need - available_from_rainfall)
            if additional_needed > 200:
                adequacy = "Rainfall may be insufficient - consider irrigation"
            else:
                adequacy = "Rainfall appears adequate for rainfed cultivation"
        
        return {
            "typical_requirement_mm": typical_need,
            "rainfall_mm": rainfall_mm,
            "irrigation_type": irrigation,
            "additional_needed_mm": round(additional_needed, 1),
            "adequacy": adequacy,
            "irrigation_recommended": additional_needed > 100
        }
