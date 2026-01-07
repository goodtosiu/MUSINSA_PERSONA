import streamlit as st
import numpy as np
import pandas as pd
import os
import json
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import datetime

# 환경 변수 및 데이터 로드 설정
load_dotenv()

# [설정]
DATA_PATH = 'master_data.npz'
OUTPUT_FILE = f"labeled_data_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

# ---------------------------------------------------------
# [1] 데이터 로딩 (캐싱하여 속도 향상)
# ---------------------------------------------------------
@st.cache_resource
def load_resources():
    # 1. Master Data 로드
    if not os.path.exists(DATA_PATH):
        st.error(f"🚨 {DATA_PATH} 파일이 없습니다.")
        return None, None
    
    data = np.load(DATA_PATH, allow_pickle=True)
    master_data = {k: data[k] for k in ['ids', 'names', 'prices', 'imgs', 'cats', 
                                        'name_vecs', 'brand_vecs', 'img_vecs', 'cat_vecs']}
    
    # 2. DB 연결
    try:
        db_url = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
        engine = create_engine(db_url)
    except Exception as e:
        st.error(f"DB 연결 실패: {e}")
        return master_data, None

    return master_data, engine

master_data, engine = load_resources()

# ---------------------------------------------------------
# [2] 추천 조합 생성 로직 (배치 생성)
# ---------------------------------------------------------
def generate_batch_outfits(persona, count=100):
    """
    지정된 페르소나에 대해 랜덤하게 대표 코디를 선정하고,
    대표 코디의 카테고리 구성을 100% 유지하는 유사 상품 조합을 생성함.
    구성 요소가 누락되면 해당 조합을 버리고 재시도함.
    """
    generated_batch = []
    
    if engine is None:
        return []

    with engine.connect() as conn:
        # 1. 해당 페르소나의 모든 Outfit ID 가져오기
        outfit_query = "SELECT DISTINCT outfit FROM persona_item WHERE persona = %s"
        outfits_df = pd.read_sql(outfit_query, conn, params=(persona,))
        
        if outfits_df.empty:
            st.error("해당 페르소나의 코디 데이터가 없습니다.")
            return []
        
        all_outfits = outfits_df['outfit'].tolist()

    # 진행률 표시 바
    progress_bar = st.progress(0)
    
    # [수정] while 루프로 변경하여 목표 개수(count)를 채울 때까지 반복 (재시도 로직)
    while len(generated_batch) < count:
        # 랜덤으로 대표 Outfit 하나 선정
        selected_outfit = int(np.random.choice(all_outfits))
        
        # 타겟 아이템 가져오기
        with engine.connect() as conn:
            item_query = "SELECT product_id FROM persona_item WHERE persona = %s AND outfit = %s"
            target_ids = pd.read_sql(item_query, conn, params=(persona, selected_outfit))['product_id'].tolist()

        # [검증 1] DB에 있는 상품 ID가 master_data에 실제로 모두 존재하는지 체크
        # 존재하지 않는 ID가 하나라도 있다면 이 대표 코디는 데이터 불량이므로 스킵하고 다시 뽑음
        valid_mask = np.isin(target_ids, master_data['ids'])
        if not np.all(valid_mask):
            # print(f"Skipping outfit {selected_outfit}: Missing items in master_data")
            continue 

        target_indices = np.where(np.isin(master_data['ids'], target_ids))[0]
        target_item_map = {master_data['cats'][idx]: idx for idx in target_indices}
        
        CATEGORY_MAP = {"outer": "아우터", "top": "상의", "bottom": "바지", "shoes": "신발", "acc": "액세서리"}
        
        current_set = {
            "persona": persona,
            "target_outfit_id": selected_outfit,
            "items": {},  # {category: {id, name, img_url}}
            "simple_items": {} # {category: id} -> 저장용
        }

        # 카테고리별 상품 선정
        target_categories_found = 0
        expected_categories_count = 0

        for eng_key, kor_val in CATEGORY_MAP.items():
            # 대표 코디에 해당 카테고리가 있는지 확인
            if kor_val not in target_item_map:
                continue
            
            expected_categories_count += 1
            target_idx = target_item_map[kor_val]
            
            # 유사도 계산
            sim_score = (
                (master_data['name_vecs'] @ master_data['name_vecs'][target_idx]) * 0.1 +
                (master_data['brand_vecs'] @ master_data['brand_vecs'][target_idx]) * 0.1 +
                (master_data['img_vecs'] @ master_data['img_vecs'][target_idx]) * 0.6 +
                (master_data['cat_vecs'] @ master_data['cat_vecs'][target_idx]) * 0.1
            )
            
            # 카테고리 일치 필터
            cat_mask = (master_data['cats'] == kor_val)
            cat_scores = sim_score[cat_mask]
            cat_real_indices = np.where(cat_mask)[0]
            
            # 상위 100개 중 1개 랜덤 선택
            if len(cat_scores) > 0:
                top_100_indices = np.argsort(cat_scores)[::-1][:100]
                picked_local_idx = np.random.choice(top_100_indices)
                original_idx = cat_real_indices[picked_local_idx]
                
                current_set["items"][eng_key] = {
                    "id": int(master_data['ids'][original_idx]),
                    "name": str(master_data['names'][original_idx]),
                    "img_url": str(master_data['imgs'][original_idx])
                }
                current_set["simple_items"][eng_key] = int(master_data['ids'][original_idx])
                target_categories_found += 1
            else:
                # 후보 상품이 아예 없는 경우 (매우 드뭄)
                pass

        # [검증 2] 대표 코디가 가진 카테고리 수와 생성된 코디의 카테고리 수가 같은지 확인
        # 하나라도 생성 실패했다면(후보 부족 등) 이 조합은 버리고 다시 시도
        if target_categories_found == expected_categories_count and expected_categories_count > 0:
            generated_batch.append(current_set)
            # 진행률 업데이트
            progress_bar.progress(len(generated_batch) / count)
        
    return generated_batch
