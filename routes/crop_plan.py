"""
AgriSense AI - Crop Plan / Economics routes

Exposes the new Agricultural Production Planning layer (seed/planting
material requirement, crop duration, fertilizer guidance, plant
protection guidance, and cost breakdown) for a given crop, scaled to
the farmer's selected farm area.

Deliberately a separate endpoint from /api/predict/* (see
docs/architecture.md "Crop Plan Layer"): the ML prediction pipeline
and the agronomy/economics data layer are independent concerns. The
frontend calls this endpoint for the top recommended crop (or any
crop from the Crop Directory) after a prediction has been made.
"""
from flask import Blueprint, jsonify, request

from config.crop_master import get_crop_info
from services.agronomy_service import get_crop_plan

crop_plan_bp = Blueprint("crop_plan", __name__)


@crop_plan_bp.route("/api/crop-plan/<crop_id>", methods=["GET"])
def crop_plan(crop_id):
    """
    Get the crop plan / economics layer for a crop.

    Query params:
        area_ha (float, optional, default 1.0): farm area to scale
            planting-material and fertilizer quantities to.
    """
    crop_info = get_crop_info(crop_id)
    if not crop_info:
        return jsonify({"error": f"Unknown crop: {crop_id}"}), 404

    try:
        area_ha = float(request.args.get("area_ha", 1.0))
    except (TypeError, ValueError):
        return jsonify({"error": "area_ha must be a number."}), 400

    if area_ha <= 0:
        return jsonify({"error": "area_ha must be a positive number."}), 400

    plan = get_crop_plan(crop_id, area_ha)
    if plan is None:
        return jsonify({"error": f"Unknown crop: {crop_id}"}), 404

    # Always be explicit about ML support status alongside agronomic data,
    # per the honesty rule: "ML recommendation unavailable" must never be
    # confused with "no agronomic reference information".
    if not crop_info.get("supported_for_recommendation"):
        plan["ml_support_note"] = crop_info.get(
            "reason", "This crop does not have a validated ML recommendation/yield estimate."
        )

    return jsonify(plan), 200
