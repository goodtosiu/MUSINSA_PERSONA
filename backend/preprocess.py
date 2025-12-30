import numpy as np
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

def create_master_data():
    print("🔄 완전체 마스터 데이터 결합 시작...")
    
    db_url = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    engine = create_engine(db_url)
    
    df_base = pd.read_sql("""
        SELECT p.product_id, p.product_name, p.original_price, p.img_url, 
               c.upper_category, p.category_id, p.brand_id 
        FROM product p 
        JOIN category c ON p.category_id = c.category_id
    """, engine)

    def get_vec_map(path):
        if not os.path.exists(path):
            print(f"⚠️ 경고: {path} 파일 없음")
            return {}
        data = np.load(path, allow_pickle=True)
        keys = list(data.files)
        # ID를 int 키로, 벡터를 value로 매핑
        return {int(k): v for k, v in zip(data[keys[0]].ravel(), data[keys[1]])}

    print("📦 개별 벡터 파일 로딩 중...")
    name_map = get_vec_map('embedding_name.npz')
    img_map = get_vec_map('image_embeddings.npz')
    cat_map = get_vec_map('cat_emb.npz')
    brand_map = get_vec_map('brand_emb.npz')

    # 차원을 안전하게 가져오는 함수 수정
    def get_dim(v_map, default):
        if not v_map: return default
        first_val = next(iter(v_map.values()))
        # 만약 값이 배열이면 길이를 반환, 단일 숫자면 1을 반환
        if hasattr(first_val, "__len__"):
            return len(first_val)
        return 1 if isinstance(first_val, (int, float, np.number)) else default

    d_name = get_dim(name_map, 200)
    d_brand = get_dim(brand_map, 768)
    d_img = get_dim(img_map, 512)
    d_cat = get_dim(cat_map, 50)

    ids, names, prices, imgs, cats = [], [], [], [], []
    name_matrix, brand_matrix, img_matrix, cat_matrix = [], [], [], []

    print(f"🏗️ 데이터 결합 중... (Name:{d_name}, Brand:{d_brand}, Img:{d_img}, Cat:{d_cat})")
    
    total_count = len(df_base)
    for i, (_, row) in enumerate(df_base.iterrows()):
        # 진행 상황 표시
        if i % 2000 == 0:
            print(f"⏳ 진행 중... [{i}/{total_count}] ({(i/total_count)*100:.1f}%)", end='\r')

        pid = int(row['product_id'])
        bid = int(row['brand_id']) if row['brand_id'] is not None else -1
        cid = int(row['category_id'])

        def get_valid_vec(v_map, key, dim):
            v = v_map.get(key)
            if v is None:
                return np.zeros(dim)
            # v가 단일 숫자일 경우 배열로 변환
            if not hasattr(v, "__len__"):
                v = np.array([v])
            # 차원이 안 맞으면 0으로 채우거나 자름
            if len(v) != dim:
                res = np.zeros(dim)
                limit = min(len(v), dim)
                res[:limit] = v[:limit]
                return res
            return v

        nv = get_valid_vec(name_map, pid, d_name)
        bv = get_valid_vec(brand_map, bid, d_brand)
        iv = get_valid_vec(img_map, pid, d_img)
        cv = get_valid_vec(cat_map, cid, d_cat)

        ids.append(pid)
        names.append(row['product_name'])
        prices.append(row['original_price'])
        imgs.append(row['img_url'])
        cats.append(row['upper_category'])
        
        # 정규화
        name_matrix.append(nv / (np.linalg.norm(nv) + 1e-9))
        brand_matrix.append(bv / (np.linalg.norm(bv) + 1e-9))
        img_matrix.append(iv / (np.linalg.norm(iv) + 1e-9))
        cat_matrix.append(cv / (np.linalg.norm(cv) + 1e-9))

    print(f"\n✅ 결합 완료! 파일 압축 및 저장 중...")
    
    np.savez_compressed('master_data.npz', 
                        ids=np.array(ids), 
                        names=np.array(names), 
                        prices=np.array(prices), 
                        imgs=np.array(imgs), 
                        cats=np.array(cats),
                        name_vecs=np.vstack(name_matrix).astype(np.float32),
                        brand_vecs=np.vstack(brand_matrix).astype(np.float32),
                        img_vecs=np.vstack(img_matrix).astype(np.float32),
                        cat_vecs=np.vstack(cat_matrix).astype(np.float32))
    
    print("✅ 모든 작업이 끝났습니다. 이제 서버를 켜세요!")

if __name__ == "__main__":
    create_master_data()