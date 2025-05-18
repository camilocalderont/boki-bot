from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

class Settings:
    META_TOKEN: str = os.getenv("META_BOT_TOKEN")
    PHONE_ID: str = os.getenv("META_NUMBER_ID")
    VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN")
    GRAPH_API_VERSION: str = os.getenv("META_VERSION", "v22.0")
    BASE_URL: str = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

@lru_cache
def get_settings() -> Settings:
    return Settings()
