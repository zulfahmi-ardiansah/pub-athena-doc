# Athena Document Extractor

High-performance modular FastAPI service for converting images and multi-page documents (PDF, PNG, JPEG) into typed structured JSON.

## Features

- **Document Specialization**: Built-in Indonesian domain models for:
  - **KTP** (`identity_card`): Extract 16-digit NIK, full names, addresses, RT/RW, etc.
  - **NPWP** (`tax_number`): Extract 15/16-digit NPWP, taxpayer name, KPP, etc.
- **Decoupled Pluggable Architecture**:
  - **File Preprocessor**: Image Preprocessor (deskew, CLAHE contrast enhancement, Otsu/adaptive thresholding, PDF rendering).
  - **Text Extraction Modules**:
    - Digital PDF Extractor (`PyMuPDF`) with confidence scoring.
    - OCR-based Extractor (`RapidOCR` ONNX CPU, `Tesseract`, `Google Cloud Vision OCR`).
    - Visual-LLM Extractor (multimodal verbatim transcription via `Ollama` or `Google Gemini`).
  - **Text Analysis Modules**:
    - String Text Analysis (Deterministic, zero-LLM regex/heuristic parsing).
    - LLM-based Text Analysis (Pydantic JSON schema-constrained generation via `Ollama` or `Google Gemini`).
    - Visual-LLM-based Text Analysis (Direct image-to-JSON multimodal inference).
- **Three Core Engines**:
  - `string_engine`: Preprocessor &rarr; (Digital PDF or OCR fallback) &rarr; Deterministic String Text Analysis.
  - `visual_engine`: Preprocessor &rarr; Direct Visual-LLM Multimodal JSON Analysis.
  - `hybrid_engine`: Preprocessor &rarr; Configurable Extraction Pipeline (`digital_pdf,ocr,visual_llm` cascading on low confidence) &rarr; Configurable Analysis (`llm` or `string`).

---

## Architecture Overview

```
                                [ Client Request ]
                                        │
                                        ▼
                         POST /api/v1/extract/{document_type}
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
     [ string_engine ]          [ visual_engine ]          [ hybrid_engine ]
             │                          │                          │
   Image Preprocessor           Image Preprocessor         Image Preprocessor
             │                          │                          │
   Digital PDF or OCR           Direct Multimodal           Extraction Priority
   (on low confidence)              Vision LLM            (PDF -> OCR -> Vision LLM)
             │                          │                          │
   Deterministic String                 │                  Configurable Analysis
      Text Analysis                     │                   (LLM or String Parser)
             │                          │                          │
             └──────────────────────────┼──────────────────────────┘
                                        ▼
                         Pydantic Validation & Normalization
                                        │
                                        ▼
                                [ JSON Response ]
```

---

## Getting Started

### 1. Requirements & Setup

```bash
# Clone repository and create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\Activate.ps1       # Windows PowerShell
.venv\Scripts\activate.bat       # Windows Command Prompt

# Install project dependencies from pyproject.toml:
pip install -e ".[dev]"
```

### 2. Configure Environment

Copy `.env.example` to `.env`:
```ini
# Primary Engine: "string_engine" | "visual_engine" | "hybrid_engine"
ENGINE_TYPE="hybrid_engine"

# Extraction Pipeline & Fallback Threshold (for hybrid_engine)
EXTRACTION_PIPELINE="digital_pdf,ocr,visual_llm"
EXTRACTION_MIN_CONFIDENCE=0.5
ANALYSIS_MODE="llm"

# OCR Backend: "rapidocr" | "tesseract" | "google_vision"
OCR_BACKEND="rapidocr"

# LLM Provider: "ollama" | "google"
LLM_PROVIDER="ollama"
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_TEXT_MODEL="qwen2.5:3b"
OLLAMA_VISION_MODEL="llama3.2-vision"
```

### 3. Run Development Server

```bash
uvicorn src.app.main:app --reload --port 8000
```

Interactive API documentation available at: `http://localhost:8000/docs`

---

## API Endpoints

### 1. Health Check
`GET /health`

### 2. List Supported Documents & Schemas
`GET /api/v1/documents`

### 3. Extract Document
`POST /api/v1/extract/{document_type}`
- Form Data: `file` (PDF, PNG, JPG)
- Query Params (optional):
  - `trace`: boolean (`true` / `false`)
  - `engine`: override engine (`string_engine`, `visual_engine`, `hybrid_engine`)
  - `analysis_mode`: override analyzer (`llm`, `string`)
  - `pipeline`: override extraction sequence (`digital_pdf,ocr,visual_llm`)