# ---------------------------------------------------------
# [3] UI 및 인터랙션 로직
# ---------------------------------------------------------
st.title("🧥 아웃핏 평가 데이터 생성기")
st.markdown("생성된 조합을 보고 **페르소나에 어울리면 O, 아니면 X**를 눌러주세요.")

# 세션 상태 초기화
if 'batch_data' not in st.session_state:
    st.session_state.batch_data = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'labeled_results' not in st.session_state:
    st.session_state.labeled_results = []

# 사이드바: 설정 및 생성
with st.sidebar:
    st.header("설정")
    persona_input = st.text_input("페르소나 입력", value="아메카지")
    
    if st.button("🚀 배치 데이터 생성 (100개)"):
        with st.spinner('조합 생성 중...'):
            st.session_state.batch_data = generate_batch_outfits(persona_input, 100)
            st.session_state.current_index = 0
            st.session_state.labeled_results = [] # 새로 생성하면 결과 초기화
        st.success(f"100개 조합 생성 완료!")

    st.markdown("---")
    st.write(f"현재 진행: {st.session_state.current_index} / {len(st.session_state.batch_data)}")
    
    # 중간 저장 기능
    if st.button("💾 현재까지 결과 파일 저장"):
        if st.session_state.labeled_results:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(st.session_state.labeled_results, f, ensure_ascii=False, indent=4)
            st.success(f"저장 완료: {OUTPUT_FILE}")
        else:
            st.warning("저장할 데이터가 없습니다.")

# 메인 화면: 이미지 표시 및 버튼
if st.session_state.batch_data:
    if st.session_state.current_index < len(st.session_state.batch_data):
        current_data = st.session_state.batch_data[st.session_state.current_index]
        items = current_data['items']
        
        st.subheader(f"조합 #{st.session_state.current_index + 1} (페르소나: {current_data['persona']})")
        
        # 이미지 갤러리 (누끼 없이 원본 URL 사용 - 2-4 요구사항)
        cols = st.columns(len(items))
        for idx, (cat, info) in enumerate(items.items()):
            with cols[idx]:
                st.image(info['img_url'], use_container_width=True)
                st.caption(f"[{cat}] {info['name']}")

        # 평가 버튼 영역
        col1, col2 = st.columns([1, 1])
        
        def save_decision(label):
            # 1. 결과 저장 (2-3 요구사항)
            result_entry = {
                "persona": current_data['persona'],
                "category_items": current_data['simple_items'], # 카테고리: ID 구조
                "label": label, # "good" or "bad"
                "timestamp": datetime.now().isoformat()
            }
            st.session_state.labeled_results.append(result_entry)
            
            # 2. 다음 인덱스로 이동
            st.session_state.current_index += 1
            
            # 3. 100개 완료 시 자동 저장
            if st.session_state.current_index >= len(st.session_state.batch_data):
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(st.session_state.labeled_results, f, ensure_ascii=False, indent=4)
                st.balloons()
                st.success(f"모든 평가 완료! 파일이 저장되었습니다: {OUTPUT_FILE}")

        with col1:
            if st.button("⭕ 어울림 (Good)", type="primary", use_container_width=True):
                save_decision("good")
        
        with col2:
            if st.button("❌ 안 어울림 (Bad)", type="secondary", use_container_width=True):
                save_decision("bad")
                
    else:
        st.info("모든 데이터 평가가 완료되었습니다. 사이드바에서 다시 생성할 수 있습니다.")

else:
    st.info("👈 왼쪽 사이드바에서 페르소나를 입력하고 '배치 데이터 생성'을 눌러주세요.")