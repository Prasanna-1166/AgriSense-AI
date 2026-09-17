"""Tests for location search/reverse geocoding routes and validation."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from utils.validation import validate_coordinates


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_validate_coordinates_valid():
    valid, msg = validate_coordinates(20.5937, 78.9629)
    assert valid is True


def test_validate_coordinates_invalid_lat():
    valid, msg = validate_coordinates(200, 78.9629)
    assert valid is False
    assert "Latitude" in msg


def test_validate_coordinates_invalid_lon():
    valid, msg = validate_coordinates(20.5937, 400)
    assert valid is False
    assert "Longitude" in msg


def test_search_requires_query(client):
    response = client.get("/api/location/search")
    assert response.status_code == 400


def test_reverse_requires_coordinates(client):
    response = client.get("/api/location/reverse")
    assert response.status_code == 400


def test_reverse_rejects_invalid_coordinates(client):
    response = client.get("/api/location/reverse?lat=999&lon=999")
    assert response.status_code == 400


def test_states_endpoint_includes_ap_and_telangana(client):
    response = client.get("/api/location/states")
    assert response.status_code == 200
    data = response.get_json()
    assert "Andhra Pradesh" in data["states"]
    assert "Telangana" in data["states"]


def test_districts_endpoint_requires_state(client):
    response = client.get("/api/location/districts")
    assert response.status_code == 400


def test_districts_endpoint_ap_has_full_list(client):
    response = client.get("/api/location/districts?state=Andhra Pradesh")
    data = response.get_json()
    assert len(data["districts"]) > 20  # AP has 26 districts post-2022 reorganization


def test_resolve_requires_coordinates(client):
    response = client.get("/api/location/resolve")
    assert response.status_code == 400
