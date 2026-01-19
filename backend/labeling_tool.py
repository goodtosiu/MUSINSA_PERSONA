import streamlit as st
import numpy as np
import pandas as pd
import os
import json
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import datetime

# 환경 변수 및 데이터 로드 설정
# backend 디렉토리의 .env 파일 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

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
    # [수정] 'lower_cats' 키 추가 로드
    master_data = {k: data[k] for k in ['ids', 'names', 'prices', 'imgs', 'cats', 'lower_cats']}
    
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
# [2] 추천 조합 생성 로직
# ---------------------------------------------------------
def generate_batch_outfits(persona, count=100):
    """
    representative_item 테이블에서 해당 페르소나의 아이템을 모두 가져온 뒤,
    카테고리별로 그룹핑하고 랜덤하게 하나씩 뽑아 조합(Outfit)을 생성함.
    [룰]
    1. 액세서리는 30% 확률로만 등장.
    2. 하위 카테고리(lower_cats) 정보를 이용해, 넥타이는 상의가 '셔츠'일 때만 등장.
    """
    generated_batch = []
    
    if engine is None:
        return []

    with engine.connect() as conn:
        # 1. 해당 페르소나의 대표 아이템 ID 모두 가져오기
        query = "SELECT product_id FROM representative_item WHERE persona = %s"
        df = pd.read_sql(query, conn, params=(persona,))
        
        if df.empty:
            st.error("해당 페르소나의 대표 아이템 데이터가 없습니다.")
            return []
        
        target_ids = df['product_id'].tolist()

    # 2. Master Data와 매핑하여 유효한 아이템 정보 및 카테고리 정보 확보
    id_to_idx = {pid: i for i, pid in enumerate(master_data['ids'])}
    
    # 카테고리별 인덱스 풀(Pool) 생성
    category_pool = {}
    
    for pid in target_ids:
        if pid in id_to_idx:
            idx = id_to_idx[pid]
            cat_name = master_data['cats'][idx] 
            
            if cat_name not in category_pool:
                category_pool[cat_name] = []
            category_pool[cat_name].append(idx)
            
    # 카테고리 매핑
    CATEGORY_MAP = {
        "outer": "아우터", 
        "top": "상의", 
        "bottom": "바지", 
        "shoes": "신발", 
        "acc": "액세서리"
    }

    progress_bar = st.progress(0)
    
    attempts = 0
    max_attempts = count * 20 

    while len(generated_batch) < count and attempts < max_attempts:
        attempts += 1
        
        current_set = {
            "persona": persona,
            "items": {},        
            "simple_items": {},
            "item_indices": {} # [추가] 검증 로직을 위해 master_data의 인덱스를 임시 저장
        }
        
        # 각 카테고리별로 랜덤하게 1개씩 추출
        for eng_key, kor_val in CATEGORY_MAP.items():
            # 액세서리 확률 등장 (20%)
            if eng_key == "acc":
                if np.random.rand() > 0.2: 
                    continue

            if kor_val in category_pool and category_pool[kor_val]:
                picked_idx = int(np.random.choice(category_pool[kor_val]))
                
                current_set["items"][eng_key] = {
                    "id": int(master_data['ids'][picked_idx]),
                    "name": str(master_data['names'][picked_idx]),
                    "img_url": str(master_data['imgs'][picked_idx]),
                    # UI에 표시할 때 참고하기 위해 하위 카테고리 정보도 같이 넣을 수 있음 (선택사항)
                    "sub_cat": str(master_data['lower_cats'][picked_idx]) 
                }
                current_set["simple_items"][eng_key] = int(master_data['ids'][picked_idx])
                current_set["item_indices"][eng_key] = picked_idx # 인덱스 저장

        # [수정된 룰] 하위 카테고리(lower_cats) 기반 넥타이 & 셔츠 규칙 적용
        if "top" in current_set["item_indices"] and "acc" in current_set["item_indices"]:
            top_idx = current_set["item_indices"]["top"]
            acc_idx = current_set["item_indices"]["acc"]
            
            top_sub = master_data['lower_cats'][top_idx]
            acc_sub = master_data['lower_cats'][acc_idx]
            
            # DB에 저장된 실제 하위 카테고리 명칭을 확인해야 함 (예: '셔츠', '넥타이')
            # 만약 데이터에 '셔츠/블라우스' 처럼 되어 있다면 in 연산자 사용 권장
            is_shirt = "셔츠/블라우스" in top_sub
            is_tie = "넥타이" in acc_sub
            
            # 넥타이인데 셔츠가 아니면 -> 액세서리 제거
            if is_tie and not is_shirt:
                del current_set["items"]["acc"]
                del current_set["simple_items"]["acc"]
                del current_set["item_indices"]["acc"]

        # 최소 조건: 상의, 바지, 신발 필수
        has_top = "top" in current_set["items"]
        has_bottom = "bottom" in current_set["items"]
        has_shoes = "shoes" in current_set["items"]
        
        if has_top and has_bottom and has_shoes:
            # 저장 시 불필요한 item_indices는 제거하고 저장
            del current_set["item_indices"]
            generated_batch.append(current_set)
            progress_bar.progress(len(generated_batch) / count)
        
    if len(generated_batch) < count:
        st.warning(f"조건을 만족하는 조합이 부족하여 {len(generated_batch)}개만 생성되었습니다.")

    return generated_batch

