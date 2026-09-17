"""Tests for soil validation/extraction and rule-based risk service."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from services.soil_service import validate_manual_soil_values, build_no_soil_test_response
from services import soil_extraction_service, risk_service


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_no_soil_data_response_is_explicit():
    resp = build_no_soil_test_response()
    assert resp["available"] is False
    assert "No soil test available" in resp["message"]


def test_validate_manual_soil_values_valid():
    result = validate_manual_soil_values({"ph": 6.5, "N": 80})
    assert "ph" in result["valid"]
    assert result["valid"]["ph"]["status"] == "USER_ENTERED"
    assert len(result["errors"]) == 0


def test_validate_manual_soil_values_rejects_out_of_range():
    result = validate_manual_soil_values({"ph": 25})
    assert "ph" not in result["valid"]
    assert len(result["errors"]) == 1


def test_validate_manual_soil_values_only_uses_supplied_fields():
    """Never invent values for fields the user didn't supply."""
    result = validate_manual_soil_values({"ph": 6.5})
    assert list(result["valid"].keys()) == ["ph"]


def test_soil_validate_endpoint_empty_body_returns_no_test_available(client):
    response = client.post("/api/soil/validate", json={})
    data = response.get_json()
    assert data["available"] is False


def test_upload_validation_rejects_bad_extension():
    result = soil_extraction_service.validate_upload("report.exe", 1000)
    assert result["valid"] is False


def test_upload_validation_rejects_oversized_file():
    result = soil_extraction_service.validate_upload("report.pdf", 100 * 1024 * 1024)
    assert result["valid"] is False


def test_upload_validation_accepts_pdf():
    result = soil_extraction_service.validate_upload("report.pdf", 1000)
    assert result["valid"] is True


def test_extraction_failure_never_fabricates_values():
    """If a file has no extractable soil fields, extraction must report failure, not guess."""
    result = soil_extraction_service.extract_soil_report("/nonexistent/file.pdf")
    assert result["success"] is False
    assert result["extracted"] == {}


# --- Risk service tests ---

def test_rainfall_risk_no_forecast_is_data_unavailable():
    risk = risk_service.assess_rainfall_risk(None, None)
    assert risk["level"] == "Data unavailable"


def test_rainfall_risk_heavy_rain_flagged_high():
    forecast = {"precipitation": [10, 10, 60, 5, 5, 5, 5]}
    risk = risk_service.assess_rainfall_risk(forecast, 1000)
    assert risk["level"] == "High"
    assert risk["rule"] is not None


def test_rainfall_risk_drought_flagged_moderate():
    forecast = {"precipitation": [1, 2, 1, 0, 1, 2, 1]}
    risk = risk_service.assess_rainfall_risk(forecast, 200)
    assert risk["level"] == "Moderate"


def test_temperature_risk_heat_stress():
    forecast = {"temp_max": [38, 39, 42, 37, 36, 35, 34], "temp_min": [24, 25, 26, 23, 22, 21, 20]}
    risk = risk_service.assess_temperature_risk(forecast)
    assert risk["level"] == "High"


def test_data_availability_risk_unsupported_crop():
    risk = risk_service.assess_data_availability_risk("high", crop_supported=False)
    assert risk["level"] == "Data unavailable"


def test_build_risk_summary_returns_four_categories():
    summary = risk_service.build_risk_summary(None, None, "partial", "moderate", True)
    categories = {r["category"] for r in summary}
    assert categories == {"rainfall", "temperature", "irrigation", "data_availability"}
