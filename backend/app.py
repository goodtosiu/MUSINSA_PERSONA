import os
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import create_engine
import requests
from io import BytesIO
from PIL import Image
from rembg import remove
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# [설정]
master_data = {}
PROCESSED_DIR = os.path.join(os.getcwd(), "static", "processed_imgs")
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ---------------------------------------------------------
# [초기화] 데이터 로드
# ---------------------------------------------------------
def init_data():
    global master_data
    try:
        path = '../data/master_data.npz'
        if not os.path.exists(path):
            print(f"🚨 [오류] {path} 파일 없음")
            return
        data = np.load(path, allow_pickle=True)
        required_keys = ['ids', 'names', 'prices', 'imgs', 'cats', 
                         'name_vecs', 'brand_vecs', 'img_vecs', 'cat_vecs']
        temp_data = {}
        for key in required_keys:
            if key not in data:
                print(f"❌ [키 누락] {key}")
                return
            
            val = data[key]
            if key.endswith('_vecs'):
                try:
                    if val.dtype == object or isinstance(val, list):
                        temp_data[key] = np.array([np.array(x, dtype=np.float32) for x in val])
                    else:
                        temp_data[key] = val.astype(np.float32)
                except Exception:
                    temp_data[key] = val
            else:
                temp_data[key] = val
                
        master_data = temp_data
        print(f"✅ 데이터 로드 완료! (총 {len(master_data['ids'])}개)")
    except Exception as e:
        print(f"❌ 데이터 로딩 에러: {e}")

init_data()

# localhost
db_url = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)

# ---------------------------------------------------------
# [신규 API] master_data(npz)에서 카테고리별 가격 범위 추출
# ---------------------------------------------------------
@app.route('/api/price-ranges', methods=['GET'])
def get_price_ranges():
    if not master_data:
        return jsonify({"error": "Data not loaded"}), 500

    CATEGORY_MAP = {"outer": "아우터", "top": "상의", "bottom": "바지", "shoes": "신발", "acc": "액세서리"}
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

    return jsonify(category_price_ranges)

# ---------------------------------------------------------
# [기능] 누끼 따기 및 저장 함수
# ---------------------------------------------------------
def process_and_save_image(image_url, save_path):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            input_image = Image.open(BytesIO(response.content)).convert("RGBA")
            output_image = remove(input_image)
            output_image.save(save_path, format="PNG")
            return True
        else:
            return False
    except Exception as e:
        print(f"   ⚠️ 누끼 에러: {e}")
        return False

# ---------------------------------------------------------
# [API] 추천 상품 반환 (기존 버전 - 주석 처리)
# ---------------------------------------------------------
# @app.route('/api/products', methods=['GET'])
# def get_recommendations_old():
#     persona = request.args.get('persona', '아메카지')
#     fixed_outfit_id = request.args.get('outfit_id')
#     target_category_filter = request.args.get('category') 
#     
#     print(f"\n🔍 [추천 요청] 페르소나: {persona}, OutfitID: {fixed_outfit_id or '랜덤'}")

#     if not master_data: 
#         return jsonify({"error": "Server data not loaded"}), 500

#     try:
#         with engine.connect() as conn:
#             if fixed_outfit_id:
#                 selected_outfit = int(fixed_outfit_id)
#             else:
#                 outfit_query = "SELECT DISTINCT outfit FROM persona_item WHERE persona = %s"
#                 outfits_df = pd.read_sql(outfit_query, conn, params=(persona,))
#                 if outfits_df.empty: 
#                     print(f"❌ 페르소나 '{persona}'에 해당하는 코디가 없습니다.")
#                     return jsonify({"error": "Persona not found"}), 404
#                 selected_outfit = int(np.random.choice(outfits_df['outfit'].tolist()))

#             print(f"👗 선택된 코디 ID: {selected_outfit}")
#             item_query = "SELECT product_id FROM persona_item WHERE persona = %s AND outfit = %s"
#             target_ids = pd.read_sql(item_query, conn, params=(persona, selected_outfit))['product_id'].tolist()
#             
#             if not target_ids: return jsonify({"error": "Invalid Outfit ID"}), 404

#         target_indices = np.where(np.isin(master_data['ids'], target_ids))[0]
#         target_item_map = {master_data['cats'][idx]: idx for idx in target_indices}

#         CATEGORY_MAP = {"outer": "아우터", "top": "상의", "bottom": "바지", "shoes": "신발", "acc": "액세서리"}

