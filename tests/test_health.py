"""Tests for the health check endpoint."""
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


def test_health_endpoint_exists(client):
    response = client.get("/api/health")
    assert response.status_code in (200, 503)


def test_health_endpoint_returns_json(client):
    response = client.get("/api/health")
    data = response.get_json()
    assert "status" in data
    assert "models" in data
    assert "app" in data


def test_health_reports_model_status(client):
    response = client.get("/api/health")
    data = response.get_json()
    assert "crop_model_loaded" in data["models"]
    assert "yield_model_loaded" in data["models"]
    assert "ready" in data["models"]
