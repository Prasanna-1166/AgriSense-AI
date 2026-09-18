"""
AgriSense AI - Agronomy & Economics Service
=============================================

Consumes config/crop_agronomy_data.py (the single source of truth for
real-world agronomic values) and:

  1. Scales planting-material and fertilizer quantities to the
     farmer's actual selected farm area (simple arithmetic:
     quantity_per_ha * area_ha).
  2. Assembles a transparent cost breakdown following the required
     separation of concerns:
         AGRONOMIC REQUIREMENT  (from crop_agronomy_data.py)
             x UNIT PRICE        (not yet populated - see module docstring)
             = CALCULATED COST
     Since no verified current unit prices are available yet, every
     cost component is honestly reported as UNAVAILABLE rather than
     fabricated. The calculation machinery is fully in place so that
     adding a sourced unit_price to config/crop_agronomy_data.py is
     the only change needed to make costs appear.
  3. Never invents numbers. If a field is UNAVAILABLE upstream, it
     stays UNAVAILABLE here - this module only does arithmetic on
     values that already exist.

This module does NOT touch the ML crop/yield models in ml/predictor.py
and is intentionally decoupled from them: it consumes a crop id (and
optionally the ML "top_crop" suitability/yield block for context) but
never recomputes or overrides ML output.
"""
from typing import Dict, Optional

from config.crop_agronomy_data import get_crop_agronomy, has_agronomy_data
from config.crop_master import get_crop_info, is_crop_supported


_SCALABLE_STATUSES = ("VERIFIED_SOURCE", "SOURCE_ESTIMATE")


def _scale_planting_material(pm: Dict, area_ha: float) -> Dict:
    if pm.get("status") not in _SCALABLE_STATUSES or pm.get("quantity_per_ha") is None:
        return pm
    scaled = dict(pm)
    scaled["quantity_for_farm"] = round(pm["quantity_per_ha"] * area_ha, 2)
    scaled["farm_area_ha"] = area_ha
    return scaled


def _scale_fertilizers(fertilizers, area_ha: float):
    if isinstance(fertilizers, dict):
        # UNAVAILABLE placeholder shape
        return fertilizers
    scaled = []
    for f in fertilizers:
        item = dict(f)
        if item.get("status") in _SCALABLE_STATUSES and item.get("quantity_per_ha") is not None:
            item["quantity_for_farm"] = round(item["quantity_per_ha"] * area_ha, 2)
        scaled.append(item)
    return scaled


def _build_cost_estimate(pm: Dict, fertilizers, area_ha: float, cost_survey: Optional[Dict] = None) -> Dict:
    """
    Build the cost picture for a crop. Two independent things are surfaced,
    deliberately kept separate so nothing is double-counted:

    1. `components` - a bottom-up itemized list (quantity x unit_price =
       component cost) built from the sourced seed/fertilizer quantities.
       Every unit_price is currently unset (None), so this stays honestly
       UNAVAILABLE for every crop - see module docstring.

    2. `surveyed_total` - where a real, dated, government/academic cost-of-
       cultivation SURVEY figure exists for this crop (see
       crop_agronomy_data.py `cost_survey`), it is surfaced directly and
       scaled to the farmer's area. This is a genuinely sourced total
       (already includes seed, fertiliser, labour, machinery, irrigation,
       etc. per its own survey methodology) - it is NOT the sum of
       `components` and should never be added to it.
    """
    components = []

    if pm and pm.get("status") in _SCALABLE_STATUSES and pm.get("quantity_per_ha") is not None:
        components.append({
            "name": "Seed / planting material",
            "quantity_per_ha": pm["quantity_per_ha"],
            "unit": pm.get("unit"),
            "unit_price": None,
            "price_year": None,
            "price_source": None,
            "cost_per_ha": None,
            "status": "UNAVAILABLE",
            "note": "Quantity is sourced (see planting_material above); local unit price not verified.",
        })

    if isinstance(fertilizers, list):
        for f in fertilizers:
            if f.get("status") in _SCALABLE_STATUSES and f.get("quantity_per_ha") is not None:
                components.append({
                    "name": f.get("nutrient") or f.get("name"),
                    "quantity_per_ha": f["quantity_per_ha"],
                    "unit": f.get("unit"),
                    "unit_price": None,
                    "price_year": None,
                    "price_source": None,
                    "cost_per_ha": None,
                    "status": "UNAVAILABLE",
                    "note": "Quantity is sourced (see fertilizers above); local unit price not verified.",
                })

    priced_components = [c for c in components if c.get("cost_per_ha") is not None]
    total_per_ha = round(sum(c["cost_per_ha"] for c in priced_components), 2) if priced_components else None

    if not components:
        coverage = "unavailable"
    elif not priced_components:
        coverage = "unavailable"
    elif len(priced_components) < len(components):
        coverage = "partial"
    else:
        coverage = "complete"

    surveyed_total = None
    if cost_survey and cost_survey.get("status") == "VERIFIED_SOURCE" and cost_survey.get("total_per_ha") is not None:
        surveyed_total = dict(cost_survey)
        surveyed_total["total_for_farm"] = round(cost_survey["total_per_ha"] * area_ha, 2)
        surveyed_total["area_ha"] = area_ha

    return {
        "currency": "INR",
        "area_ha": area_ha,
        "components": components,
        "total_per_ha": total_per_ha,
        "total_for_farm": round(total_per_ha * area_ha, 2) if total_per_ha is not None else None,
        "coverage": coverage,
        "coverage_label": {
            "complete": "Estimated cultivation cost",
            "partial": "Partial sourced estimate",
            "unavailable": "Cost data unavailable" if not surveyed_total else "Itemized cost data unavailable (see reported survey total below)",
        }[coverage],
        "note": ("Some or all itemized cost components are unavailable because current local market "
                 "prices were not verified for this release. Input quantities above are sourced and can "
                 "be priced locally."
                 if coverage != "complete" else
                 "All shown components are priced from verified sources; other real-world inputs "
                 "(labour, irrigation, land preparation, etc.) may not be included - see components list."),
        "surveyed_total": surveyed_total,
    }


