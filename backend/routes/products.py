from flask import Blueprint, request, jsonify
from services.recommendation_service import get_recommendations

products_bp = Blueprint('products', __name__)

@products_bp.route('/api/products', methods=['GET'])
def get_recommendations_route():
    persona = request.args.get('persona', '아메카지')
    target_category_filter = request.args.get('category')

    print(f"\n🔍 [추천 요청] 페르소나: {persona}")

    try:
        result = get_recommendations(persona, target_category_filter, request)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"❌ 추천 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500