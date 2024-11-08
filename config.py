from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    WEBHOOK_URL: str
    TELEGRAM_BOT_TOKEN: str
    DATABASE_URL: str

    class Config:
        env_file = ".env"

try:
    settings = Settings()
except Exception as e:
    raise RuntimeError(f"Configuration Error: {str(e)}")  