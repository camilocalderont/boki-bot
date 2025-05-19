from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

class Settings:
    # WhatsApp Cloud API settings
    META_TOKEN: str = os.getenv("META_BOT_TOKEN")
    PHONE_ID: str = os.getenv("META_NUMBER_ID")
    VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN")
    GRAPH_API_VERSION: str = os.getenv("META_VERSION", "v22.0")
    BASE_URL: str = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    # NestJS API settings
    API_URL: str = os.getenv("API_URL", "http://localhost")
    API_PORT: str = os.getenv("API_PORT", "3000")
    API_VERSION: str = os.getenv("API_VERSION", "1")
    API_TOKEN: str = os.getenv("API_TOKEN", "")

@lru_cache
def get_settings() -> Settings:
    return Settings()