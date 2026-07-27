import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-psm-secret-key")
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'psm.db'}")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PSM_ADMIN_USER = os.getenv("PSM_ADMIN_USER", "admin")
    PSM_ADMIN_PASS = os.getenv("PSM_ADMIN_PASS", "changeme")

    AGNES_API_KEY = os.getenv("AGNES_API_KEY", "")
    AGNES_BASE_URL = os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
    AGNES_TEXT_MODEL = os.getenv("AGNES_TEXT_MODEL", "agnes-2.0-flash")
    AGNES_IMAGE_MODEL = os.getenv("AGNES_IMAGE_MODEL", "agnes-image-2.1-flash")

    QUOTA_TEXT_PER_LESSON = int(os.getenv("QUOTA_TEXT_PER_LESSON", "10"))
    QUOTA_IMAGE_PER_LESSON = int(os.getenv("QUOTA_IMAGE_PER_LESSON", "5"))
    AI_CONCURRENT_LIMIT = int(os.getenv("AI_CONCURRENT_LIMIT", "5"))
    IMAGE_WORKER_COUNT = int(os.getenv("IMAGE_WORKER_COUNT", "2"))
    IMAGE_WORKERS_ENABLED = os.getenv("IMAGE_WORKERS_ENABLED", "1").lower() in {"1", "true", "yes"}
    IMAGE_POST_TIMEOUT = float(os.getenv("IMAGE_POST_TIMEOUT", "35"))
    IMAGE_POST_TOTAL_TIMEOUT = float(os.getenv("IMAGE_POST_TOTAL_TIMEOUT", "75"))
    IMAGE_DOWNLOAD_TIMEOUT = float(os.getenv("IMAGE_DOWNLOAD_TIMEOUT", "20"))
    IMAGE_DOWNLOAD_TOTAL_TIMEOUT = float(os.getenv("IMAGE_DOWNLOAD_TOTAL_TIMEOUT", "45"))
    IMAGE_NETWORK_RETRIES = int(os.getenv("IMAGE_NETWORK_RETRIES", "2"))
    IMAGE_JOB_MAX_ATTEMPTS = int(os.getenv("IMAGE_JOB_MAX_ATTEMPTS", "2"))
    IMAGE_WORKER_POLL_INTERVAL = float(os.getenv("IMAGE_WORKER_POLL_INTERVAL", "0.25"))
    SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", "7200"))
    APPLICATION_ROOT = os.getenv("APPLICATION_ROOT", "/psm")
    # Cookie 路径用根 /，否则 /api/* 路径请求不携带 session → 前端"网络错误"
    SESSION_COOKIE_PATH = os.getenv("SESSION_COOKIE_PATH", "/")

    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "app" / "static" / "uploads"))

    # Derived
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
    ALLOWED_SCREENSHOT_EXT = {"png", "jpg", "jpeg"}


class TestConfig(Config):
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    WTF_CSRF_ENABLED = False
    IMAGE_WORKERS_ENABLED = False
