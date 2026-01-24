from flask import Blueprint, request, jsonify
from services.outfit_service import create_outfit

outfit_bp = Blueprint('outfit', __name__)

@outfit_bp.route('/api/outfit', methods=['POST'])
def create_outfit_route():
    """
    Frontend payload example:
    {
      "persona": "아메카지",
      "items": [
        {"category":"top","product_id":123},
        {"category":"bottom","product_id":456},
        {"category":"shoes","product_id":789},
        {"category":"outer","product_id":111},   // optional
        {"category":"acc","product_id":222}      // optional
      ]
    }

    Rules:
    - top/bottom/shoes are required
    - outer/acc are optional; if missing, store 0 (dummy product_id meaning "None")
    - outfit table should enforce uniqueness via UNIQUE(outer_id, top_id, bottom_id, shoes_id, acc_id)
    """
    payload = request.get_json(silent=True) or {}
    persona = payload.get('persona')
    items = payload.get('items', [])

    success, message, status_code = create_outfit(persona, items)

    if success:
        return jsonify({"ok": True}), status_code
    else:
        return jsonify({"ok": False, "error": message}), status_code