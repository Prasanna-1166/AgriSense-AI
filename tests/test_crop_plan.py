"""
Tests for the Crop Agronomy/Economics layer (crop_agronomy_data.py,
agronomy_service.py, routes/crop_plan.py).

Focus areas per project requirements: no fabricated values, correct
farm-area scaling arithmetic, honest handling of missing data, and
that existing prediction/crop endpoints keep working unmodified.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from config.crop_agronomy_data import CROP_AGRONOMY, get_crop_agronomy, has_agronomy_data
from config.crop_master import CROP_MASTER
from services.agronomy_service import get_crop_plan


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# 1. Crop agronomy data lookup
# ---------------------------------------------------------------------------
def test_agronomy_lookup_returns_entry_for_known_crop():
    assert get_crop_agronomy("rice") is not None


def test_agronomy_lookup_none_for_unknown_crop():
    assert get_crop_agronomy("dragonfruit") is None


def test_every_crop_in_master_registry_has_an_agronomy_entry():
    """Every crop in the Crop Master should at least have a (possibly
    all-UNAVAILABLE) agronomy entry, never a silent KeyError."""
    for crop_id in CROP_MASTER:
        assert get_crop_agronomy(crop_id) is not None or crop_id in (
            "chilli", "tobacco", "wheat", "sugarcane", "turmeric", "groundnut"
        ), f"{crop_id} should have an agronomy entry or be an acknowledged ML-unsupported crop"


# ---------------------------------------------------------------------------
# 2 & 3. Supported crop with complete vs partial data
# ---------------------------------------------------------------------------
def test_rice_has_complete_core_agronomy_fields():
    entry = get_crop_agronomy("rice")
    assert entry["duration"]["status"] == "VERIFIED_SOURCE"
    assert entry["planting_material"]["status"] == "VERIFIED_SOURCE"
    assert len(entry["fertilizers"]) > 0
    assert len(entry["sources"]) > 0


def test_cotton_has_partial_agronomy_data():
    """Cotton has verified fertilizer/seed data but duration and plant
    protection are honestly marked unavailable - a real partial case."""
    entry = get_crop_agronomy("cotton")
    assert entry["planting_material"]["status"] == "VERIFIED_SOURCE"
    assert entry["duration"]["status"] == "UNAVAILABLE"
    assert entry["plant_protection"]["status"] == "UNAVAILABLE"


# ---------------------------------------------------------------------------
# 4. Unsupported crop (no ML) still gets an honest crop-plan response
# ---------------------------------------------------------------------------
def test_unsupported_crop_crop_plan_via_service():
    plan = get_crop_plan("groundnut", area_ha=1.0)
    assert plan is not None
    assert plan["ml_recommendation_supported"] is False


def test_unsupported_crop_crop_plan_via_route_includes_ml_note(client):
    resp = client.get("/api/crop-plan/groundnut")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ml_recommendation_supported"] is False
    assert "ml_support_note" in data


# ---------------------------------------------------------------------------
# 5. Missing cost / 7. Missing fertilizer / 8. Missing pesticide
# ---------------------------------------------------------------------------
def test_no_crop_has_a_fabricated_cost_total():
    """Global honesty check: since no unit prices are verified anywhere
    in this release, NO crop should show a computed total cost."""
    for crop_id in CROP_AGRONOMY:
        plan = get_crop_plan(crop_id, area_ha=1.0)
        econ = plan["economics"]
        assert econ["total_per_ha"] is None, f"{crop_id} unexpectedly has a priced total (should be unavailable)"
        assert econ["coverage"] == "unavailable"


def test_watermelon_has_no_data_yet_and_says_so_honestly():
    plan = get_crop_plan("watermelon", area_ha=1.0)
    assert plan["has_agronomy_data"] is False
    assert plan["duration"]["status"] == "UNAVAILABLE"
    assert plan["planting_material"]["status"] == "UNAVAILABLE"


def test_mungbean_plant_protection_marked_unavailable_not_fabricated():
    entry = get_crop_agronomy("mungbean")
    assert entry["plant_protection"]["status"] == "UNAVAILABLE"


# ---------------------------------------------------------------------------
# Tree/perennial crops: per-plant sourced values, derived per-ha estimates
# ---------------------------------------------------------------------------
def test_mango_fertilizer_per_ha_is_derived_source_estimate_not_verified():
    """Mango N/P/K per-ha figures are DERIVED from a per-tree dose x an
    assumed planting density - they must be tagged SOURCE_ESTIMATE, not
    VERIFIED_SOURCE, since the per-ha number itself isn't independently
    sourced."""
    entry = get_crop_agronomy("mango")
    n = next(f for f in entry["fertilizers"] if f["nutrient"] == "Nitrogen (N)")
    assert n["status"] == "SOURCE_ESTIMATE"
    assert n["quantity_per_plant"] == pytest.approx(1.0)
    assert n["quantity_per_ha"] == pytest.approx(100.0)


def test_mango_planting_material_scales_by_farm_area():
    plan = get_crop_plan("mango", area_ha=2.0)
    pm = plan["planting_material"]
    assert pm["status"] == "VERIFIED_SOURCE"
    assert pm["quantity_for_farm"] == pytest.approx(200.0)


def test_orange_fertilizer_is_per_plant_only_not_fabricated_per_ha():
    """Orange has a verified per-tree dose but no verified planting
    density, so per-ha must stay None rather than being guessed."""
    entry = get_crop_agronomy("orange")
    n = next(f for f in entry["fertilizers"] if f["nutrient"] == "Nitrogen (N)")
    assert n["status"] == "VERIFIED_SOURCE"
    assert n["quantity_per_ha"] is None
    assert n["quantity_per_plant"] == 600


def test_jute_has_verified_duration_and_seed_rate():
    entry = get_crop_agronomy("jute")
    assert entry["duration"]["status"] == "VERIFIED_SOURCE"
    assert entry["planting_material"]["status"] == "VERIFIED_SOURCE"


def test_lentil_fertilizer_available_but_seed_rate_honestly_unavailable():
    entry = get_crop_agronomy("lentil")
    assert entry["fertilizers"][0]["status"] == "VERIFIED_SOURCE"
    assert entry["planting_material"]["status"] == "UNAVAILABLE"


def test_coffee_kidneybeans_mothbeans_muskmelon_watermelon_still_unavailable():
    """Crops explicitly not researched to a verifiable standard in this
    update must still say so honestly, not silently disappear."""
    for crop_id in ("coffee", "kidneybeans", "mothbeans", "muskmelon", "watermelon"):
        assert has_agronomy_data(crop_id) is False


# ---------------------------------------------------------------------------
# 9 & 12. Farm area scaling / seed quantity scaling
# ---------------------------------------------------------------------------
def test_seed_quantity_scales_linearly_with_farm_area():
    plan_1ha = get_crop_plan("rice", area_ha=1.0)
    plan_3ha = get_crop_plan("rice", area_ha=3.0)
    qty_1 = plan_1ha["planting_material"]["quantity_for_farm"]
    qty_3 = plan_3ha["planting_material"]["quantity_for_farm"]
    assert qty_3 == pytest.approx(qty_1 * 3, rel=1e-6)


def test_fertilizer_quantity_scales_linearly_with_farm_area():
    plan_1ha = get_crop_plan("maize", area_ha=1.0)
    plan_2ha = get_crop_plan("maize", area_ha=2.5)
    n_1 = next(f for f in plan_1ha["fertilizers"] if f["nutrient"] == "Nitrogen (N)")
    n_2 = next(f for f in plan_2ha["fertilizers"] if f["nutrient"] == "Nitrogen (N)")
    assert n_2["quantity_for_farm"] == pytest.approx(n_1["quantity_for_farm"] * 2.5, rel=1e-6)


# ---------------------------------------------------------------------------
# 10 & 11. Per-hectare / total farm cost calculation (structure, not fabrication)
# ---------------------------------------------------------------------------
def test_cost_breakdown_structure_present_even_when_unpriced():
    plan = get_crop_plan("rice", area_ha=2.0)
    econ = plan["economics"]
    assert econ["area_ha"] == 2.0
    assert econ["currency"] == "INR"
    assert isinstance(econ["components"], list)
    assert len(econ["components"]) > 0
    for c in econ["components"]:
        assert "quantity_per_ha" in c
        assert "unit_price" in c
        assert "cost_per_ha" in c


# ---------------------------------------------------------------------------
# Reported survey cost (rice/maize/cotton) - real, dated, sourced totals,
# kept separate from the itemized (unpriced) bottom-up components
# ---------------------------------------------------------------------------
def test_rice_has_a_real_surveyed_total_cost():
    plan = get_crop_plan("rice", area_ha=1.0)
    survey = plan["economics"]["surveyed_total"]
    assert survey is not None
    assert survey["status"] == "VERIFIED_SOURCE"
    assert survey["total_per_ha"] == pytest.approx(66985.0)
    assert survey["source"] is not None


def test_surveyed_total_scales_by_farm_area():
    plan = get_crop_plan("cotton", area_ha=3.0)
    survey = plan["economics"]["surveyed_total"]
    assert survey["total_for_farm"] == pytest.approx(survey["total_per_ha"] * 3.0, rel=1e-6)


def test_surveyed_total_never_summed_into_itemized_total():
    """The itemized (unpriced) total_per_ha must stay None even when a
    surveyed_total exists - the two are never added together."""
    plan = get_crop_plan("maize", area_ha=1.0)
    econ = plan["economics"]
    assert econ["total_per_ha"] is None
    assert econ["surveyed_total"]["total_per_ha"] is not None


def test_crops_without_a_survey_have_null_surveyed_total():
    plan = get_crop_plan("chickpea", area_ha=1.0)
    assert plan["economics"]["surveyed_total"] is None


# ---------------------------------------------------------------------------
# 13. Invalid farm area
# ---------------------------------------------------------------------------
def test_invalid_area_ha_rejected_by_route(client):
    resp = client.get("/api/crop-plan/rice?area_ha=notanumber")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 14. Zero / negative farm area
# ---------------------------------------------------------------------------
def test_zero_area_ha_rejected_by_route(client):
    resp = client.get("/api/crop-plan/rice?area_ha=0")
    assert resp.status_code == 400


def test_negative_area_ha_rejected_by_route(client):
    resp = client.get("/api/crop-plan/rice?area_ha=-2")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 15. Missing source metadata never silently invented
# ---------------------------------------------------------------------------
def test_every_verified_field_carries_a_source():
    for crop_id, entry in CROP_AGRONOMY.items():
        if entry.get("no_data_yet"):
            continue
        pm = entry.get("planting_material", {})
        if pm.get("status") == "VERIFIED_SOURCE":
            assert pm.get("source"), f"{crop_id} planting_material VERIFIED_SOURCE with no source"
        for f in entry.get("fertilizers", []) or []:
            if isinstance(f, dict) and f.get("status") == "VERIFIED_SOURCE" and f.get("quantity_per_ha") is not None:
                assert f.get("source"), f"{crop_id} fertilizer entry VERIFIED_SOURCE with no source"


# ---------------------------------------------------------------------------
# 16-22. Existing functionality untouched by this feature
# ---------------------------------------------------------------------------
def test_unknown_crop_route_returns_404(client):
    resp = client.get("/api/crop-plan/not_a_real_crop")
    assert resp.status_code == 404


def test_existing_crops_endpoint_still_works(client):
    resp = client.get("/api/crops")
    assert resp.status_code == 200


def test_existing_health_endpoint_still_works(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_existing_prediction_endpoints_still_registered(client):
    # Missing body should yield a clean 4xx/503, never a 404 (route must exist)
    resp = client.post("/api/predict/quick", json={})
    assert resp.status_code in (400, 422, 503)
    resp = client.post("/api/predict/assisted", json={})
    assert resp.status_code in (400, 422, 503)
    resp = client.post("/api/predict/expert", json={})
    assert resp.status_code in (400, 422, 503)
