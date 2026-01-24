import os
import numpy as np
import pandas as pd
from utils.data_loader import get_master_data
from utils.db import get_engine
from utils.image_processor import process_and_save_image
from config import CATEGORY_MAP, PROCESSED_DIR

def get_representative_items(engine, persona):
    """
    representative_item 테이블에서 페르소나의 대표 상품 ID 리스트를 가져옵니다.

    Args:
        engine: SQLAlchemy 엔진
        persona (str): 페르소나 이름

    Returns:
        list: 대표 상품 ID 리스트

    Raises:
        ValueError: 대표 상품이 없을 경우
    """
    query = "SELECT product_id FROM representative_item WHERE persona = %s"
    rep_items_df = pd.read_sql(query, engine, params=(persona,))

    if rep_items_df.empty:
        raise ValueError(f"페르소나 '{persona}'에 해당하는 대표 상품이 없습니다.")

    return rep_items_df['product_id'].tolist()

def find_representative_indices(master_data, representative_ids):
    """
    대표 상품 ID들을 master_data에서 인덱스로 변환합니다.

    Args:
        master_data (dict): 마스터 데이터
        representative_ids (list): 대표 상품 ID 리스트

    Returns:
        tuple: (representative_indices, missing_ids)
    """
    id_to_idx = {int(pid): idx for idx, pid in enumerate(master_data['ids'])}
    representative_indices = []
    missing_ids = []

    for rep_id in representative_ids:
        rep_id_int = int(rep_id)
        if rep_id_int in id_to_idx:
            representative_indices.append(id_to_idx[rep_id_int])
        else:
            missing_ids.append(rep_id_int)

    return representative_indices, missing_ids

def calculate_similarity_scores(master_data, representative_indices):
    """
    각 대표 상품에 대해 전체 상품과의 유사도 점수를 계산합니다.

    Args:
        master_data (dict): 마스터 데이터
        representative_indices (list): 대표 상품 인덱스 리스트

    Returns:
        dict: {product_id: max_similarity_score}
    """
    all_candidate_indices = {}

    for rep_idx in representative_indices:
        rep_id = int(master_data['ids'][rep_idx])
        rep_name = str(master_data['names'][rep_idx])

        # 전체 상품과의 유사도 계산
        sim_name = np.dot(master_data['name_vecs'], master_data['name_vecs'][rep_idx])
        sim_brand = np.dot(master_data['brand_vecs'], master_data['brand_vecs'][rep_idx])
        sim_img = np.dot(master_data['img_vecs'], master_data['img_vecs'][rep_idx])
        sim_cat = np.dot(master_data['cat_vecs'], master_data['cat_vecs'][rep_idx])

        final_scores = (sim_name * 0.1) + (sim_brand * 0.2) + (sim_img * 0.6) + (sim_cat * 0.1)

        # 대표 상품 자체는 제외
        final_scores[rep_idx] = -1.0

        # 상위 10개 선택
        top_indices = np.argsort(final_scores)[::-1][:10]

        for candidate_idx in top_indices:
            candidate_id = int(master_data['ids'][candidate_idx])
            candidate_score = final_scores[candidate_idx]

            # 이미 후보에 있으면 더 높은 점수로 업데이트
            if candidate_id not in all_candidate_indices:
                all_candidate_indices[candidate_id] = candidate_score
            else:
                all_candidate_indices[candidate_id] = max(all_candidate_indices[candidate_id], candidate_score)

        print(f"   🎯 {rep_name[:30]}... -> 후보 {len(top_indices)}개 추가")

    return all_candidate_indices

def categorize_candidates(master_data, all_candidate_indices):
    """
    후보 상품들을 카테고리별로 분류합니다.

    Args:
        master_data (dict): 마스터 데이터
        all_candidate_indices (dict): 후보 상품들 {product_id: score}

    Returns:
        dict: 카테고리별 후보 상품들
    """
    candidates_by_category = {eng_key: [] for eng_key in CATEGORY_MAP.keys()}

    id_to_idx = {int(pid): idx for idx, pid in enumerate(master_data['ids'])}

    for candidate_id, score in all_candidate_indices.items():
        if candidate_id in id_to_idx:
            candidate_idx = id_to_idx[candidate_id]
            category_kor = str(master_data['cats'][candidate_idx])

            # 영어 카테고리 키로 변환
            for eng_key, kor_val in CATEGORY_MAP.items():
                if category_kor == kor_val:
                    candidates_by_category[eng_key].append({
                        'id': candidate_id,
                        'idx': candidate_idx,
                        'score': score
                    })
                    break

    return candidates_by_category

