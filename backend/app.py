import os
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from sqlalchemy import create_engine
import requests
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

master_data = {} # 전역 변수 초기화

def init_data():
    global master_data
    try:
        data = np.load(r"master_data.npz",allow_pickle=True)
        master_data = {
            'ids': data['ids'],
            'names': data['names'],
            'prices': data['prices'],
            'imgs': data['imgs'],
            'cats': data['cats'],
            'name_vecs': data['name_vecs'],
            'brand_vecs': data['brand_vecs'],
            'img_vecs': data['img_vecs'],
            'cat_vecs': data['cat_vecs']
        }
        
        print(f"✅ {len(master_data['ids'])}개 상품 데이터 로드 완료")

        # [진단 코드] 벡터가 0인지 확인
        print("-" * 40)
        print("🕵️‍♀️ 벡터 데이터 무결성 검사")
        
        # 이름 벡터 검사
        name_sum = np.sum(np.abs(master_data['name_vecs']))
        print(f"   👉 이름 벡터 절대값 합계: {name_sum:.4f} (0이면 데이터 비어있음)")
        
        # 브랜드 벡터 검사
        brand_sum = np.sum(np.abs(master_data['brand_vecs']))
        print(f"   👉 브랜드 벡터 절대값 합계: {brand_sum:.4f} (0이면 데이터 비어있음)")
        
        # 이미지 벡터 검사 (이건 정상일 것임)
        img_sum = np.sum(np.abs(master_data['img_vecs']))
        print(f"   👉 이미지 벡터 절대값 합계: {img_sum:.4f}")
        print("-" * 40)

        # 만약 합계가 0이라면 경고 메시지 출력
        if name_sum == 0 or brand_sum == 0:
            print("⚠️ 경고: 텍스트 벡터(이름/브랜드)가 0으로 채워져 있습니다!")
            print("   preprocess.py 에서 임베딩이 제대로 수행되지 않았을 가능성이 큽니다.")

    except KeyError as e:
        print(f"❌ NPZ 파일 내 키 누락 에러: {e}")
    except Exception as e:
        print(f"❌ 데이터 로딩 중 에러 발생: {e}")

# 서버 시작 시 데이터 로드 호출
init_data()

# DB 연결 설정 (Outfit 정보를 가져오기 위해 필요)
db_url = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)

# 2. 추천 상품 API
# 2. 추천 상품 API
# 2. 추천 상품 API
@app.route('/api/products', methods=['GET'])
def get_recommendations():
    persona = request.args.get('persona', '아메카지')
    
    try:
        # [STEP 1] 특정 Outfit(조합) 하나를 랜덤 선택
        with engine.connect() as conn:
            outfit_query = "SELECT DISTINCT outfit FROM persona_item WHERE persona = %s"
            outfits_df = pd.read_sql(outfit_query, conn, params=(persona,))
            
            if outfits_df.empty:
                return jsonify({"error": "Persona not found"}), 404
            
            selected_outfit = np.random.choice(outfits_df['outfit'].tolist())
            item_query = "SELECT product_id FROM persona_item WHERE persona = %s AND outfit = %s"
            target_ids = pd.read_sql(item_query, conn, params=(persona, int(selected_outfit)))['product_id'].tolist()
            
            print(f"\n🔍 [요청 페르소나] {persona} (Outfit ID: {selected_outfit})")
            print(f"🎯 [타겟 상품 ID] {target_ids}")

        # [STEP 2] 다차원 기준 벡터(Target Vector) 생성
        mask = np.isin(master_data['ids'], target_ids)
        if not np.any(mask):
            return jsonify({"error": "Target items match fail"}), 404
            
        # 각 요소별 평균 벡터 추출
        t_name = np.mean(master_data['name_vecs'][mask], axis=0)
        t_brand = np.mean(master_data['brand_vecs'][mask], axis=0) 
        t_img = np.mean(master_data['img_vecs'][mask], axis=0)     
        t_cat = np.mean(master_data['cat_vecs'][mask], axis=0)

        # [STEP 3] 4개 차원 유사도 연산 (행렬 곱)
        sim_name = master_data['name_vecs'] @ t_name
        sim_brand = master_data['brand_vecs'] @ t_brand
        sim_img = master_data['img_vecs'] @ t_img
        sim_cat = master_data['cat_vecs'] @ t_cat

        # [STEP 4] 가중치 결합 (이름 30%, 브랜드 30%, 이미지 30%, 카테고리 10%)
        final_scores = (sim_name * 0.3) + (sim_brand * 0.3) + (sim_img * 0.3) + (sim_cat * 0.1)

        # [STEP 5] 카테고리별 결과 분류 및 셔플 (상위 100개 중 5개)
        CATEGORY_MAP = {"outer": "아우터", "top": "상의", "bottom": "바지", "shoes": "신발", "acc": "액세서리"}
        final_data = {key: [] for key in CATEGORY_MAP.keys()}

        print("-" * 50)
        for eng_key, kor_val in CATEGORY_MAP.items():
            cat_mask = (master_data['cats'] == kor_val)
            cat_scores = final_scores[cat_mask]
            
            if len(cat_scores) == 0: continue

            # 해당 카테고리에 속하는 전체 데이터 내 인덱스
            cat_real_indices = np.where(cat_mask)[0]
            
            # 1. 점수 내림차순 정렬 후 상위 100개 인덱스(로컬) 추출
            sorted_indices_local = np.argsort(cat_scores)[::-1]
            top_100_local = sorted_indices_local[:100]
            
            # 2. 상위 100개 중에서 랜덤으로 5개 선택 (여기서 셔플 효과 발생)
            selected_local = np.random.choice(top_100_local, min(5, len(top_100_local)), replace=False)
            
            print(f"📂 [{kor_val}] 추천 생성 중...")

            for loc_idx in selected_local:
                original_idx = cat_real_indices[loc_idx] # 원본 인덱스 복원
                
                final_data[eng_key].append({
                    "product_id": int(master_data['ids'][original_idx]),
                    "product_name": str(master_data['names'][original_idx]),
                    "price": int(master_data['prices'][original_idx]),
                    "img_url": str(master_data['imgs'][original_idx]),
                    "category": kor_val,
                    "score": float(final_scores[original_idx])
                })

        # [STEP 6] 응답 생성 및 캐시 방지 헤더 추가 (★중요)
        response = jsonify(final_data)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response

    except Exception as e:
        print(f"❌ 다차원 추천 로직 에러: {e}")
        return jsonify({"error": str(e)}), 500


# 3. 누끼 이미지 반환 API
@app.route('/api/remove-bg')
def remove_bg():
    img_url = request.args.get('url')
    if not img_url or img_url == 'undefined':
        return "Invalid URL", 400
    try:
        # 실제로는 여기서 AI 모델을 돌리거나 외부 API를 호출하겠지만, 
        # 지금은 원본 이미지를 그대로 반환하거나 캐시된 결과를 보낸다고 가정
        response = requests.get(img_url)
        return response.content, 200, {'Content-Type': 'image/jpeg'}
    except:
        return "Error", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)