#         final_response = { 
#             "current_outfit_id": selected_outfit, 
#             "items": {} 
#         }

#         for eng_key, kor_val in CATEGORY_MAP.items():
#             if target_category_filter and target_category_filter != eng_key:
#                 continue

#             if kor_val not in target_item_map:
#                 print(f"   ⚠️ {kor_val} 카테고리에 해당하는 기본 아이템이 없습니다.")
#                 final_response["items"][eng_key] = [] 
#                 continue

#             target_idx = target_item_map[kor_val]
#             
#             # [추가] 기준 상품(Target) 정보 출력
#             target_name = master_data['names'][target_idx]
#             print(f"   🎯 카테고리 분석: {kor_val}")
#             print(f"      기준 상품: {target_name} (ID: {master_data['ids'][target_idx]})")

#             cat_min = request.args.get(f'min_{eng_key}', type=int)
#             cat_max = request.args.get(f'max_{eng_key}', type=int)
#             
#             if cat_min or cat_max:
#                 print(f"      필터 적용: {cat_min or 0} ~ {cat_max or '무제한'}원")

#             sim_name = np.dot(master_data['name_vecs'], master_data['name_vecs'][target_idx])
#             sim_brand = np.dot(master_data['brand_vecs'], master_data['brand_vecs'][target_idx])
#             sim_img = np.dot(master_data['img_vecs'], master_data['img_vecs'][target_idx])
#             sim_cat = np.dot(master_data['cat_vecs'], master_data['cat_vecs'][target_idx])

#             final_scores = (sim_name * 0.1) + (sim_brand * 0.1) + (sim_img * 0.6) + (sim_cat * 0.1)

#             price_mask = np.ones(len(master_data['prices']), dtype=bool)
#             if cat_min is not None:
#                 price_mask &= (master_data['prices'] >= cat_min)
#             if cat_max is not None:
#                 price_mask &= (master_data['prices'] <= cat_max)

#             combined_mask = (master_data['cats'] == kor_val) & price_mask
#             cat_scores = final_scores[combined_mask]
#             cat_real_indices = np.where(combined_mask)[0]
#             
#             if len(cat_scores) == 0:
#                 print(f"      ❌ 가격 조건에 맞는 {kor_val} 상품이 없습니다.")
#                 final_response["items"][eng_key] = []
#                 continue

#             # 유사도 기반 정렬 및 상위 5개 선택
#             sorted_indices = np.argsort(cat_scores)[::-1][:100]
#             selected_local = np.random.choice(sorted_indices, min(5, len(sorted_indices)), replace=False)
#             
#             items_list = []
#             for loc_idx in selected_local:
#                 original_idx = cat_real_indices[loc_idx]
#                 score = cat_scores[loc_idx]
#                 p_id = int(master_data['ids'][original_idx])
#                 p_name = str(master_data['names'][original_idx])
#                 
#                 # [추가] 추천 후보별 유사도 점수 및 상품명 출력
#                 print(f"      ✨ 추천 후보: {p_name[:30]}... | 점수: {score:.4f}")

#                 processed_filename = f"nobg_{p_id}.png"
#                 processed_file_path = os.path.join(PROCESSED_DIR, processed_filename)
#                 
#                 if os.path.exists(processed_file_path):
#                     final_img_url = f"{request.host_url}static/processed_imgs/{processed_filename}"
#                 else:
#                     success = process_and_save_image(master_data['imgs'][original_idx], processed_file_path)
#                     final_img_url = f"{request.host_url}static/processed_imgs/{processed_filename}" if success else master_data['imgs'][original_idx]

#                 items_list.append({
#                     "product_id": p_id,
#                     "product_name": p_name,
#                     "price": int(master_data['prices'][original_idx]),
#                     "img_url": final_img_url,
#                     "category": kor_val,
#                 })
#             final_response["items"][eng_key] = items_list

