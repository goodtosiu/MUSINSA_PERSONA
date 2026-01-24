import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 환경 변수 로드 (실패해도 계속 진행)
try:
    load_dotenv()
except Exception:
    pass

# 데이터베이스 엔진 초기화
def get_db_engine():
    """데이터베이스 엔진을 생성하고 반환합니다."""
    db_url = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    return create_engine(db_url)

# 전역 엔진 인스턴스 (lazy initialization)
_engine = None

def get_engine():
    """전역 데이터베이스 엔진을 반환합니다."""
    global _engine
    if _engine is None:
        _engine = get_db_engine()
    return _engine