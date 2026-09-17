"""Tests for farm profile persistence and Current Farm Mode."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_farm_profile_starts_empty_or_persists(client):
    response = client.get("/api/farm/profile")
    assert response.status_code == 200
    data = response.get_json()
    assert "exists" in data


def test_farm_profile_save_and_retrieve(client):
    payload = {"area_ha": 2.5, "irrigation": "partial", "state": "Andhra Pradesh", "district": "Guntur"}
    save_resp = client.post("/api/farm/profile", json=payload)
    assert save_resp.status_code == 200

    get_resp = client.get("/api/farm/profile")
    data = get_resp.get_json()
    assert data["exists"] is True
    assert data["profile"]["district"] == "Guntur"

    # cleanup
    client.delete("/api/farm/profile")


def test_farm_profile_delete(client):
    client.post("/api/farm/profile", json={"area_ha": 1})
    del_resp = client.delete("/api/farm/profile")
    assert del_resp.status_code == 200
    get_resp = client.get("/api/farm/profile")
    assert get_resp.get_json()["exists"] is False


def test_farm_profile_rejects_empty_body(client):
    response = client.post("/api/farm/profile", json={})
    assert response.status_code == 400


def test_current_farm_requires_current_crop(client):
    response = client.post("/api/farm/analyze-current", json={"lat": 16.5, "lon": 80.6})
    assert response.status_code == 400


def test_current_farm_requires_coordinates(client):
    response = client.post("/api/farm/analyze-current", json={"current_crop": "rice"})
    assert response.status_code == 400


def test_current_farm_unknown_crop_404(client):
    response = client.post("/api/farm/analyze-current", json={
        "lat": 16.5, "lon": 80.6, "current_crop": "unicorn_fruit"
    })
    assert response.status_code == 404


def test_current_farm_unsupported_mandatory_crop_returns_honest_message(client):
    """
    Chilli has no validated model - the endpoint must say so explicitly
    rather than returning a fabricated suitability/yield.
    """
    response = client.post("/api/farm/analyze-current", json={
        "lat": 16.5, "lon": 80.6, "current_crop": "chilli", "area_ha": 1, "irrigation": "partial"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["suitability_available"] is False
    assert data["yield_available"] is False
    assert "message" in data
    assert "crop_analysis" not in data
