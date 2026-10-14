from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "qwen/qwen-2.5-coder-32b-instruct"
    OPENROUTER_TIMEOUT: int = 60
    MAX_SOURCE_BYTES: int = 102400
    MAX_SOURCE_LINES: int = 3000
    DATABASE_URL: str = "sqlite:///./debugger.db"
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    # Provider routing order for OpenRouter (e.g. 'Cloudflare')
    OPENROUTER_PROVIDER_ORDER: str = ""
    # Max output tokens to avoid OpenRouter reserving the entire context window (e.g. 28k+ tokens) on pay-as-you-go balance
    OPENROUTER_MAX_TOKENS: int = 4096
    # Debug flag: set to true/1/yes to log raw AI responses (never logs API keys)
    DEBUG_AI_RESPONSES: bool = False

    @property
    def cors_origins(self) -> List[str]:
        if not self.FRONTEND_ORIGIN:
            return ["http://localhost:5173"]
        origins = [origin.strip() for origin in self.FRONTEND_ORIGIN.split(",") if origin.strip()]
        if "http://localhost:5173" not in origins:
            origins.append("http://localhost:5173")
        return origins

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