# ---------------------------------------------------------
# [3] UI 및 인터랙션 로직
# ---------------------------------------------------------
st.title("🧥 대표 아이템 기반 조합 평가")
st.markdown("대표 아이템들을 무작위로 조합했습니다. **어울리면 O, 아니면 X**를 눌러주세요.")

# 세션 상태 초기화
if 'batch_data' not in st.session_state:
    st.session_state.batch_data = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'labeled_results' not in st.session_state:
    st.session_state.labeled_results = []

# 사이드바
with st.sidebar:
    st.header("설정")
    persona_input = st.text_input("페르소나 입력", value="아메카지")
    
    if st.button("🚀 랜덤 조합 생성 (100개)"):
        with st.spinner('아이템 로드 및 조합 중...'):
            st.session_state.batch_data = generate_batch_outfits(persona_input, 100)
            st.session_state.current_index = 0
            st.session_state.labeled_results = [] 
        st.success(f"{len(st.session_state.batch_data)}개 조합 생성 완료!")

    st.markdown("---")
    st.write(f"현재 진행: {st.session_state.current_index} / {len(st.session_state.batch_data)}")
    
    if st.button("💾 결과 저장"):
        if st.session_state.labeled_results:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(st.session_state.labeled_results, f, ensure_ascii=False, indent=4)
            st.success(f"저장 완료: {OUTPUT_FILE}")
        else:
            st.warning("저장할 데이터가 없습니다.")

# 메인 화면
if st.session_state.batch_data:
    if st.session_state.current_index < len(st.session_state.batch_data):
        current_data = st.session_state.batch_data[st.session_state.current_index]
        items = current_data['items']
        
        st.subheader(f"조합 #{st.session_state.current_index + 1} (페르소나: {current_data['persona']})")
        
        # 이미지 갤러리
        display_order = ["outer", "top", "bottom", "shoes", "acc"]
        cols = st.columns(5)
        
        for idx, cat_key in enumerate(display_order):
            with cols[idx]:
                if cat_key in items:
                    info = items[cat_key]
                    st.image(info['img_url'], use_container_width=True)
                    # 하위 카테고리 정보가 있다면 같이 표시해주면 검증에 좋음
                    sub_text = f"({info.get('sub_cat', '')})" if 'sub_cat' in info else ""
                    st.caption(f"[{cat_key}] {info['name']} {sub_text}")
                else:
                    st.write("") 

        # 평가 버튼
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        
        def save_decision(label):
            result_entry = {
                "persona": current_data['persona'],
                "category_items": current_data['simple_items'], 
                "label": label, 
                "timestamp": datetime.now().isoformat()
            }
            st.session_state.labeled_results.append(result_entry)
            st.session_state.current_index += 1
            
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
    st.info("👈 왼쪽 사이드바에서 페르소나를 입력하고 '랜덤 조합 생성'을 눌러주세요.")