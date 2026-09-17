"""
AgriSense AI - Crop routes

Exposes the Crop Master registry and a comparison endpoint.
"""
from flask import Blueprint, jsonify, request

from config.crop_master import CROP_MASTER, list_crops, get_crop_info
from ml.predictor import predict_recommendations, is_ready
from config.settings import CROP_FEATURES

crops_bp = Blueprint("crops", __name__)


@crops_bp.route("/api/crops", methods=["GET"])
def get_crops():
    """List all crops in the Crop Master registry, with data availability status."""
    category = request.args.get("category")
    crops = list_crops(category=category)
    return jsonify({
        "crops": crops,
        "total": len(crops),
        "supported_count": sum(1 for c in crops if c.get("supported_for_recommendation")),
        "unsupported_count": sum(1 for c in crops if not c.get("supported_for_recommendation")),
    }), 200


@crops_bp.route("/api/crops/<crop_id>", methods=["GET"])
def get_crop(crop_id):
    """Get Crop Master info for a specific crop."""
    info = get_crop_info(crop_id)
    if not info:
        return jsonify({"error": f"Unknown crop: {crop_id}"}), 404
    return jsonify(info), 200


@crops_bp.route("/api/crops/compare", methods=["POST"])
def compare_crops():
    """
    Compare specific supported crops for a given set of conditions.
    Body: { feature values..., area_ha, irrigation, crops: [crop_id, ...] }
    """
    if not is_ready():
        return jsonify({"error": "Prediction models are not trained yet."}), 503

    data = request.get_json(silent=True) or {}
    requested_crops = data.get("crops", [])

    if not requested_crops:
        return jsonify({"error": "Provide a list of crop ids to compare in 'crops'."}), 400

    # Separate supported vs unsupported requested crops
    unsupported_requested = [c for c in requested_crops if not get_crop_info(c) or
                              not get_crop_info(c).get("supported_for_recommendation")]

    feature_values = {}
    for feat in CROP_FEATURES:
        if feat not in data:
            return jsonify({"error": f"Missing field: {feat}"}), 400
        try:
            feature_values[feat] = float(data[feat])
        except (TypeError, ValueError):
            return jsonify({"error": f"Invalid value for {feat}"}), 400

    area_ha = float(data.get("area_ha", 1.0))
    irrigation = str(data.get("irrigation", "partial")).lower()

    result = predict_recommendations(feature_values, area_ha, irrigation, top_n=len(CROP_MASTER))

    all_crops_by_id = {c["crop"]: c for c in result["ranked_crops"]}
    comparison = []
    for crop_id in requested_crops:
        if crop_id in all_crops_by_id:
            comparison.append(all_crops_by_id[crop_id])
        else:
            info = get_crop_info(crop_id)
            comparison.append({
                "crop": crop_id,
                "unsupported": True,
                "reason": info.get("reason") if info else "Unknown crop.",
                "real_world_data_note": info.get("real_world_data_note") if info else None,
            })

    return jsonify({
        "comparison": comparison,
        "unsupported_requested": unsupported_requested,
    }), 200
