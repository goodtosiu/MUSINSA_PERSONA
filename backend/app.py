import os
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import create_engine
import requests
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)
CORS(app)

# [설정] 전역 변수 및 경로 설정
master_data = {}
PROCESSED_DIR = os.path.join(os.getcwd(), "static", "processed_imgs")
os.makedirs(PROCESSED_DIR, exist_ok=True) # 폴더 없으면 생성

# ==========================================
# 1. 데이터 로드 (서버 시작 시 1회 실행)
# ==========================================
def init_data():
    global master_data
    try:
        path = 'master_data.npz'
        
        if not os.path.exists(path):
            print(f"🚨 [오류] {path} 파일을 찾을 수 없습니다. 경로를 확인하세요.")
            return

        data = np.load(path, allow_pickle=True)
        print(f"📂 NPZ 파일 로드 중... 키 목록: {list(data.files)}")
        
        # 필수 키 확인 및 데이터 할당
        required_keys = ['ids', 'names', 'prices', 'imgs', 'cats', 
                         'name_vecs', 'brand_vecs', 'img_vecs', 'cat_vecs']
        
        temp_data = {}
        for key in required_keys:
            if key not in data:
                print(f"❌ [키 누락] '{key}' 데이터가 없습니다.")
                return
            temp_data[key] = data[key]
            
        master_data = temp_data
        print(f"✅ 데이터 로드 완료! (총 {len(master_data['ids'])}개 상품)")

    except Exception as e:
        print(f"❌ 데이터 로딩 중 치명적 에러: {e}")

# 서버 시작 시 호출
init_data()

# DB 연결 설정
db_url = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)


