import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always load .env from project root (not cwd / Docker service names)
_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "sqlite:///db.sqlite3"
    REDIS_URL: str = "redis://localhost:6379/0"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    ELEVENLABS_API_KEY: str = ""
    DEEPGRAM_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    DJANGO_BASE_URL: str = "http://localhost:8000"
    FASTAPI_BASE_URL: str = "http://localhost:8001"
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_APP_SID: str = ""
    TWILIO_API_KEY_SID: str = ""
    TWILIO_API_KEY_SECRET: str = ""

    @property
    def relay_ws_url(self) -> str:
        base = (self.FASTAPI_BASE_URL or "http://localhost:8001").rstrip("/")
        return base.replace("https://", "wss://").replace("http://", "ws://") + "/relay/ws"


settings = Settings()
