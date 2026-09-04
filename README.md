# Athena Document Extractor

High-performance modular FastAPI service for converting images and multi-page documents (PDF, PNG, JPEG) into typed structured JSON.

## Features

- **Document Specialization**: Built-in Indonesian domain models for:
  - **KTP** (`identity_card`): Extract 16-digit NIK, full names, addresses, RT/RW, etc.
  - **NPWP** (`tax_number`): Extract 15/16-digit NPWP, taxpayer name, KPP, etc.
- **Intelligent Triage Pipeline**:
  - Multi-page digital PDFs: Fast direct text extraction via `PyMuPDF` (0 GPU, <10ms).
  - Scanned PDFs / Photos: High-speed CPU OCR via `RapidOCR` (ONNX runtime, Apache-2.0).
  - Merges multi-page texts with page delimiters.
- **Structured JSON Schema Constraints**:
  - Forces GBNF grammar constraints on LLM token generation (100% syntactically valid JSON).
  - Zero-hallucination rules for critical numeric IDs (NIK, NPWP).
- **Pluggable Engine Architecture (Strategy Pattern)**:
  - `ocr_hybrid` (or `local_cpu`): Hybrid OCR & inference using `RapidOCR`/`Tesseract` + `Ollama` (`qwen2.5:3b`).
  - `visual_model`: Pure local multimodal vision inference using `Ollama` (`llama3.2-vision`, `qwen2.5-vl`, or `minicpm-v`).
  - `cloud_google`: Google Cloud Gemini 1.5 Flash multimodal extraction.

---

## Architecture Overview

```
                          [ Client Request ]
                                  │
                                  ▼
                   POST /api/v1/extract/{document_type}
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
          (PDF / Scanned / Digital)          (Image)
                    │                           │
                    ▼                           ▼
            PyMuPDF Inspector             RapidOCR (ONNX CPU)
         [Digital Text vs Render]               │
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                        Aggregated Text Stream
                                  │
                                  ▼
                     Structured LLM Provider
                 (Ollama Qwen2.5 / Google Gemini)
               [format = Pydantic JSON Schema]
                                  │
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
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`:
```ini
ENGINE_BACKEND=ocr_hybrid
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_KEEP_ALIVE=-1
OLLAMA_PRELOAD=true
```

> **Note:** `OLLAMA_PRELOAD=true` and `OLLAMA_KEEP_ALIVE=-1` ensure the model is automatically preloaded into RAM/VRAM during server startup and retained in memory indefinitely, eliminating cold-start latencies on inference.

### 3. Pull Recommended Ollama Model

```bash
ollama pull qwen2.5:3b
```

### 4. Run Development Server

```bash
uvicorn src.app.main:app --reload --port 8000
```

Interactive API documentation available at: `http://localhost:8000/docs`

---

## API Endpoints

### 1. Health Check
`GET /health`
```json
{
  "status": "healthy",
  "app_name": "Athena Document Extractor",
  "active_backend": "local_cpu",
  "ollama_model": "qwen2.5:3b"
}
```

### 2. List Supported Documents & Schemas
`GET /api/v1/documents`

### 3. Extract Document
`POST /api/v1/extract/{document_type}`
- Form Data: `file` (PDF, PNG, JPG)
- Supported `document_type`: `identity_card`, `tax_number`

**Example Response (`identity_card`):**
```json
{
  "success": true,
  "document_type": "identity_card",
  "filename": "ktp_sample.jpg",
  "data": {
    "id_number": "3171010101900001",
    "full_name": "JOHN DOE",
    "birth_place": "JAKARTA",
    "birth_date": "01-01-1990",
    "gender": "LAKI-LAKI",
    "blood_type": "O",
    "address": "JL. SUDIRMAN NO. 12",
    "neighborhood_unit": "001/002",
    "village": "GELORA",
    "district": "TANAH ABANG",
    "religion": "ISLAM",
    "marital_status": "KAWIN",
    "occupation": "KARYAWAN SWASTA",
    "nationality": "WNI",
    "valid_until": "SEUMUR HIDUP"
  }
}
```

---

## Adding New Document Types

1. Create a directory in `src/domain/documents/<new_type>/`.
2. Define Pydantic schema in `schema.py`.
3. Define prompt builders in `prompt.py`.
4. Create document class inheriting `BaseDocument` in `__init__.py`.
5. Register in `src/domain/registry.py`.
