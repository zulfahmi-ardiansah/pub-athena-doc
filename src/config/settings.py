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

    # Engine backend selection: "ocr_hybrid" | "visual_model" | "local_cpu" | "cloud_google"
    engine_backend: Literal["ocr_hybrid", "visual_model", "local_cpu", "cloud_google"] = "ocr_hybrid"

    # OCR Engine for OCR Hybrid: "rapidocr" | "tesseract" | "vision_model" | "visual_model"
    ocr_engine: Literal["rapidocr", "tesseract", "vision_model", "visual_model"] = "rapidocr"
    tesseract_cmd: str = ""

    # OCR Image Preprocessing settings
    ocr_preprocess: bool = True
    ocr_deskew: bool = True
    ocr_enhance_contrast: bool = True
    ocr_threshold_mode: Literal["none", "otsu", "adaptive"] = "none"
    ocr_enhance_gamma: float = 1.15
    ocr_enhance_white_cutoff: int = 230
    ocr_enhance_black_level: int = 25

    # Interactive Demo UI at / or /demo & Trace Output
    enable_demo: bool = True
    trace_dir: str = "trace"

    # Ollama Local LLM / Vision
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_vision_model: str = "llama3.2-vision"
    ollama_timeout_seconds: float = 60.0
    ollama_keep_alive: str = "-1"
    ollama_preload: bool = True

    # Google Gemini Cloud
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # File constraints
    max_file_size_mb: int = 15


@lru_cache()
def get_settings() -> Settings:
    return Settings()