def select_random_items(master_data, candidates_by_category, target_category_filter=None, request=None):
    """
    카테고리별로 랜덤하게 아이템을 선택하고 이미지 처리합니다.

    Args:
        master_data (dict): 마스터 데이터
        candidates_by_category (dict): 카테고리별 후보 상품들
        target_category_filter (str, optional): 특정 카테고리만 필터링
        request: Flask request 객체 (이미지 URL 생성용)

    Returns:
        dict: 최종 추천 결과
    """
    final_response = {
        "persona": "",  # 호출 시점에 설정
        "current_outfit_id": None,
        "items": {}
    }

    for eng_key, kor_val in CATEGORY_MAP.items():
        if target_category_filter and target_category_filter != eng_key:
            final_response["items"][eng_key] = []
            continue

        category_candidates = candidates_by_category[eng_key]

        if not category_candidates:
            print(f"   ⚠️ {kor_val} 카테고리에 후보가 없습니다.")
            final_response["items"][eng_key] = []
            continue

        # 랜덤으로 5개 선택 (후보가 5개 미만이면 모두 선택)
        num_select = min(5, len(category_candidates))
        selected_candidates = np.random.choice(len(category_candidates), num_select, replace=False)

        items_list = []
        for sel_idx in selected_candidates:
            candidate = category_candidates[sel_idx]
            original_idx = candidate['idx']
            p_id = candidate['id']
            p_name = str(master_data['names'][original_idx])
            score = candidate['score']

            print(f"      ✨ [{kor_val}] {p_name[:30]}... | 점수: {score:.4f}")

            processed_filename = f"nobg_{p_id}.png"
            processed_file_path = os.path.join(PROCESSED_DIR, processed_filename)

            if os.path.exists(processed_file_path):
                final_img_url = f"{request.host_url}static/processed_imgs/{processed_filename}"
            else:
                success = process_and_save_image(master_data['imgs'][original_idx], processed_file_path)
                final_img_url = f"{request.host_url}static/processed_imgs/{processed_filename}" if success else master_data['imgs'][original_idx]

            items_list.append({
                "product_id": p_id,
                "product_name": p_name,
                "price": int(master_data['prices'][original_idx]),
                "img_url": final_img_url,
                "category": kor_val,
            })

        final_response["items"][eng_key] = items_list

    return final_response

def get_recommendations(persona, target_category_filter=None, request=None):
    """
    페르소나 기반 상품 추천을 수행합니다.

    Args:
        persona (str): 페르소나 이름
        target_category_filter (str, optional): 특정 카테고리 필터
        request: Flask request 객체

    Returns:
        dict: 추천 결과

    Raises:
        ValueError: 데이터 로드 실패 또는 페르소나 없음
    """
    master_data = get_master_data()
    if not master_data:
        raise ValueError("Server data not loaded")

    engine = get_engine()

    try:
        # 1. 대표 상품 가져오기
        representative_ids = get_representative_items(engine, persona)
        print(f"📋 대표 상품 {len(representative_ids)}개 발견")

        # 2. 인덱스 변환
        representative_indices, missing_ids = find_representative_indices(master_data, representative_ids)

        if missing_ids:
            print(f"⚠️ master_data에서 찾지 못한 ID: {missing_ids[:5]}{'...' if len(missing_ids) > 5 else ''} (총 {len(missing_ids)}개)")

        if not representative_indices:
            raise ValueError("No valid representative items found in master data")

        print(f"✅ 유효한 대표 상품 {len(representative_indices)}개 확인")

        # 3. 유사도 계산
        all_candidate_indices = calculate_similarity_scores(master_data, representative_indices)
        print(f"📊 총 후보 상품: {len(all_candidate_indices)}개")

        # 4. 카테고리별 분류
        candidates_by_category = categorize_candidates(master_data, all_candidate_indices)

        # 5. 랜덤 선택 및 결과 생성
        final_response = select_random_items(master_data, candidates_by_category, target_category_filter, request)
        final_response["persona"] = persona

        print(f"✅ 추천 결과 생성 완료 (페르소나: {persona})")
        return final_response

    except Exception as e:
        print(f"❌ 추천 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        raise