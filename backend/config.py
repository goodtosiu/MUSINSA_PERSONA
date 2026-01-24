import os

# 프로세스된 이미지 저장 디렉토리
PROCESSED_DIR = os.path.join(os.getcwd(), "static", "processed_imgs")
os.makedirs(PROCESSED_DIR, exist_ok=True)

# 카테고리 매핑
CATEGORY_MAP = {
    "outer": "아우터",
    "top": "상의",
    "bottom": "바지",
    "shoes": "신발",
    "acc": "액세서리"
}