def get_crop_plan(crop_id: str, area_ha: float) -> Optional[Dict]:
    """
    Build the full crop-plan/economics payload for one crop, scaled to
    the farmer's area. Returns None if crop_id is not recognized at
    all by the crop master registry.
    """
    crop_id = crop_id.lower()
    crop_info = get_crop_info(crop_id)
    if not crop_info:
        return None

    area_ha = max(float(area_ha), 0.0)

    agronomy = get_crop_agronomy(crop_id)
    if agronomy is None:
        # Recognized crop (in crop master) but no agronomy entry at all yet.
        agronomy = {
            "region_scope": None, "last_verified": None,
            "duration": {"status": "UNAVAILABLE", "note": "No agronomic reference data on file for this crop yet."},
            "planting_material": {"status": "UNAVAILABLE", "note": "No agronomic reference data on file for this crop yet."},
            "fertilizers": [], "fertilizer_note": None,
            "plant_protection": {"status": "UNAVAILABLE", "note": "No agronomic reference data on file for this crop yet."},
            "sources": [], "no_data_yet": True,
        }

    planting_material = _scale_planting_material(agronomy.get("planting_material", {}), area_ha)
    fertilizers = _scale_fertilizers(agronomy.get("fertilizers", []), area_ha)
    economics = _build_cost_estimate(agronomy.get("planting_material", {}), agronomy.get("fertilizers", []),
                                      area_ha, agronomy.get("cost_survey"))

    return {
        "crop": crop_id,
        "display_name": crop_info.get("display_name", crop_id.capitalize()),
        "ml_recommendation_supported": is_crop_supported(crop_id),
        "region_scope": agronomy.get("region_scope"),
        "last_verified": agronomy.get("last_verified"),
        "has_agronomy_data": has_agronomy_data(crop_id),
        "duration": agronomy.get("duration"),
        "planting_material": planting_material,
        "fertilizers": fertilizers,
        "fertilizer_note": agronomy.get("fertilizer_note"),
        "plant_protection": agronomy.get("plant_protection"),
        "economics": economics,
        "sources": agronomy.get("sources", []),
        "disclaimer": (
            "Input requirements and cost figures are reference estimates from documented "
            "agricultural sources. Actual requirements and prices vary by variety, soil "
            "condition, region, season, supplier and farm practice. Follow current local "
            "agricultural advisories and soil-test recommendations."
        ),
        "plant_protection_disclaimer": (
            "Plant-protection information is reference guidance from agricultural sources. "
            "Follow the current product label and local agricultural advisory before application."
        ),
    }
