import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'findback-enterprise-secret-key-2026-prod-alpha')
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'findback.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    
    # Matching algorithm weights (from project synopsis)
    MATCH_WEIGHT_DESCRIPTION = 0.50
    MATCH_WEIGHT_CATEGORY = 0.20
    MATCH_WEIGHT_LOCATION = 0.20
    MATCH_WEIGHT_DATE = 0.10
    
    # Matching threshold (out of 100)
    MATCH_THRESHOLD = 38.0
    HIGH_CONFIDENCE_THRESHOLD = 70.0
