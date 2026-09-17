"""Tests for environment/soil/weather service fallback behavior."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import soil_service, weather_service, environment_service


def test_regional_npk_estimate_returns_values():
    result = soil_service._regional_npk_estimate(20.0, 78.0)
    assert "N" in result and "P" in result and "K" in result
    assert all(isinstance(v, (int, float)) for v in result.values())


def test_soil_type_estimate_never_raises():
    # Should return a string for any valid coordinate, even far from land
    result = soil_service.get_soil_type_estimate(85.0, 0.0)
    assert isinstance(result, str)


def test_latitude_climate_default_reasonable():
    tropical = weather_service._latitude_climate_default(5.0)
    polar = weather_service._latitude_climate_default(75.0)
    assert tropical["temperature"] > polar["temperature"]


def test_compute_data_quality_handles_empty_profile():
    quality = environment_service.compute_data_quality({})
    assert quality["overall"] in ("low", "moderate", "high")


def test_compute_data_quality_with_mixed_sources():
    profile = {
        "climate": {
            "temperature": {"status": "retrieved"},
            "rainfall": {"status": "estimated"},
            "humidity": {"status": "retrieved"},
        },
        "soil": {
            "N": {"status": "fallback"},
            "P": {"status": "fallback"},
            "K": {"status": "fallback"},
            "ph": {"status": "estimated"},
        }
    }
    quality = environment_service.compute_data_quality(profile)
    assert quality["overall"] == "low"  # fallback present -> low confidence


def test_merge_with_user_overrides_prioritizes_manual():
    profile = {
        "climate": {"temperature": {"value": 20, "status": "retrieved"}},
        "soil": {"N": {"value": 40, "status": "fallback"}}
    }
    merged = environment_service.merge_with_user_overrides(profile, {"temperature": 30})
    assert merged["temperature"]["value"] == 30
    assert merged["temperature"]["status"] == "manual"
    assert merged["N"]["value"] == 40  # untouched, stays as-is
