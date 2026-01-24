import os
import numpy as np

# 전역 데이터 저장소
master_data = {}

def init_data():
    """
    master_data.npz 파일에서 데이터를 로드하고 전처리합니다.
    """
    global master_data
    try:
        path = '../data/master_data.npz'
        if not os.path.exists(path):
            print(f"🚨 [오류] {path} 파일 없음")
            return False

        data = np.load(path, allow_pickle=True)
        required_keys = ['ids', 'names', 'prices', 'imgs', 'cats',
                         'name_vecs', 'brand_vecs', 'img_vecs', 'cat_vecs']
        temp_data = {}

        for key in required_keys:
            if key not in data:
                print(f"❌ [키 누락] {key}")
                return False

            val = data[key]
            if key.endswith('_vecs'):
                try:
                    if val.dtype == object or isinstance(val, list):
                        temp_data[key] = np.array([np.array(x, dtype=np.float32) for x in val])
                    else:
                        temp_data[key] = val.astype(np.float32)
                except Exception:
                    temp_data[key] = val
            else:
                temp_data[key] = val

        master_data = temp_data
        print(f"✅ 데이터 로드 완료! (총 {len(master_data['ids'])}개)")
        return True

    except Exception as e:
        print(f"❌ 데이터 로딩 에러: {e}")
        return False

def get_master_data():
    """전역 master_data를 반환합니다."""
    return master_data