# ==========================================
# 2. 추천 상품 API (셔플 로직 적용)
# ==========================================
@app.route('/api/products', methods=['GET'])
def get_recommendations():
    # 1. 파라미터 받기
    persona = request.args.get('persona', '아메카지')
    fixed_outfit_id = request.args.get('outfit_id') # 셔플 시 프론트엔드가 보내주는 ID
    
    # 예외처리: 마스터 데이터가 없을 경우
    if not master_data:
        return jsonify({"error": "Server data not loaded"}), 500

    try:
        # [STEP 1] 기준점(Target) 설정 - Outfit ID 결정
        with engine.connect() as conn:
            if fixed_outfit_id:
                # 셔플 버튼 클릭 시: 기존 Outfit ID 유지
                selected_outfit = int(fixed_outfit_id)
                print(f"\n🔄 [셔플 요청] 기존 Outfit ID 유지: {selected_outfit}")
            else:
                # 첫 접속 시: 새로운 Outfit ID 랜덤 선택
                outfit_query = "SELECT DISTINCT outfit FROM persona_item WHERE persona = %s"
                outfits_df = pd.read_sql(outfit_query, conn, params=(persona,))
                
                if outfits_df.empty:
                    return jsonify({"error": "Persona not found"}), 404
                
                selected_outfit = int(np.random.choice(outfits_df['outfit'].tolist()))
                print(f"\n🆕 [신규 요청] 새로운 Outfit ID 랜덤 선택: {selected_outfit}")

            # 선택된 Outfit에 포함된 상품 ID 가져오기 (Target Items)
            item_query = "SELECT product_id FROM persona_item WHERE persona = %s AND outfit = %s"
            target_ids = pd.read_sql(item_query, conn, params=(persona, selected_outfit))['product_id'].tolist()

            if not target_ids:
                return jsonify({"error": "Invalid Outfit ID (No items found)"}), 404

        # [STEP 2] 타겟 벡터 생성 (평균 벡터)
        mask = np.isin(master_data['ids'], target_ids)
        if not np.any(mask):
            return jsonify({"error": "Target items match fail in master_data"}), 404
            
        t_name = np.mean(master_data['name_vecs'][mask], axis=0)
        t_brand = np.mean(master_data['brand_vecs'][mask], axis=0)
        t_img = np.mean(master_data['img_vecs'][mask], axis=0)
        t_cat = np.mean(master_data['cat_vecs'][mask], axis=0)

        # [STEP 3] 전체 상품과의 유사도 계산 (벡터 내적)
        sim_name = master_data['name_vecs'] @ t_name
        sim_brand = master_data['brand_vecs'] @ t_brand
        sim_img = master_data['img_vecs'] @ t_img
        sim_cat = master_data['cat_vecs'] @ t_cat

        # [STEP 4] 가중치 적용 (이름 30%, 브랜드 30%, 이미지 30%, 카테고리 10%)
        final_scores = (sim_name * 0.3) + (sim_brand * 0.3) + (sim_img * 0.3) + (sim_cat * 0.1)

        # [STEP 5] 카테고리별 필터링, 상위 100개 추출 -> 랜덤 5개 선택
        CATEGORY_MAP = {"outer": "아우터", "top": "상의", "bottom": "바지", "shoes": "신발", "acc": "액세서리"}
        
        final_response = {
            "current_outfit_id": selected_outfit, # 프론트엔드가 다음 요청 때 쓸 ID
            "items": {}
        }

        for eng_key, kor_val in CATEGORY_MAP.items():
            # 1. 카테고리 필터링
            cat_mask = (master_data['cats'] == kor_val)
            cat_scores = final_scores[cat_mask]
            
            if len(cat_scores) == 0:
                final_response["items"][eng_key] = []
                continue

            # 2. 상위 100개 후보군 선정
            cat_real_indices = np.where(cat_mask)[0] # 실제 데이터 인덱스
            sorted_indices_local = np.argsort(cat_scores)[::-1] # 점수 높은 순 정렬
            top_100_local = sorted_indices_local[:100] # 상위 100개만 자름
            
            # 3. 셔플: 상위 100개 중에서 랜덤 5개 선택
            pick_count = min(5, len(top_100_local))
            selected_local = np.random.choice(top_100_local, pick_count, replace=False)
            
            items_list = []
            for loc_idx in selected_local:
                original_idx = cat_real_indices[loc_idx]
                
                p_id = int(master_data['ids'][original_idx])
                p_name = str(master_data['names'][original_idx])
                p_price = int(master_data['prices'][original_idx])
                p_img_origin = str(master_data['imgs'][original_idx])
                
                # --- [이미지 처리 로직] ---
                # 저장된 누끼 파일명 규칙: nobg_{product_id}.png
                processed_filename = f"nobg_{p_id}.png"
                processed_file_path = os.path.join(PROCESSED_DIR, processed_filename)
                
                # 파일이 실제로 존재하면 로컬 URL 반환, 없으면 원본 URL 반환
                if os.path.exists(processed_file_path):
                    final_img_url = f"{request.host_url}static/processed_imgs/{processed_filename}"
                    is_processed = True
                else:
                    final_img_url = p_img_origin
                    is_processed = False
                # -----------------------

                items_list.append({
                    "product_id": p_id,
                    "product_name": p_name,
                    "price": p_price,
                    "img_url": final_img_url,         # 프론트에서 보여줄 이미지
                    "original_img_url": p_img_origin, # 원본 필요시 사용
                    "is_processed": is_processed,     # 누끼 처리 여부
                    "category": kor_val,
                    "score": float(final_scores[original_idx])
                })
            
            final_response["items"][eng_key] = items_list

        # [STEP 6] 응답 반환 (캐시 방지 헤더 설정)
        response = jsonify(final_response)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response

    except Exception as e:
        print(f"❌ API 에러 발생: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================================
# 3. 정적 파일 서빙 (누끼 이미지)
# ==========================================
# Flask는 기본적으로 static 폴더를 서빙하지만, 명시적으로 경로를 잡아줍니다.
@app.route('/static/processed_imgs/<path:filename>')
def serve_processed_image(filename):
    return send_from_directory(PROCESSED_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)