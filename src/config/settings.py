from functools import lru_cache
from typing import List, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # 1. Core Application
    app_name: str = "Athena Document Extractor"
    debug: bool = True
    port: int = 8000
    host: str = "0.0.0.0"
    enable_demo: bool = True
    max_file_size_mb: int = 15
    trace_dir: str = "trace"

    # Primary Engine Backend
    engine_type: Literal["string_engine", "visual_engine", "hybrid_engine"] = "hybrid_engine"

    # 2. Workflow & Pipeline
    extraction_pipeline: str = "digital_pdf,ocr,visual_llm"
    extraction_min_confidence: float = 0.5
    analysis_mode: Literal["llm", "string"] = "llm"

    # 3. Image Preprocessing
    image_preprocess: bool = True
    image_deskew: bool = True
    image_enhance_contrast: bool = True
    image_threshold_mode: Literal["none", "otsu", "adaptive"] = "none"
    image_enhance_gamma: float = 1.15
    image_enhance_white_cutoff: int = 230
    image_enhance_black_level: int = 25
    image_render_dpi: int = 150

    # 4. OCR Backend
    ocr_backend: Literal["rapidocr", "tesseract", "google_vision"] = "rapidocr"
    tesseract_cmd: str = ""

    # 5. LLM Provider & Models
    llm_provider: Literal["ollama", "google"] = "ollama"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_text_model: str = "qwen2.5:3b"
    ollama_vision_model: str = "llama3.2-vision"
    ollama_timeout_seconds: float = 60.0
    ollama_keep_alive: str = "-1"
    ollama_preload: bool = True

    # Google Cloud & Gemini
    google_api_key: str = ""
    google_project_id: str = ""
    google_location: str = "us-central1"
    google_application_credentials: str = ""
    google_text_model: str = "gemini-1.5-flash"
    google_vision_model: str = "gemini-1.5-flash"

    def get_extraction_stages(self) -> List[str]:
        """Returns list of extraction stage names parsed from extraction_pipeline string."""
        if not self.extraction_pipeline:
            return ["digital_pdf", "ocr", "visual_llm"]
        return [s.strip().lower() for s in self.extraction_pipeline.split(",") if s.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
