# Athena - Document Extractor

![Version](https://img.shields.io/badge/version-0.2.0-blue) ![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white) ![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white) ![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-enabled-F5A800?logo=opentelemetry&logoColor=white)

**Athena** is a FastAPI service that converts messy document images and multi-page PDFs (such as ID cards, tax forms, and receipts) into clean, typed, structured JSON. Extracting data from real-world documents is usually a headache: scanned PDFs have scrambled text layers, mobile uploads are taken at odd angles with potato cameras, and paying a cloud Vision LLM to parse every simple digital document burns through your API bill fast.

Athena fixes that by combining OpenCV computer vision deskewing, local CPU OCR, deterministic regex parsing, and multimodal Vision LLMs into an automated multi-tier pipeline. It extracts digital text in milliseconds, cascades to OCR or Vision LLMs only when needed, and validates everything into strict Pydantic schemas before returning your payload.

Athena operates across **three engines**, chosen via configuration or overridden per request:

| Engine | Identifier | Description | When to use |
|--------|------------|-------------|-------------|
| **Hybrid** *(Default)* | `hybrid_engine` | Cascades through Digital PDF -> CPU OCR -> Vision LLM based on confidence thresholds, followed by schema-guided structured LLM parsing. | General production use: optimal balance between speed, cost, and high accuracy. |
| **Visual** | `visual_engine` | Passes preprocessed images directly to a multimodal Vision LLM (Ollama or Google Gemini) for zero-step image-to-JSON inference. | Complex visual layouts, handwritten notes, or heavily degraded documents. |
| **String** | `string_engine` | Extracts text via PyMuPDF or local OCR (RapidOCR / Tesseract) and parses fields using deterministic regex rules with zero LLM calls. | High-throughput, offline, or resource-constrained CPU environments. |

---

## Architecture Overview

```
                            [ Client Request: PDF / Image ]
                                          │
                                          ▼
                         POST /api/v1/extract/{document_type}
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            ▼                             ▼                             ▼
    [ string_engine ]             [ visual_engine ]             [ hybrid_engine ]
            │                             │                             │
    CV Preprocessor               CV Preprocessor               CV Preprocessor
    (Deskew, CLAHE)               (Deskew, CLAHE)               (Deskew, CLAHE)
            │                             │                             │
    Digital PDF / OCR             Direct Vision LLM             Extraction Waterfall
   (RapidOCR / Tesseract)         (Ollama / Gemini)           (PDF -> OCR -> Vision LLM)
            │                             │                             │
    Deterministic Regex                   │                    Structured Analyzer
      Heuristic Parser                    │                   (Text LLM or Regex)
            │                             │                             │
            └─────────────────────────────┼─────────────────────────────┘
                                          ▼
                        Pydantic Validation & Normalization
                                          │
                                          ▼
                              [ Structured JSON Response ]
```

---

## How It Works

When you submit a document to `/api/v1/extract/{document_type}`, Athena executes a 6-step pipeline:

| # | Step | Component | What happens |
|---|------|-----------|--------------|
| 1 | **Validate request** | API Router & Registry | Checks file size against `MAX_FILE_SIZE_MB`, verifies `document_type` against registered schemas, and assigns a correlation `request_id`. |
| 2 | **CV Preprocessing** | Image Preprocessor | Converts PDF pages to raster images (at `IMAGE_RENDER_DPI`), fixes rotational tilt with OpenCV deskewing, and enhances contrast using CLAHE histogram equalization. |
| 3 | **Extract text** | Extractor Modules | In `hybrid_engine`, it grabs digital text layers first. If confidence score is below `EXTRACTION_MIN_CONFIDENCE`, it falls back to local OCR (RapidOCR or Tesseract), and finally to Vision LLM verbatim transcription. |
| 4 | **Analyze & structure** | Analyzer Modules | Maps raw extracted text into the schema using schema-guided LLM generation (`text_llm`) or deterministic regex rules (`string`). |
| 5 | **Validate & clean** | Pydantic Schema | Strips noise and prefixes (e.g. `PROVINSI`, `NIK:`), normalizes dates to `DD-MM-YYYY`, and formats missing values as `null`. |
| 6 | **Deliver & redact** | Telemetry & Logger | Returns the validated JSON payload, exports OpenTelemetry trace spans, and automatically masks sensitive personal data (NIK, NPWP, emails, tokens) in application logs. |

---

## Supported Documents

Athena ships with specialized domain models for Indonesian documents, returning clean structured JSON:

### 1. Identity Card (`identity_card` / Indonesian KTP)

Extracts 16-digit NIK, full name, address hierarchy, religion, marital status, and validity:

```json
{
  "province": "DKI JAKARTA",
  "city": "JAKARTA PUSAT",
  "id_number": "3171010101900001",
  "full_name": "BUDI SANTOSO",
  "birth_place": "JAKARTA",
  "birth_date": "01-01-1990",
  "gender": "LAKI-LAKI",
  "blood_type": "O",
  "address": "JL. JENDERAL SUDIRMAN NO. 45",
  "neighborhood_unit": "002/005",
  "village": "BENDUNGAN HILIR",
  "district": "TANAH ABANG",
  "religion": "ISLAM",
  "marital_status": "BELUM KAWIN",
  "occupation": "KARYAWAN SWASTA",
  "nationality": "WNI",
  "valid_until": "SEUMUR HIDUP"
}
```

### 2. Tax Identification Number (`tax_number` / Indonesian NPWP)

Extracts 15/16-digit NPWP, taxpayer name, registered KPP, and registration date:

```json
{
  "tax_id": "01.234.567.8-012.000",
  "taxpayer_name": "PT ADIDAYA WIKASITA",
  "nik": "3171010101900001",
  "address": "JL. GATOT SUBROTO KAV. 18",
  "tax_office": "KPP PRATAMA SETIABUDI DUA",
  "registration_date": "15-08-2018"
}
```

---

## Web Interface

Athena includes a browser-based test workspace served directly from the application when `ENABLE_DEMO=true`.

- **URL**: `http://localhost:8000/demo` (and `http://localhost:8000/`)
- **Capabilities**: Drag-and-drop file upload, live image preview and zoom, runtime engine/pipeline dropdown overrides, stage-by-stage evolution trace inspector, structured field viewer, raw JSON payload viewer with one-click copy, and dark/light theme switching.

---

## Quick Start with Docker (Recommended)

The Docker image bundles Python 3.13, OpenCV runtime libraries, and ONNX Runtime CPU dependencies.

### 1. Standard Setup

```bash
# Clone repository and prepare environment file
git clone <repo-url>
cd adw-pdc-athena
cp .env.example .env

# Build and start the API service
docker compose up -d --build
```

- **Web Demo UI**: <http://localhost:8000/demo>
- **Swagger API Docs**: <http://localhost:8000/docs>
- **Health Check**: <http://localhost:8000/health>

### 2. Companion Profiles

Athena supports optional companion containers via Docker Compose profiles:

```bash
# Start API with local containerized Ollama
docker compose --profile with-ollama up -d

# Start API with Jaeger distributed tracing dashboard (http://localhost:16686)
docker compose --profile with-telemetry up -d
```

---

## Local Development

### Requirements

- **Python 3.10+** (Python 3.13 recommended)
- **C/C++ compiler & OpenCV system libraries**
- *(Optional)* **Ollama** running locally on port 11434

### Installation

**Using `uv` (Recommended):**
```bash
uv sync --extra dev
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\Activate.ps1       # Windows PowerShell
```

**Using standard `venv` & `pip`:**
```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\Activate.ps1       # Windows PowerShell
pip install -e ".[dev]"
```

### Run Server

```bash
uvicorn src.app.main:app --reload --port 8000
```

---

## API Usage

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/extract/{document_type}` | Extract structured JSON from uploaded file (PDF, PNG, JPG) |
| `GET` | `/api/v1/documents` | List all supported document schemas and field definitions |
| `GET` | `/health` | Service status, active engine, LLM models, and telemetry info |
| `GET` | `/health/ready` | Readiness probe (verifies engine singleton, log and trace disk storage) |
| `GET` | `/health/live` | Lightweight liveness probe for Kubernetes and Docker healthchecks |

---

### Extract Document Request

```bash
curl -X POST "http://localhost:8000/api/v1/extract/identity_card?trace=true" \
  -H "accept: application/json" \
  -F "file=@ktp_sample.jpg"
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `trace` | `boolean` | `false` | Include stage-by-stage execution trace in response JSON |
| `keep_trace` | `boolean` | `false` | Persist debug images and artifacts in `trace/<uuid>/` on disk |
| `engine` | `string` | *(from .env)* | Override active engine (`hybrid_engine`, `visual_engine`, `string_engine`) |
| `analysis_mode` | `string` | *(from .env)* | Override analyzer mode (`text_llm`, `string`) |
| `pipeline` | `string` | *(from .env)* | Override extraction stages (e.g. `digital_pdf,ocr`) |

#### Sample Response

```json
{
  "success": true,
  "request_id": "8f3b2a10-9876-4c32-b5e1-0123456789ab",
  "document_type": "identity_card",
  "filename": "ktp_sample.jpg",
  "data": {
    "province": "DKI JAKARTA",
    "city": "JAKARTA PUSAT",
    "id_number": "3171010101900001",
    "full_name": "BUDI SANTOSO",
    "birth_place": "JAKARTA",
    "birth_date": "01-01-1990",
    "gender": "LAKI-LAKI",
    "blood_type": "O",
    "address": "JL. JENDERAL SUDIRMAN NO. 45",
    "neighborhood_unit": "002/005",
    "village": "BENDUNGAN HILIR",
    "district": "TANAH ABANG",
    "religion": "ISLAM",
    "marital_status": "BELUM KAWIN",
    "occupation": "KARYAWAN SWASTA",
    "nationality": "WNI",
    "valid_until": "SEUMUR HIDUP"
  },
  "trace": {
    "stages": [
      { "stage": "preprocess", "status": "success", "metadata": { "deskew_applied": true } },
      { "stage": "ocr", "status": "success", "confidence": 0.94, "backend": "rapidocr" },
      { "stage": "analyze", "status": "success", "analyzer": "text_llm", "model": "qwen2.5:3b" }
    ],
    "execution_time_ms": 320.4
  }
}
```

---

## Configuration Reference

Key settings configurable via environment variables or `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `ENGINE_TYPE` | `hybrid_engine` | Primary engine: `hybrid_engine`, `visual_engine`, or `string_engine` |
| `EXTRACTION_PIPELINE` | `digital_pdf,ocr,visual_llm` | Extraction sequence attempted by `hybrid_engine` |
| `EXTRACTION_MIN_CONFIDENCE` | `0.5` | Minimum extractor confidence score before cascading to next stage |
| `ANALYSIS_MODE` | `text_llm` | Analyzer mode: `text_llm` (LLM schema-guided) or `string` (deterministic regex) |
| `OCR_BACKEND` | `rapidocr` | OCR engine: `rapidocr` (CPU ONNX), `tesseract`, or `google_vision` |
| `LLM_TEXT_PROVIDER` | `ollama` | Provider for structured text analysis: `ollama` or `google` |
| `LLM_VISION_PROVIDER` | `ollama` | Provider for multimodal vision extraction: `ollama` or `google` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_TEXT_MODEL` | `qwen2.5:3b` | Ollama model for text extraction |
| `OLLAMA_VISION_MODEL` | `llama3.2-vision` | Ollama model for vision extraction |
| `PI_MASKING_ENABLED` | `true` | Automatically redact NIK, NPWP, emails, and tokens in application logs |
| `OTEL_ENABLED` | `false` | Enable OpenTelemetry distributed tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP collector gRPC or HTTP endpoint (e.g. Jaeger) |

---

## Adding New Document Types

Athena is designed to be easily extensible. To add a new document type, create a folder under `src/domain/documents/<slug>/` with the following files:

```
src/domain/documents/driver_license/
├── schema.py        # Pydantic schema with field definitions & validators
├── parser.py        # Deterministic regex parser for string_engine
├── prompt.py        # LLM system and user prompt templates
└── __init__.py      # DocumentSpecification export
```

Export a `DocumentSpecification` instance in `__init__.py`:

```python
from src.domain.base import DocumentSpecification
from .schema import DriverLicenseSchema
from .parser import DriverLicenseParser
from .prompt import DRIVER_LICENSE_PROMPT

DRIVER_LICENSE_DOC = DocumentSpecification(
    slug="driver_license",
    title="Surat Izin Mengemudi (SIM)",
    description="Indonesian Driver's License extraction model",
    schema_cls=DriverLicenseSchema,
    parser_cls=DriverLicenseParser,
    prompt_template=DRIVER_LICENSE_PROMPT,
)
```

The document specification is automatically discovered by `DocumentRegistry` and immediately available through the API and Web Demo without modifying core engine code.

---

## Testing

```bash
# Run test suite
pytest

# Run tests with verbose output
pytest -v -s
```

---

## License

Apache 2.0. See `LICENSE` for details.
