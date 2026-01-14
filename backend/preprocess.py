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
    
    print("📥 DB에서 상품 정보 로딩 중...")
    # [수정 1] SQL 쿼리에 c.lower_category 추가
    df_base = pd.read_sql("""
        SELECT p.product_id, p.product_name, p.original_price, p.img_url, 
               c.upper_category, c.lower_category, p.category_id, p.brand_id 
        FROM product p 
        JOIN category c ON p.category_id = c.category_id
    """, engine)
    
    # 더 안전하고 진단 가능한 맵핑 함수
    def get_vec_map(path, name="Data"):
        if not os.path.exists(path):
            print(f"⚠️ [누락] {path} 파일이 없습니다. (모두 0으로 채워집니다)")
            return {}
            
        data = np.load(path, allow_pickle=True)
        files = data.files
        
        ids_arr = None
        vecs_arr = None
        
        for f in files:
            arr = data[f]
            if arr.ndim == 1: # 1차원이면 ID로 간주
                ids_arr = arr
            elif arr.ndim == 2: # 2차원이면 벡터로 간주
                vecs_arr = arr
        
        if ids_arr is None or vecs_arr is None:
            print(f"❌ [{name}] 파일 구조 인식 실패: keys={files}")
            return {}

        mapping = {k: v for k, v in zip(ids_arr, vecs_arr)}
        
        first_key = next(iter(mapping))
        print(f"✅ [{name}] 로드 완료 | 개수: {len(mapping)} | Key타입: {type(first_key)} | 예시키: {first_key}")
        return mapping

    print("\n📦 개별 벡터 파일 로딩 및 분석...")
    name_map = get_vec_map('name_emb.npz', "상품명")
    img_map = get_vec_map('image_embeddings.npz', "이미지")
    cat_map = get_vec_map('cat_emb.npz', "카테고리")
    brand_map = get_vec_map('brand_emb.npz', "브랜드")

    # 차원 설정
    def get_dim(v_map, default):
        if not v_map: return default
        return len(next(iter(v_map.values())))

    d_name = get_dim(name_map, 200)
    d_brand = get_dim(brand_map, 768)
    d_img = get_dim(img_map, 512)
    d_cat = get_dim(cat_map, 50)

    # [수정 2] lower_cats 리스트 초기화 추가
    ids, names, prices, imgs, cats, lower_cats = [], [], [], [], [], []
    name_matrix, brand_matrix, img_matrix, cat_matrix = [], [], [], []

    print(f"\n🏗️ 데이터 매칭 및 결합 시작... (Total: {len(df_base)} items)")
    print(f"   - Dimensions: Name({d_name}), Brand({d_brand}), Img({d_img}), Cat({d_cat})")
    
    stats = {"name_hit": 0, "brand_hit": 0, "img_hit": 0}
    
    total_count = len(df_base)
    for i, (_, row) in enumerate(df_base.iterrows()):
        if i % 2000 == 0:
            print(f"⏳ 진행 중... [{i}/{total_count}]", end='\r')

        pid = int(row['product_id'])
        bid = int(row['brand_id']) if row['brand_id'] is not None else -1
        cid = int(row['category_id'])

        def fetch_vec(v_map, key, dim, stat_key=None):
            val = v_map.get(key)
            if val is None:
                val = v_map.get(str(key))
            if val is None and isinstance(key, str) and key.isdigit():
                val = v_map.get(int(key))
            
            if val is not None:
                if stat_key: stats[stat_key] += 1
                if not hasattr(val, "__len__"): val = np.array([val])
                if len(val) != dim:
                    res = np.zeros(dim)
                    lim = min(len(val), dim)
                    res[:lim] = val[:lim]
                    return res
                return val
            return np.zeros(dim)

        nv = fetch_vec(name_map, pid, d_name, "name_hit")
        bv = fetch_vec(brand_map, bid, d_brand, "brand_hit")
        iv = fetch_vec(img_map, pid, d_img, "img_hit")
        cv = fetch_vec(cat_map, cid, d_cat)

        ids.append(pid)
        names.append(row['product_name'])
        prices.append(row['original_price'])
        imgs.append(row['img_url'])
        cats.append(row['upper_category']) # 기존 cats는 상위 카테고리 유지
        lower_cats.append(row['lower_category']) # [수정 3] 하위 카테고리 추가
        
        # 정규화
        norm_n = np.linalg.norm(nv)
        norm_b = np.linalg.norm(bv)
        norm_i = np.linalg.norm(iv)
        norm_c = np.linalg.norm(cv)

        name_matrix.append(nv / (norm_n + 1e-9) if norm_n > 0 else nv)
        brand_matrix.append(bv / (norm_b + 1e-9) if norm_b > 0 else bv)
        img_matrix.append(iv / (norm_i + 1e-9) if norm_i > 0 else iv)
        cat_matrix.append(cv / (norm_c + 1e-9) if norm_c > 0 else cv)

    print(f"\n\n📊 [매칭 결과 통계]")
    print(f"   👉 상품명 매칭 성공: {stats['name_hit']} / {total_count} ({(stats['name_hit']/total_count)*100:.1f}%)")
    print(f"   👉 브랜드 매칭 성공: {stats['brand_hit']} / {total_count} ({(stats['brand_hit']/total_count)*100:.1f}%)")
    print(f"   👉 이미지 매칭 성공: {stats['img_hit']} / {total_count} ({(stats['img_hit']/total_count)*100:.1f}%)")
    
    if stats['name_hit'] == 0:
        print("🚨 경고: 상품명 벡터 매칭 실패.")
    if stats['brand_hit'] == 0:
        print("🚨 경고: 브랜드 벡터 매칭 실패.")

    print(f"\n✅ 파일 저장 중...")
    
    # [수정 4] 저장 시 lower_cats 추가
    np.savez_compressed('master_data.npz', 
                        ids=np.array(ids), 
                        names=np.array(names), 
                        prices=np.array(prices), 
                        imgs=np.array(imgs), 
                        cats=np.array(cats),           # 상위 카테고리
                        lower_cats=np.array(lower_cats), # 하위 카테고리 (새로 추가됨)
                        name_vecs=np.vstack(name_matrix).astype(np.float32),
                        brand_vecs=np.vstack(brand_matrix).astype(np.float32),
                        img_vecs=np.vstack(img_matrix).astype(np.float32),
                        cat_vecs=np.vstack(cat_matrix).astype(np.float32))
    
    print("✅ preprocess 완료! 이제 app.py를 재실행하세요.")

if __name__ == "__main__":
    create_master_data()