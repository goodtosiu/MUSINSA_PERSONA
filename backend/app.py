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
    
    # --- [추가] 가격 필터 파라미터 ---
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)
    # ------------------------------

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
                print(f"\n🆕 [신규 선택] Outfit ID: {selected_outfit}")

            item_query = "SELECT product_id FROM persona_item WHERE persona = %s AND outfit = %s"
            target_ids = pd.read_sql(item_query, conn, params=(persona, selected_outfit))['product_id'].tolist()
            
            if not target_ids: return jsonify({"error": "Invalid Outfit ID"}), 404

        # [확인용 로그]
        print(f"   🎯 [기준(Target) 상품 목록] Outfit {selected_outfit}번 구성:")
        target_indices_check = np.where(np.isin(master_data['ids'], target_ids))[0]
        for t_idx in target_indices_check:
            t_name = master_data['names'][t_idx]
            t_cat = master_data['cats'][t_idx]
            print(f"      - [{t_cat}] {t_name}")
        print("   --------------------------------------------------")

        # [STEP 2] 타겟 아이템 매핑
        target_indices = np.where(np.isin(master_data['ids'], target_ids))[0]
        target_item_map = {}
        for idx in target_indices:
            cat_name = master_data['cats'][idx]
            target_item_map[cat_name] = idx

        # --- [추가] 가격 필터 마스크 생성 ---
        price_mask = np.ones(len(master_data['prices']), dtype=bool)
        if min_price is not None:
            price_mask &= (master_data['prices'] >= min_price)
        if max_price is not None:
            price_mask &= (master_data['prices'] <= max_price)
        # ---------------------------------

        CATEGORY_MAP = {"outer": "아우터", "top": "상의", "bottom": "바지", "shoes": "신발", "acc": "액세서리"}
        final_response = { "current_outfit_id": selected_outfit, "items": {} }
        
        if not target_category_filter:
            print(f"\n📊 [점수 로그] 요청 페르소나: {persona} (Outfit {selected_outfit})")

        for eng_key, kor_val in CATEGORY_MAP.items():
            if target_category_filter and target_category_filter != eng_key: continue
            if kor_val not in target_item_map:
                final_response["items"][eng_key] = [] 
                continue

            target_idx = target_item_map[kor_val]

            t_name = master_data['name_vecs'][target_idx]
            t_brand = master_data['brand_vecs'][target_idx]
            t_img = master_data['img_vecs'][target_idx]
            t_cat = master_data['cat_vecs'][target_idx]

            sim_name = master_data['name_vecs'] @ t_name
            sim_brand = master_data['brand_vecs'] @ t_brand
            sim_img = master_data['img_vecs'] @ t_img
            sim_cat = master_data['cat_vecs'] @ t_cat

            final_scores = (sim_name * 0.1) + (sim_brand * 0.1) + (sim_img * 0.6) + (sim_cat * 0.1)

            # --- [수정] 카테고리 필터 + 가격 필터 동시 적용 ---
            combined_mask = (master_data['cats'] == kor_val) & price_mask
            cat_scores = final_scores[combined_mask]
            
            if len(cat_scores) == 0:
                final_response["items"][eng_key] = []
                continue

            cat_real_indices = np.where(combined_mask)[0]
            # 이미 가격으로 필터링된 상품들 중 상위 100개 추출
            sorted_indices = np.argsort(cat_scores)[::-1][:100]
            selected_local = np.random.choice(sorted_indices, min(5, len(sorted_indices)), replace=False)
            
            items_list = []
            print(f"   📂 [{kor_val}] 추천 점수 (가중치: Img 0.6 / 나머지 0.1)")
            
            for loc_idx in selected_local:
                original_idx = cat_real_indices[loc_idx]
                p_id = int(master_data['ids'][original_idx])
                p_name = str(master_data['names'][original_idx])
                p_img_origin = str(master_data['imgs'][original_idx])
                
                # 로그 출력
                s_total = final_scores[original_idx]
                print(f"      👉 [{p_name[:10]}..] 총점:{s_total:.3f} (가격: {master_data['prices'][original_idx]})")

                processed_filename = f"nobg_{p_id}.png"
                processed_file_path = os.path.join(PROCESSED_DIR, processed_filename)
                
                if os.path.exists(processed_file_path):
                    final_img_url = f"{request.host_url}static/processed_imgs/{processed_filename}"
                else:
                    print(f"         ✂️ [누끼] {p_id}...", end="")
                    success = process_and_save_image(p_img_origin, processed_file_path)
                    if success:
                        print(" 완료")
                        final_img_url = f"{request.host_url}static/processed_imgs/{processed_filename}"
                    else:
                        print(" 실패")
                        final_img_url = p_img_origin

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