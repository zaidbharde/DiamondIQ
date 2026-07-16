import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-change-this-secret-key"
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
    DATABASE_PATH = os.getenv("DATABASE_PATH") or str(BASE_DIR / "Artifacts" / "predictions.db")
    MODEL_PATH = os.getenv("MODEL_PATH") or str(BASE_DIR / "Artifacts" / "model.pkl")
    PREPROCESSOR_PATH = os.getenv("PREPROCESSOR_PATH") or str(BASE_DIR / "Artifacts" / "preprocessor.pkl")
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    UPLOAD_FOLDER = str(BASE_DIR / "Artifacts" / "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    MAX_IMAGE_SIZE_MB = 10
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")
    JSON_SORT_KEYS = False
