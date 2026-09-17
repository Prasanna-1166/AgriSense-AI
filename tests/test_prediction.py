"""Tests for prediction routes and input validation."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from utils.validation import validate_feature_values, validate_farm_inputs
from config.settings import CROP_FEATURES


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_validate_feature_values_valid():
    values = {"N": 50, "P": 40, "K": 45, "temperature": 25, "humidity": 70, "ph": 6.5, "rainfall": 200}
    valid, msg, cleaned = validate_feature_values(values, CROP_FEATURES)
    assert valid is True
    assert cleaned["ph"] == 6.5


def test_validate_feature_values_missing():
    values = {"N": 50}
    valid, msg, cleaned = validate_feature_values(values, CROP_FEATURES)
    assert valid is False


def test_validate_feature_values_out_of_range_ph():
    values = {"N": 50, "P": 40, "K": 45, "temperature": 25, "humidity": 70, "ph": 20, "rainfall": 200}
    valid, msg, cleaned = validate_feature_values(values, CROP_FEATURES)
    assert valid is False
    assert "pH" in msg


def test_validate_farm_inputs_defaults():
    valid, msg, cleaned = validate_farm_inputs({})
    assert valid is True
    assert cleaned["area_ha"] == 1.0
    assert cleaned["irrigation"] == "partial"


def test_validate_farm_inputs_invalid_irrigation():
    valid, msg, cleaned = validate_farm_inputs({"irrigation": "maybe"})
    assert valid is False


def test_predict_expert_requires_all_fields(client):
    response = client.post("/api/predict/expert", json={"N": 50})
    assert response.status_code in (400, 503)


def test_predict_quick_requires_coordinates(client):
    response = client.post("/api/predict/quick", json={})
    assert response.status_code == 400


def test_predict_assisted_requires_coordinates(client):
    response = client.post("/api/predict/assisted", json={})
    assert response.status_code == 400


def test_predict_expert_with_valid_data_or_model_not_ready(client):
    """
    If models are trained, this should succeed (200). If not yet trained
    in this test environment, it should fail gracefully with 503 rather
    than crashing.
    """
    payload = {
        "N": 60, "P": 40, "K": 45, "temperature": 26, "humidity": 70,
        "ph": 6.5, "rainfall": 200, "area_ha": 2, "irrigation": "partial"
    }
    response = client.post("/api/predict/expert", json=payload)
    assert response.status_code in (200, 503)
    data = response.get_json()
    if response.status_code == 200:
        assert "top_crop" in data
        assert "ranked_crops" in data
        assert "data_quality" in data
    else:
        assert "error" in data
