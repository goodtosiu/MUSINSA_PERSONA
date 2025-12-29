import os
import random
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

current_dir = os.path.dirname(os.path.abspath(__file__))
# 카테고리별로 폴더를 나눈 경로
BASE_CACHE_DIR = os.path.join(current_dir, 'static', 'processed_images')

CATEGORIES = ["상의", "바지", "아우터", "신발"]

@app.route('/api/products', methods=['GET'])
def get_random_recommendations():
    final_result = {"targets": {}}
    
    for cat in CATEGORIES:
        cat_path = os.path.join(BASE_CACHE_DIR, cat)
        
        # 해당 카테고리 폴더의 파일 리스트 읽기
        if not os.path.exists(cat_path):
            os.makedirs(cat_path, exist_ok=True)
            return jsonify({"error": f"{cat} 폴더에 파일이 없습니다."}), 500
            
        files = [f for f in os.listdir(cat_path) if f.endswith('.png')]
        
        if not files:
            return jsonify({"error": f"{cat} 폴더가 비어있습니다."}), 500

        # 랜덤하게 타겟 1개, 추천 5개 뽑기 (중복 허용)
        # 프론트엔드에 '파일명' 자체를 넘겨버립니다.
        target_file = random.choice(files)
        rec_files = random.sample(files, min(len(files), 6))
        if target_file in rec_files: rec_files.remove(target_file)
        
        # 프론트엔드가 이해할 수 있게 경로 형식으로 전달
        final_result["targets"][cat] = f"{cat}/{target_file}"
        final_result[cat] = [f"{cat}/{f}" for f in rec_files[:5]]

    return jsonify(final_result)

@app.route('/api/remove-bg')
def remove_bg():
    # 이제 url 파라미터 대신 위에서 보낸 "카테고리/파일명"이 들어옵니다.
    img_path = request.args.get('url') 
    if not img_path: return "Path Required", 400
    
    full_path = os.path.join(BASE_CACHE_DIR, img_path)
    
    if os.path.exists(full_path):
        return send_file(full_path, mimetype='image/png')
    return "File Not Found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)