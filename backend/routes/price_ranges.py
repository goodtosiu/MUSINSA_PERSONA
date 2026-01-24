from flask import Blueprint, jsonify
from services.price_service import get_price_ranges

price_ranges_bp = Blueprint('price_ranges', __name__)

@price_ranges_bp.route('/api/price-ranges', methods=['GET'])
def get_price_ranges_route():
    result = get_price_ranges()

    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)