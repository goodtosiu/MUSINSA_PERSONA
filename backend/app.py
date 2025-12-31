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
        path = 'master_data.npz'
        data = np.load(path, allow_pickle=True)
        
        # [중요] 모든 키가 존재하는지 확인하고 master_data에 담기
        master_data = {
            'ids': data['ids'],
            'names': data['names'],
            'prices': data['prices'],
            'imgs': data['imgs'],
            'cats': data['cats'],
            'name_vecs': data['name_vecs'],
            'brand_vecs': data['brand_vecs'], # 여기서 에러나면 파일이 잘못된 것
            'img_vecs': data['img_vecs'],
            'cat_vecs': data['cat_vecs']
        }
        print(f"✅ {len(master_data['ids'])}개 상품 및 4종 벡터 로드 완료")
        print(f"📦 포함된 키: {list(master_data.keys())}")
        
    except KeyError as e:
        print(f"❌ NPZ 파일 내 키 누락 에러: {e}")
        print("💡 preprocess.py를 다시 실행하여 파일을 갱신해야 합니다.")
    except Exception as e:
        print(f"❌ 데이터 로딩 중 에러 발생: {e}")


# 서버 시작 시 데이터 로드 호출
init_data()

# DB 연결 설정 (Outfit 정보를 가져오기 위해 필요)
db_url = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)

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

        # [STEP 2] 다차원 기준 벡터(Target Vector) 생성
        mask = np.isin(master_data['ids'], target_ids)
        if not np.any(mask):
            return jsonify({"error": "Target items match fail"}), 404
            
        # 각 요소별 평균 벡터 추출
        t_name = np.mean(master_data['name_vecs'][mask], axis=0)
        t_brand = np.mean(master_data['brand_vecs'][mask], axis=0) # 브랜드 벡터 추가
        t_img = np.mean(master_data['img_vecs'][mask], axis=0)     # 이미지 벡터 추가
        t_cat = np.mean(master_data['cat_vecs'][mask], axis=0)

        # [STEP 3] 4개 차원 유사도 연산 (행렬 곱)
        sim_name = master_data['name_vecs'] @ t_name
        sim_brand = master_data['brand_vecs'] @ t_brand
        sim_img = master_data['img_vecs'] @ t_img
        sim_cat = master_data['cat_vecs'] @ t_cat

        # [STEP 4] 가중치 결합 (실제 스타일 체감에 중요한 요소에 높은 비중)
        # 이름(텍스트) 30% + 브랜드 정체성 30% + 시각적 유사도 30% + 카테고리 일치 10%
        final_scores = (sim_name * 0.3) + (sim_brand * 0.3) + (sim_img * 0.3) + (sim_cat * 0.1)

        # [STEP 5] 카테고리별 결과 분류 및 셔플 (상위 100개 중 5개)
        CATEGORY_MAP = {"outer": "아우터", "top": "상의", "bottom": "바지", "shoes": "신발", "acc": "액세서리"}
        final_data = {key: [] for key in CATEGORY_MAP.keys()}

        for eng_key, kor_val in CATEGORY_MAP.items():
            cat_mask = (master_data['cats'] == kor_val)
            cat_scores = final_scores[cat_mask]
            
            if len(cat_scores) == 0: continue

            # 유사도 높은 순으로 인덱스 정렬
            top_indices = np.argsort(cat_scores)[-100:][::-1]
            selected_indices = np.random.choice(top_indices, min(5, len(top_indices)), replace=False)
            
            # 실제 데이터 인덱스 매핑
            cat_real_indices = np.where(cat_mask)[0]
            
            for idx in selected_indices:
                original_idx = cat_real_indices[idx]
                final_data[eng_key].append({
                    "product_id": int(master_data['ids'][original_idx]),
                    "product_name": str(master_data['names'][original_idx]),
                    "price": int(master_data['prices'][original_idx]),
                    "img_url": str(master_data['imgs'][original_idx]),
                    "category": kor_val,
                    "score": float(final_scores[original_idx]) # 디버깅용 점수
                })

        return jsonify(final_data)

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