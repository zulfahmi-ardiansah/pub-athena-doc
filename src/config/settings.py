from functools import lru_cache
from typing import Any, List, Literal, Optional
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
    keep_trace_artifacts: bool = False

    # Primary Engine Backend
    engine_type: Literal["string_engine", "visual_engine", "hybrid_engine"] = "hybrid_engine"

    # 2. Workflow & Pipeline
    extraction_pipeline: str = "digital_pdf,ocr,visual_llm"
    extraction_min_confidence: float = 0.5
    analysis_mode: Literal["text_llm", "string"] = "text_llm"

    @field_validator("analysis_mode", mode="before")
    @classmethod
    def normalize_analysis_mode(cls, v: Any) -> str:
        val = str(v or "text_llm").strip().lower()
        if val in ("llm", "text_llm"):
            return "text_llm"
        if val == "string":
            return "string"
        raise ValueError(f"Invalid analysis_mode '{v}'. Allowed values are 'text_llm' or 'string'.")

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
    # Global fallback LLM Provider
    llm_provider: Literal["ollama", "google", "openai"] = "ollama"
    # Specific providers for text analysis vs visual extraction (fall back to llm_provider if not set)
    llm_text_provider: Optional[Literal["ollama", "google", "openai"]] = None
    llm_vision_provider: Optional[Literal["ollama", "google", "openai"]] = None

    @field_validator("llm_text_provider", "llm_vision_provider", mode="before")
    @classmethod
    def parse_optional_provider(cls, v: Any) -> Optional[str]:
        if not v or not str(v).strip():
            return None
        val = str(v).strip().lower()
        if val in ("ollama", "google", "openai"):
            return val
        raise ValueError(f"Invalid LLM provider '{v}'. Allowed values are 'ollama', 'google', or 'openai'.")

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

    # OpenAI / OpenAI-compatible (OpenAI, OpenRouter, vLLM, LM Studio, Groq, etc.)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_text_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 60.0

    # 6. Standardized Logging & Personal Information (PI) Privacy
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_dir: str = "logs"
    log_format: Literal["json", "text"] = "json"
    log_to_file: bool = True
    log_retention_days: int = 30
    log_max_bytes: int = 50 * 1024 * 1024  # 50 MB
    log_backup_count: int = 10
    pi_masking_enabled: bool = True
    pdp_masking_enabled: Optional[bool] = None

    @field_validator("pi_masking_enabled", mode="before")
    @classmethod
    def resolve_pi_masking(cls, v: Any, info: Any) -> bool:
        if v is not None:
            return bool(v)
        return True


    # 7. OpenTelemetry & Distributed Tracing
    otel_enabled: bool = False
    otel_service_name: str = "athena-doc-extractor"
    otel_service_version: str = "0.2.0"
    otel_exporter_otlp_endpoint: Optional[str] = None
    otel_exporter_otlp_protocol: Literal["grpc", "http/protobuf"] = "grpc"
    otel_sample_rate: float = 1.0

    def get_text_provider_type(self) -> Literal["ollama", "google", "openai"]:
        """Returns the effective provider type for text analysis."""
        return self.llm_text_provider or self.llm_provider

    def get_vision_provider_type(self) -> Literal["ollama", "google", "openai"]:
        """Returns the effective provider type for visual/image extraction."""
        return self.llm_vision_provider or self.llm_provider

    def get_extraction_stages(self) -> List[str]:
        """Returns list of extraction stage names parsed from extraction_pipeline string."""
        if not self.extraction_pipeline:
            return ["digital_pdf", "ocr", "visual_llm"]
        return [s.strip().lower() for s in self.extraction_pipeline.split(",") if s.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()

