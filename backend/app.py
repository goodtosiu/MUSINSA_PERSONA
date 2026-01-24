from flask import Flask
from flask_cors import CORS
from utils.data_loader import init_data
from routes.outfit import outfit_bp
from routes.price_ranges import price_ranges_bp
from routes.products import products_bp
from routes.static import static_bp

# Flask 앱 초기화
app = Flask(__name__)
CORS(app)

# 데이터 초기화
init_data()

# Blueprint 등록
app.register_blueprint(outfit_bp)
app.register_blueprint(price_ranges_bp)
app.register_blueprint(products_bp)
app.register_blueprint(static_bp)

if __name__ == '__main__':
    app.run(port=5000)