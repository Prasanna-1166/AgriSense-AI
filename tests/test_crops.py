"""Tests for the Crop Master registry and crop routes - core honesty checks."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from config.crop_master import (
    CROP_MASTER, SUPPORTED_CROP_IDS, UNSUPPORTED_CROP_IDS,
    is_crop_supported, get_crop_info
)
from ml.predictor import get_models


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_mandatory_priority_crops_present_in_registry():
    """Every mandatory crop from the project brief must appear somewhere in the registry."""
    mandatory = ["rice", "cotton", "chilli", "tobacco", "wheat", "sugarcane", "turmeric", "groundnut", "maize"]
    for crop in mandatory:
        assert get_crop_info(crop) is not None, f"{crop} missing from Crop Master entirely"


def test_unsupported_crops_are_not_fabricated():
    """
    Crops without training data must be explicitly marked unsupported,
    never silently mapped onto model predictions.
    """
    for crop in ["chilli", "tobacco", "wheat", "sugarcane", "turmeric", "groundnut"]:
        assert not is_crop_supported(crop), f"{crop} should NOT be marked supported (no training data for it)"
        info = get_crop_info(crop)
        assert info["data_availability"] == "UNSUPPORTED"
        assert "reason" in info


def test_supported_crops_match_trained_model_classes():
    """
    The registry's supported crop list must match EXACTLY what the trained
    model actually knows - this is the core anti-fabrication check.
    """
    bundle = get_models()
    if bundle.crop_model is None:
        pytest.skip("Crop model not trained in this environment.")
    model_classes = set(bundle.crop_model.classes_)
    registry_supported = set(SUPPORTED_CROP_IDS)
    assert model_classes == registry_supported, (
        f"Mismatch between trained model classes and registry: "
        f"in model only: {model_classes - registry_supported}, "
        f"in registry only: {registry_supported - model_classes}"
    )


def test_crops_endpoint_lists_both_supported_and_unsupported(client):
    response = client.get("/api/crops")
    assert response.status_code == 200
    data = response.get_json()
    assert data["supported_count"] > 0
    assert data["unsupported_count"] > 0


def test_crops_endpoint_unknown_crop_404(client):
    response = client.get("/api/crops/nonexistent_crop")
    assert response.status_code == 404


def test_crops_endpoint_known_unsupported_crop_returns_reason(client):
    response = client.get("/api/crops/chilli")
    assert response.status_code == 200
    data = response.get_json()
    assert data["supported_for_recommendation"] is False
    assert "reason" in data
