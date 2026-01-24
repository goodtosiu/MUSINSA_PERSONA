import numpy as np
from utils.data_loader import get_master_data
from config import CATEGORY_MAP

def get_price_ranges():
    """
    master_data에서 카테고리별 가격 범위를 계산합니다.

    Returns:
        dict: 카테고리별 가격 범위 또는 에러 메시지
    """
    master_data = get_master_data()
    if not master_data:
        return {"error": "Data not loaded"}

    category_price_ranges = {}

    for eng_key, kor_val in CATEGORY_MAP.items():
        cat_mask = (master_data['cats'] == kor_val)
        all_prices_in_cat = master_data['prices'][cat_mask]

        if len(all_prices_in_cat) > 0:
            category_price_ranges[eng_key] = {
                "min": int(np.min(all_prices_in_cat)),
                "max": int(np.max(all_prices_in_cat))
            }
        else:
            category_price_ranges[eng_key] = {"min": 0, "max": 0}

    return category_price_ranges