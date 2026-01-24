import requests
from io import BytesIO
from PIL import Image
from rembg import remove

def process_and_save_image(image_url, save_path):
    """
    이미지 URL에서 이미지를 다운로드하여 누끼를 제거하고 저장합니다.

    Args:
        image_url (str): 원본 이미지 URL
        save_path (str): 저장할 파일 경로

    Returns:
        bool: 처리 성공 여부
    """
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