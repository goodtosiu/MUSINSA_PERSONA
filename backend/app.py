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
# [API] 추천 상품 반환
# ---------------------------------------------------------
@app.route('/api/products', methods=['GET'])
def get_recommendations():
    persona = request.args.get('persona', '아메카지')
    fixed_outfit_id = request.args.get('outfit_id')
    target_category_filter = request.args.get('category')
    
    # [가격 필터 파라미터 수신]
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)

    if not master_data: return jsonify({"error": "Server data not loaded"}), 500

    try:
        # [STEP 1] Outfit ID 결정 및 타겟 아이템 확보
        with engine.connect() as conn:
            if fixed_outfit_id:
                selected_outfit = int(fixed_outfit_id)
            else:
                outfit_query = "SELECT DISTINCT outfit FROM persona_item WHERE persona = %s"
                outfits_df = pd.read_sql(outfit_query, conn, params=(persona,))
                if outfits_df.empty: return jsonify({"error": "Persona not found"}), 404
                selected_outfit = int(np.random.choice(outfits_df['outfit'].tolist()))

            item_query = "SELECT product_id FROM persona_item WHERE persona = %s AND outfit = %s"
            target_ids = pd.read_sql(item_query, conn, params=(persona, selected_outfit))['product_id'].tolist()
            
            if not target_ids: return jsonify({"error": "Invalid Outfit ID"}), 404

        # [STEP 2] 타겟 아이템 매핑
        target_indices = np.where(np.isin(master_data['ids'], target_ids))[0]
        target_item_map = {master_data['cats'][idx]: idx for idx in target_indices}

        # [가격 필터 마스크 생성]
        price_mask = np.ones(len(master_data['price']), dtype=bool)
        if min_price is not None:
            price_mask &= (master_data['price'] >= min_price)
        if max_price is not None:
            price_mask &= (master_data['price'] <= max_price)

        CATEGORY_MAP = {"outer": "아우터", "top": "상의", "bottom": "바지", "shoes": "신발", "acc": "액세서리"}
        final_response = { "current_outfit_id": selected_outfit, "items": {} }

        # 각 카테고리별로 루프를 돌며 5개씩 추출
        for eng_key, kor_val in CATEGORY_MAP.items():
            # 특정 카테고리만 요청받은 경우 해당 카테고리가 아니면 스킵
            if target_category_filter and target_category_filter != eng_key: continue

            # 해당 코디 구성에 이 카테고리가 없으면 빈 리스트 반환
            if kor_val not in target_item_map:
                final_response["items"][eng_key] = [] 
                continue

            target_idx = target_item_map[kor_val]

            # 유사도 계산 (벡터 내적)
            sim_name = master_data['name_vecs'] @ master_data['name_vecs'][target_idx]
            sim_brand = master_data['brand_vecs'] @ master_data['brand_vecs'][target_idx]
            sim_img = master_data['img_vecs'] @ master_data['img_vecs'][target_idx]
            sim_cat = master_data['cat_vecs'] @ master_data['cat_vecs'][target_idx]

            # 가중치 적용
            final_scores = (sim_name * 0.1) + (sim_brand * 0.1) + (sim_img * 0.6) + (sim_cat * 0.1)

            # [핵심] 해당 카테고리이면서 가격 필터를 통과한 상품만 필터링
            combined_mask = (master_data['cats'] == kor_val) & price_mask
            cat_scores = final_scores[combined_mask]
            cat_real_indices = np.where(combined_mask)[0]
            
            if len(cat_scores) == 0:
                final_response["items"][eng_key] = []
                continue

            # 가격 필터링된 상품 중 유사도 상위 100개 추출 후 랜덤 5개 선택
            sorted_indices = np.argsort(cat_scores)[::-1][:100]
            selected_local = np.random.choice(sorted_indices, min(5, len(sorted_indices)), replace=False)
            
            items_list = []
            for loc_idx in selected_local:
                original_idx = cat_real_indices[loc_idx]
                p_id = int(master_data['ids'][original_idx])
                
                # 누끼 이미지 경로 확인 및 처리
                processed_filename = f"nobg_{p_id}.png"
                processed_file_path = os.path.join(PROCESSED_DIR, processed_filename)
                
                if os.path.exists(processed_file_path):
                    final_img_url = f"{request.host_url}static/processed_imgs/{processed_filename}"
                else:
                    success = process_and_save_image(master_data['imgs'][original_idx], processed_file_path)
                    final_img_url = f"{request.host_url}static/processed_imgs/{processed_filename}" if success else master_data['imgs'][original_idx]

                items_list.append({
                    "product_id": p_id,
                    "product_name": str(master_data['names'][original_idx]),
                    "price": int(master_data['price'][original_idx]),
                    "img_url": final_img_url,
                    "category": kor_val,
                })
            
            # 최종 응답 객체에 카테고리별로 5개씩 담김
            final_response["items"][eng_key] = items_list

        return jsonify(final_response)

    except Exception as e:
        print(f"❌ API 에러 발생: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/static/processed_imgs/<path:filename>')
def serve_processed_image(filename):
    return send_from_directory(PROCESSED_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)