from flask import Blueprint, send_from_directory
from config import PROCESSED_DIR

static_bp = Blueprint('static', __name__)

@static_bp.route('/static/processed_imgs/<path:filename>')
def serve_processed_image(filename):
    return send_from_directory(PROCESSED_DIR, filename)