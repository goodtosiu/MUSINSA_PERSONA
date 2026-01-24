from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from utils.db import get_engine

def create_outfit(persona, items):
    """
    선택된 아이템들로 아웃핏을 생성하여 데이터베이스에 저장합니다.

    Args:
        persona (str): 페르소나 이름
        items (list): 선택된 아이템 리스트 [{"category": "top", "product_id": 123}, ...]

    Returns:
        tuple: (success: bool, message: str, status_code: int)
    """
    if not persona or not isinstance(persona, str):
        return False, "persona is required", 400

    if not isinstance(items, list):
        return False, "items must be a list", 400

    by_cat = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        cat = it.get('category')
        pid = it.get('product_id')
        if cat in ['outer', 'top', 'bottom', 'shoes', 'acc'] and pid is not None:
            try:
                by_cat[cat] = int(pid)
            except Exception:
                pass

    # 필수 아이템 검증
    if 'top' not in by_cat or 'bottom' not in by_cat or 'shoes' not in by_cat:
        return False, "top, bottom, shoes are required", 400

    # 선택 아이템은 0으로 설정 (더미 상품 ID)
    outer_id = int(by_cat.get('outer', 0))
    acc_id = int(by_cat.get('acc', 0))
    top_id = int(by_cat['top'])
    bottom_id = int(by_cat['bottom'])
    shoes_id = int(by_cat['shoes'])

    stmt = text("""
        INSERT INTO outfit (persona, outer_id, acc_id, top_id, bottom_id, shoes_id)
        VALUES (:persona, :outer_id, :acc_id, :top_id, :bottom_id, :shoes_id)
    """)

    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(stmt, {
                "persona": persona,
                "outer_id": outer_id,
                "acc_id": acc_id,
                "top_id": top_id,
                "bottom_id": bottom_id,
                "shoes_id": shoes_id
            })
        return True, "", 201
    except IntegrityError:
        return False, "duplicate outfit or invalid product_id", 409
    except Exception as e:
        return False, str(e), 500