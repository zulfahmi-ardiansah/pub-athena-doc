from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App
    app_name: str = "Athena Document Extractor"
    debug: bool = True
    port: int = 8000
    host: str = "0.0.0.0"

    # Engine backend selection: "local_cpu" | "cloud_google"
    engine_backend: Literal["local_cpu", "cloud_google"] = "local_cpu"

    # Interactive Demo UI at / or /demo
    enable_demo: bool = True

    # Ollama Local LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = 60.0

    # Google Gemini Cloud
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # File constraints
    max_file_size_mb: int = 15


@lru_cache()
def get_settings() -> Settings:
    return Settings()
