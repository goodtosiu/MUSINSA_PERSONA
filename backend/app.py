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
        path = 'master_data.npz'
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
            temp_data[key] = data[key]
        master_data = temp_data
        print(f"✅ 데이터 로드 완료! (총 {len(master_data['ids'])}개)")
    except Exception as e:
        print(f"❌ 데이터 로딩 에러: {e}")

init_data()

db_url = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)

# ---------------------------------------------------------
# [기능] 누끼 따기 함수
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
        return False
    except:
        return False

# ---------------------------------------------------------
# [API] 추천 상품 반환 (최적화 적용)
# ---------------------------------------------------------
@app.route('/api/products', methods=['GET'])
def get_recommendations():
    persona = request.args.get('persona', '아메카지')
    fixed_outfit_id = request.args.get('outfit_id')
    
    # [수정 1] 특정 카테고리만 요청했는지 확인
    target_category_filter = request.args.get('category') 
    
    if not master_data: return jsonify({"error": "Server data not loaded"}), 500

    try:
        # [STEP 1] Outfit ID 결정
        with engine.connect() as conn:
            if fixed_outfit_id:
                selected_outfit = int(fixed_outfit_id)
            else:
                outfit_query = "SELECT DISTINCT outfit FROM persona_item WHERE persona = %s"
                outfits_df = pd.read_sql(outfit_query, conn, params=(persona,))
                if outfits_df.empty: return jsonify({"error": "Persona not found"}), 404
                selected_outfit = int(np.random.choice(outfits_df['outfit'].tolist()))
                print(f"\n🆕 [신규 선택] Outfit ID: {selected_outfit}")

            # 타겟 상품 ID 추출
            item_query = "SELECT product_id FROM persona_item WHERE persona = %s AND outfit = %s"
            target_ids = pd.read_sql(item_query, conn, params=(persona, selected_outfit))['product_id'].tolist()
            
            if not target_ids: return jsonify({"error": "Invalid Outfit ID"}), 404

        # [STEP 2] 타겟 분석
        target_mask = np.isin(master_data['ids'], target_ids)
        target_categories = set(master_data['cats'][target_mask]) 

        t_vecs = {k: np.mean(master_data[f'{k}_vecs'][target_mask], axis=0) for k in ['name', 'brand', 'img', 'cat']}
        sims = {k: master_data[f'{k}_vecs'] @ v for k, v in t_vecs.items()}
        
        final_scores = (sims['name']*0.3) + (sims['brand']*0.3) + (sims['img']*0.3) + (sims['cat']*0.1)

        # [STEP 3] 결과 추출
        CATEGORY_MAP = {"outer": "아우터", "top": "상의", "bottom": "바지", "shoes": "신발", "acc": "액세서리"}
        final_response = { "current_outfit_id": selected_outfit, "items": {} }
        
        # 로그 헤더
        if not target_category_filter:
            print(f"\n📊 [점수 로그] 요청 페르소나: {persona} (Outfit {selected_outfit})")
        else:
            print(f"\n🔄 [부분 셔플] 카테고리: {target_category_filter} (Outfit {selected_outfit})")

        for eng_key, kor_val in CATEGORY_MAP.items():
            
            # [수정 2] 셔플 시: 요청된 카테고리가 아니면 건너뜀 (성능 최적화 핵심)
            if target_category_filter and target_category_filter != eng_key:
                continue

            # 1. 빈 카테고리 처리
            if kor_val not in target_categories:
                final_response["items"][eng_key] = [] 
                continue

            # 2. 필터링 및 상위 100개 추출
            cat_mask = (master_data['cats'] == kor_val)
            cat_scores = final_scores[cat_mask]
            
            if len(cat_scores) == 0:
                final_response["items"][eng_key] = []
                continue

            cat_real_indices = np.where(cat_mask)[0]
            sorted_indices = np.argsort(cat_scores)[::-1][:100]
            
            # 3. 셔플 (랜덤 5개)
            selected_local = np.random.choice(sorted_indices, min(5, len(sorted_indices)), replace=False)
            
            items_list = []
            
            print(f"   📂 [{kor_val}] 이미지 처리 및 점수:")
            
            for loc_idx in selected_local:
                original_idx = cat_real_indices[loc_idx]
                p_id = int(master_data['ids'][original_idx])
                p_name = str(master_data['names'][original_idx])
                p_img_origin = str(master_data['imgs'][original_idx])
                
                # 점수 로그
                s_total = final_scores[original_idx]
                s_n = sims['name'][original_idx]
                s_b = sims['brand'][original_idx]
                s_i = sims['img'][original_idx]
                print(f"      👉 [{p_name[:10]}..] 총점:{s_total:.3f} (N:{s_n:.2f} B:{s_b:.2f} I:{s_i:.2f})")

                # 누끼 처리 로직
                processed_filename = f"nobg_{p_id}.png"
                processed_file_path = os.path.join(PROCESSED_DIR, processed_filename)
                
                if os.path.exists(processed_file_path):
                    final_img_url = f"{request.host_url}static/processed_imgs/{processed_filename}"
                    is_processed = True
                else:
                    print(f"         ✂️ [누끼 생성] {p_id} 변환 중...", end="")
                    success = process_and_save_image(p_img_origin, processed_file_path)
                    
                    if success:
                        print(" 성공!")
                        final_img_url = f"{request.host_url}static/processed_imgs/{processed_filename}"
                        is_processed = True
                    else:
                        print(" 실패 (원본 사용)")
                        final_img_url = p_img_origin
                        is_processed = False

                items_list.append({
                    "product_id": p_id,
                    "product_name": p_name,
                    "price": int(master_data['prices'][original_idx]),
                    "img_url": final_img_url,
                    "category": kor_val,
                })
            
            final_response["items"][eng_key] = items_list

        response = jsonify(final_response)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    except Exception as e:
        print(f"❌ API 에러 발생: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/static/processed_imgs/<path:filename>')
def serve_processed_image(filename):
    return send_from_directory(PROCESSED_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)