#         print(f"✅ 추천 결과 생성 완료 (Outfit ID: {selected_outfit})")
#         return jsonify(final_response)
#     except Exception as e:
#         print(f"❌ 추천 에러 발생: {e}")
#         return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------
# [API] 추천 상품 반환 (새 버전 - representative_item 기반)
# ---------------------------------------------------------
@app.route('/api/products', methods=['GET'])
def get_recommendations():
    persona = request.args.get('persona', '아메카지')
    target_category_filter = request.args.get('category')
    
    print(f"\n🔍 [추천 요청] 페르소나: {persona}")

    if not master_data: 
        return jsonify({"error": "Server data not loaded"}), 500

    try:
        # 1. representative_item 테이블에서 해당 페르소나의 대표 상품 ID 리스트 가져오기
        with engine.connect() as conn:
            query = "SELECT product_id FROM representative_item WHERE persona = %s"
            rep_items_df = pd.read_sql(query, conn, params=(persona,))
            
            if rep_items_df.empty:
                print(f"❌ 페르소나 '{persona}'에 해당하는 대표 상품이 없습니다.")
                return jsonify({"error": "Persona not found"}), 404
            
            representative_ids = rep_items_df['product_id'].tolist()
            print(f"📋 대표 상품 {len(representative_ids)}개 발견")
        
        # 2. master_data에서 대표 상품들의 인덱스 찾기
        id_to_idx = {int(pid): idx for idx, pid in enumerate(master_data['ids'])}
        representative_indices = []
        missing_ids = []
        
        for rep_id in representative_ids:
            rep_id_int = int(rep_id)
            if rep_id_int in id_to_idx:
                representative_indices.append(id_to_idx[rep_id_int])
            else:
                missing_ids.append(rep_id_int)
        
        if missing_ids:
            print(f"⚠️ master_data에서 찾지 못한 ID: {missing_ids[:5]}{'...' if len(missing_ids) > 5 else ''} (총 {len(missing_ids)}개)")
        
        if not representative_indices:
            return jsonify({"error": "No valid representative items found in master data"}), 404
        
        print(f"✅ 유효한 대표 상품 {len(representative_indices)}개 확인")
        
        # 3. 각 대표 상품에 대해 유사도 계산하여 상위 3개씩 찾기
        all_candidate_indices = {}  # {product_id: max_similarity_score} 형식으로 저장
        total_products = len(master_data['ids'])
        
        for rep_idx in representative_indices:
            rep_id = int(master_data['ids'][rep_idx])
            rep_name = str(master_data['names'][rep_idx])
            
            # 전체 상품과의 유사도 계산
            sim_name = np.dot(master_data['name_vecs'], master_data['name_vecs'][rep_idx])
            sim_brand = np.dot(master_data['brand_vecs'], master_data['brand_vecs'][rep_idx])
            sim_img = np.dot(master_data['img_vecs'], master_data['img_vecs'][rep_idx])
            sim_cat = np.dot(master_data['cat_vecs'], master_data['cat_vecs'][rep_idx])
            
            final_scores = (sim_name * 0.1) + (sim_brand * 0.1) + (sim_img * 0.6) + (sim_cat * 0.1)
            
            # 대표 상품 자체는 제외
            final_scores[rep_idx] = -1.0
            
            # 상위 3개 선택
            top_3_indices = np.argsort(final_scores)[::-1][:3]
            
            for candidate_idx in top_3_indices:
                candidate_id = int(master_data['ids'][candidate_idx])
                candidate_score = final_scores[candidate_idx]
                
                # 이미 후보에 있으면 더 높은 점수로 업데이트
                if candidate_id not in all_candidate_indices:
                    all_candidate_indices[candidate_id] = candidate_score
                else:
                    all_candidate_indices[candidate_id] = max(all_candidate_indices[candidate_id], candidate_score)
            
            print(f"   🎯 {rep_name[:30]}... -> 후보 {len(top_3_indices)}개 추가")
        
        print(f"📊 총 후보 상품: {len(all_candidate_indices)}개")
        
        # 4. 후보 상품을 카테고리별로 분류
        CATEGORY_MAP = {"outer": "아우터", "top": "상의", "bottom": "바지", "shoes": "신발", "acc": "액세서리"}
        candidates_by_category = {eng_key: [] for eng_key in CATEGORY_MAP.keys()}
        
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
        
        # 5. 카테고리별로 5개씩 랜덤 선택
        final_response = {
            "persona": persona,
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
        
        print(f"✅ 추천 결과 생성 완료 (페르소나: {persona})")
        return jsonify(final_response)
        
    except Exception as e:
        print(f"❌ 추천 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/static/processed_imgs/<path:filename>')
def serve_processed_image(filename):
    return send_from_directory(PROCESSED_DIR, filename)

if __name__ == '__main__':
    app.run(port=5000)