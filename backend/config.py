 import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./webscribe.db")
    MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "3"))
    MAX_PAGES_PER_TASK = int(os.getenv("MAX_PAGES_PER_TASK", "50"))
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30000"))
    SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "./data/screenshots")
    REPORT_DIR = os.getenv("REPORT_DIR", "./data/reports")
    USE_PROXY = os.getenv("USE_PROXY", "False").lower() == "true"
    PROXY_LIST = os.getenv("PROXY_LIST", "").split(",") if os.getenv("PROXY_LIST") else []
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

    @classmethod
    def ensure_dirs(cls):
        os.makedirs(cls.SCREENSHOT_DIR, exist_ok=True)
        os.makedirs(cls.REPORT_DIR, exist_ok=True)