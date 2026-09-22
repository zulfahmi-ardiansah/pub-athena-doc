# Athena - Document Extractor

![Version](https://img.shields.io/badge/version-1.0.0-blue) ![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white) ![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white) ![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-enabled-F5A800?logo=opentelemetry&logoColor=white)

**Athena** is a FastAPI service that converts messy document images and multi-page PDFs (such as ID cards, tax forms, and receipts) into clean, typed, structured JSON. Extracting data from real-world documents is usually a headache: scanned PDFs have scrambled text layers, mobile uploads are taken at odd angles with potato cameras, and paying a cloud Vision LLM to parse every simple digital document burns through your API bill fast.

Athena fixes that by combining OpenCV computer vision deskewing, local CPU OCR, deterministic regex parsing, and multimodal Vision LLMs into an automated multi-tier pipeline. It extracts digital text in milliseconds, cascades to OCR or Vision LLMs only when needed, and validates everything into strict Pydantic schemas before returning your payload.

Athena operates across **three engines**, chosen via configuration or overridden per request:

| Engine | Identifier | Description | When to use |
|--------|------------|-------------|-------------|
| **Hybrid** *(Default)* | `hybrid_engine` | Cascades through Digital PDF -> CPU OCR -> Vision LLM based on confidence thresholds, followed by schema-guided structured LLM parsing. | General production use: optimal balance between speed, cost, and high accuracy. |
| **Visual** | `visual_engine` | Passes preprocessed images directly to a multimodal Vision LLM (Ollama, Google Gemini, or an OpenAI-compatible endpoint) for zero-step image-to-JSON inference. | Complex visual layouts, handwritten notes, or heavily degraded documents. |
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
   (RapidOCR / Tesseract)      (Ollama / Gemini / OpenAI)     (PDF -> OCR -> Vision LLM)
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
| 5 | **Validate & clean** | Pydantic Schema | Strips noise and prefixes (e.g. `PROVINSI`, `NIK:`), normalizes dates to ISO 8601 `YYYY-MM-DD`, and formats missing values as `null`. |
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
  "birth_date": "1990-01-01",
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

Extracts 15/16-digit NPWP, taxpayer name, registered KPP branch office and address, and registration date:

```json
{
  "tax_number": "01.234.567.8-012.000",
  "tax_payer": "PT ADIDAYA WIKASITA",
  "branch_office": "KPP PRATAMA SETIABUDI DUA",
  "branch_address": "JL. GATOT SUBROTO KAV. 18",
  "registration_date": "2018-08-15"
}
```

### 3. Business Identification Number (`business_identification_number` / Indonesian NIB)

Extracts the 13-digit NIB, business actor name and contact details, investment status, issuance/amendment dates, and the full KBLI (business classification) attachment table:

```json
{
  "number": "2210210046937",
  "name": "PT Mitra BUMDes Nusantara",
  "office_address": "LIPPO KUNINGAN TOWER LANTAI 11, JL. H.R. RASUNA SAID KAV. B-12",
  "postal_code": "12940",
  "phone_number": "02121393278",
  "email": "mbn@mitrabumdes.co.id",
  "investment_status": "PMDN",
  "issued_place": "Jakarta",
  "issued_date": "2021-10-22",
  "amendment_number": "1",
  "amendment_date": "2025-03-19",
  "printed_date": "2025-03-19",
  "signing_official_title": "Menteri Investasi dan Hilirisasi/ Kepala Badan Koordinasi Penanaman Modal",
  "fields": [
    {
      "no": "1",
      "field_code": "46321",
      "field_title": "Perdagangan Besar Daging Sapi Dan Daging Sapi Olahan",
      "business_location": "GD. PUSAT PERUM BULOG LT. 10 JL. JEND. GATOT SUBROTO KAV.49",
      "postal_code": "12950",
      "risk_level": "Rendah",
      "licenses": [
        { "license_type": "NIB", "license_status": "Terbit", "remarks": null }
      ]
    },
    {
      "no": "39",
      "field_code": "46206",
      "field_title": "Perdagangan Besar Hasil Perikanan",
      "business_location": "GD. PUSAT PERUM BULOG LT. 10 JL. JEND. GATOT SUBROTO KAV.49",
      "postal_code": "12950",
      "risk_level": "Menengah Tinggi",
      "licenses": [
        { "license_type": "NIB", "license_status": "Terbit", "remarks": null },
        {
          "license_type": "Sertifikat Standar",
          "license_status": "Belum Terverifikasi",
          "remarks": "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 (sembilan puluh) hari kerja sebelum waktu perkiraan mulai beroperasi/produksi"
        }
      ]
    }
  ]
}
```

A KBLI row's "Perizinan Berusaha" block can require more than one license (e.g. both an NIB and a Sertifikat Standar), each with its own status and remarks - `licenses` captures one entry per stacked Jenis/Status/Keterangan sub-row rather than flattening them into a single field. The `string_engine` path only parses the header fields deterministically; `fields` is filled by the LLM-based engines (`hybrid_engine` / `visual_engine`) since the multi-page attachment table isn't reliably regex-parseable.

### 4. Taxable Entrepreneur Confirmation Letter (`taxable_entrepreneur` / Indonesian SPPKP / PKP)

Extracts the issuing tax office, NPWP, taxpayer name, business classification (KLU), address, checked tax obligation(s), and signing official details:

```json
{
  "letter_number": "S-47PKP/WPJ.05/KP.1003/2015",
  "tax_office_region": "KANTOR WILAYAH DJP JAKARTA BARAT",
  "tax_office": "KPP PRATAMA JAKARTA KEBON JERUK DUA",
  "tax_office_address": "JL. K.S. TUBUN 10, JAKARTA BARAT",
  "tax_number": "01.329.904.5-039.000",
  "taxpayer_name": "PT. RAMCOMAS MANDIRI",
  "business_fields": [
    { "code": "71100", "title": "JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA KONSULTASI TEKNIS YBDI" }
  ],
  "address": "JL.KEDOYA ANGSANA BLOK B II NO.25, KEDOYA SELATAN KEBON JERUK, JAKARTA BARAT DKI JAKARTA",
  "trade_name": null,
  "tax_obligation": "PPN",
  "confirmed_since": "1992-03-21",
  "issued_place": "Jakarta Barat",
  "issued_date": "2015-04-17",
  "signing_official_title": "a.n. Kepala Kantor Kepala Seksi Pelayanan",
  "signing_official_name": "MUNAWAM",
  "signing_official_number": "196005151981031001"
}
```

`tax_obligation` only lists the checked box(es) (e.g. `[X] PPN`), joined with `; ` if more than one is checked; `trade_name` is `null` when the source prints only a placeholder dash. Both the `string_engine` and LLM-based engines fully support this document, since it's a single fixed-layout page with no repeating table.

### 5. Passport (`passport` / any ICAO Doc 9303 issuing country)

Unlike the Indonesian document types above, a passport's printed labels vary by issuing country and language ("Surname"/"Nom"/"姓"/"성명"/"Apelyido"). What's universal is the **Machine Readable Zone (MRZ)** - two fixed-width 44-character lines at the bottom of every passport bio-data page worldwide - so extraction centers on that, plus the handful of visual fields present on essentially every passport regardless of country:

```json
{
  "document_type": "P",
  "issuing_country": "USA",
  "surname": "TRAVELER",
  "given_names": "HAPPY",
  "passport_number": "E00007734",
  "nationality": "USA",
  "date_of_birth": "1990-02-05",
  "sex": "F",
  "place_of_birth": "WASHINGTON D.C., U.S.A.",
  "date_of_issue": "2020-10-15",
  "date_of_expiry": "2030-10-14",
  "issuing_authority": "UNITED STATES DEPARTMENT OF STATE",
  "mrz_line1": "P<USATRAVELER<<HAPPY<<<<<<<<<<<<<<<<<<<<<<<<",
  "mrz_line2": "E000077347USA6502056F3010145900100120<095838"
}
```

The `string_engine` path parses the MRZ deterministically by fixed character position (ICAO Doc 9303 TD3 format), which works identically regardless of issuing country - it fills every MRZ-encoded field (everything above except `place_of_birth`, `date_of_issue`, and `issuing_authority`, which aren't in the MRZ and are only ever read from the printed page by the LLM-based engines).

---

## Web Interface

Athena ships a browser-based test workspace, served straight from the FastAPI app itself, no separate frontend build or dev server required. It's the fastest way to poke at the pipeline without writing a single `curl` command.

- **URL**: `http://localhost:8000/demo` (also mounted at the app root, `http://localhost:8000/`)
- **Toggle**: controlled by the `ENABLE_DEMO` setting (`true` by default). Set it to `false` to strip the UI out of production deployments.

**Features:** drag-and-drop upload with live image preview and zoom · runtime `engine` / `pipeline` / `analysis_mode` overrides per request, no `.env` edit or restart needed · stage-by-stage trace inspector (preprocess → extract → analyze) with per-stage status, timing, and confidence · structured field viewer next to the document preview · raw JSON viewer with syntax highlighting and one-click copy · dark/light theme switching.

Use it to sanity-check a new document type, compare engines side-by-side on the same file, or hand a non-technical teammate a way to try the API without Postman.

---

## Quick Start

Get the API running locally with [`uv`](https://docs.astral.sh/uv/), the fastest path from clone to first request. Prefer containers? Jump to [Deployment with Docker](#deployment-with-docker).

### Requirements

Before setting up Athena, make sure the following are available:

#### Python 3.10+

3.13 recommended, matching the Docker image. Verify with:

```bash
python --version
```

#### uv

Used to install dependencies and keep them pinned via `uv.lock`. Install per the [official guide](https://docs.astral.sh/uv/getting-started/installation/), then verify with:

```bash
uv --version
```

#### C/C++ compiler & OpenCV system libraries

Required to build `opencv-python-headless` and `rapidocr-onnxruntime`. On Debian/Ubuntu: `sudo apt-get install build-essential libgl1`. On Windows, the Build Tools for Visual Studio cover the compiler; OpenCV's Python wheel bundles its own runtime libraries.

#### Ollama *(optional)*

Only needed if you want local LLM inference instead of Google Gemini or an OpenAI-compatible API. Install from [ollama.com](https://ollama.com/) and confirm it's serving on port `11434`:

```bash
curl http://localhost:11434
```

#### OpenAI-compatible API key *(optional)*

Only needed if you want to use OpenAI, OpenRouter, or any other OpenAI Chat Completions-compatible endpoint (vLLM, LM Studio, Groq, etc.) instead of Ollama or Google Gemini. No install required, just an `OPENAI_API_KEY` and, for non-OpenAI endpoints, an `OPENAI_BASE_URL`.

### 1. Clone & configure

```bash
git clone <repo-url>
cd adw-pdc-athena
cp .env.example .env
```

Open `.env` and set at minimum an `ENGINE_TYPE` and, if using `hybrid_engine` or `visual_engine`, one of `OLLAMA_BASE_URL`, a Google Gemini API key, or an `OPENAI_API_KEY` / `OPENAI_BASE_URL` pair, see [Configuration Reference](#configuration-reference).

### 2. Sync the environment

`uv sync` resolves and installs dependencies into a project-local `.venv`, pinned to `uv.lock` for reproducible installs, no manual `pip install` needed.

```bash
uv sync --extra dev
```

### 3. Activate & run

```bash
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\Activate.ps1       # Windows PowerShell

uvicorn src.app.main:app --reload --port 8000
```

Or skip activation entirely and let `uv` run it in the managed environment directly:

```bash
uv run uvicorn src.app.main:app --reload --port 8000
```

- **Web Demo UI**: <http://localhost:8000/demo>
- **Swagger API Docs**: <http://localhost:8000/docs>
- **Health Check**: <http://localhost:8000/health>

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
    "birth_date": "1990-01-01",
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

Key settings configurable via environment variables or `.env`, grouped by topic:

### Engine & Pipeline

| Setting | Default | Description |
|---------|---------|-------------|
| `ENGINE_TYPE` | `hybrid_engine` | Primary engine: `hybrid_engine`, `visual_engine`, or `string_engine` |
| `EXTRACTION_PIPELINE` | `digital_pdf,ocr,visual_llm` | Extraction sequence attempted by `hybrid_engine` |
| `EXTRACTION_MIN_CONFIDENCE` | `0.5` | Minimum extractor confidence score before cascading to next stage |
| `ANALYSIS_MODE` | `text_llm` | Analyzer mode: `text_llm` (LLM schema-guided) or `string` (deterministic regex) |

### OCR & LLM Providers

| Setting | Default | Description |
|---------|---------|-------------|
| `OCR_BACKEND` | `rapidocr` | OCR engine: `rapidocr` (CPU ONNX), `tesseract`, or `google_vision` |
| `LLM_TEXT_PROVIDER` | `ollama` | Provider for structured text analysis: `ollama`, `google`, or `openai` |
| `LLM_VISION_PROVIDER` | `ollama` | Provider for multimodal vision extraction: `ollama`, `google`, or `openai` |

### Ollama

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_TEXT_MODEL` | `qwen2.5:3b` | Ollama model for text extraction |
| `OLLAMA_VISION_MODEL` | `llama3.2-vision` | Ollama model for vision extraction |

### OpenAI / OpenAI-Compatible

Targets any endpoint implementing the OpenAI Chat Completions wire format: OpenAI itself, OpenRouter, vLLM, LM Studio, Groq, etc. Tries native structured outputs (`json_schema`, strict mode) first, falling back to `json_object` mode for gateways/models that don't support strict schema enforcement.

| Setting | Default | Description |
|---------|---------|-------------|
| `OPENAI_API_KEY` | *(empty)* | API key for the target endpoint (leave empty for local servers that don't require one) |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Base URL of the OpenAI-compatible API, e.g. `https://openrouter.ai/api/v1` |
| `OPENAI_TEXT_MODEL` | `gpt-4o-mini` | Model for text extraction (OpenRouter-style prefixed IDs like `openai/gpt-4o-mini` also accepted) |
| `OPENAI_VISION_MODEL` | `gpt-4o-mini` | Model for vision extraction |
| `OPENAI_TIMEOUT_SECONDS` | `60.0` | Request timeout in seconds |

### Security & Observability

| Setting | Default | Description |
|---------|---------|-------------|
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
└── __init__.py      # BaseDocument subclass export
```

Subclass `BaseDocument` in `__init__.py`, wiring the schema, prompts, and (optionally) the string parser:

```python
from pydantic import BaseModel
from src.domain.base import BaseDocument
from .schema import DriverLicenseSchema
from .parser import DriverLicenseStringParser
from .prompt import get_driver_license_system_prompt, get_driver_license_user_prompt


class DriverLicenseDocument(BaseDocument):
    slug = "driver_license"
    name = "Surat Izin Mengemudi (SIM)"
    description = "Indonesian Driver's License extraction model"
    schema_class = DriverLicenseSchema

    def build_system_prompt(self) -> str:
        return get_driver_license_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_driver_license_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return DriverLicenseStringParser.parse(raw_text)


__all__ = ["DriverLicenseDocument", "DriverLicenseSchema", "DriverLicenseStringParser"]
```

Then register an instance in `src/domain/registry.py`'s `DocumentRegistry.__init__` (import the class at the top of the file and add `self.register(DriverLicenseDocument())`) to make it immediately available through the API and Web Demo without modifying core engine code. `parse_string` is optional — omit the override (or raise `NotImplementedError`, the `BaseDocument` default) for document types the `string_engine` can't reliably handle, e.g. multi-page tables.

---

## Deployment with Docker

For anything beyond local hacking, the Docker image is the recommended path. It bundles Python 3.13, the OpenCV runtime libraries, and ONNX Runtime CPU dependencies that `string_engine` and `hybrid_engine` need for OCR, so there's no host-level toolchain to fight with.

### 1. Standard deployment

```bash
# Clone repository and prepare environment file
git clone <repo-url>
cd adw-pdc-athena
cp .env.example .env

# Build and start the API service
docker compose up -d --build
```

This starts a single `athena-api` container, publishing `PORT` (default `8000`), mounting `./logs` and `./trace` for persistence, and running a `curl`-based healthcheck against `/health/live` every 30s.

- **Web Demo UI**: <http://localhost:8000/demo>
- **Swagger API Docs**: <http://localhost:8000/docs>
- **Health Check**: <http://localhost:8000/health>

### 2. Optional companion profiles

Compose profiles let you attach supporting services on demand, without bloating the base deployment:

| Profile | Command | Adds | Configure in `.env` |
|---|---|---|---|
| `with-ollama` | `docker compose --profile with-ollama up -d` | A containerized Ollama instance for local LLM inference, reachable from the API container. | `OLLAMA_BASE_URL=http://ollama:11434` |
| `with-telemetry` | `docker compose --profile with-telemetry up -d` | Jaeger all-in-one, exposing a trace UI at `http://localhost:16686` and OTLP gRPC/HTTP receivers. | `OTEL_ENABLED=true`, `OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317` |

Profiles combine, run both at once with `docker compose --profile with-ollama --profile with-telemetry up -d` for a fully self-contained local stack (API + LLM + tracing).

### 3. Credentials for Google Vision / Gemini

If using `google_vision` OCR or the `google` LLM provider, mount your service account JSON and point `GOOGLE_APPLICATION_CREDENTIALS` at it. Uncomment the relevant `volumes` line in `docker-compose.yml`:

```yaml
volumes:
  - ./secrets:/app/secrets:ro
```

### 4. Rebuilding after changes

```bash
docker compose up -d --build   # rebuild image and recreate the container
docker compose logs -f athena-api   # tail logs
docker compose down            # stop and remove containers (volumes persist)
```

---

## Testing

The suite lives under [`tests/`](tests/), one module per layer (`test_engines.py`, `test_domain.py`, `test_pi_sanitizer.py`, `test_telemetry.py`, etc.), with fixtures in [`tests/conftest.py`](tests/conftest.py). LLM/OCR calls are mocked, so `pytest` runs fully offline.

```bash
pytest                    # full suite
pytest -v -s               # verbose, with print() output
pytest tests/test_engines.py                                        # single module
pytest tests/test_router.py -k test_extract_endpoint_returns_valid_schema  # single test
```

---

## Troubleshooting

### `ModuleNotFoundError` or import errors on startup

**Cause:** Dependencies not installed, or installed into the wrong environment.

**Solution:** Run `uv sync --extra dev` and confirm the venv is activated (or prefix commands with `uv run`).

---

### OpenCV / `rapidocr-onnxruntime` fails to build or import

**Cause:** Missing C/C++ compiler or system libraries needed by `opencv-python-headless`.

**Solution:** Install a C/C++ toolchain (see [Requirements](#requirements)), or skip the problem entirely by running Athena via [Docker](#deployment-with-docker), which bundles these already.

---

### `Connection refused` calling Ollama (`OLLAMA_BASE_URL`)

**Cause:** Ollama isn't running locally, or the container can't reach a host-installed Ollama.

**Solution:** Start Ollama (`ollama serve`) and confirm `curl http://localhost:11434` responds. From inside Docker, point `OLLAMA_BASE_URL` at `http://host.docker.internal:11434` (host) or `http://ollama:11434` (the `with-ollama` profile container), not `localhost`.

---

### `422 Unprocessable Entity` on `/api/v1/extract/{document_type}`

**Cause:** File exceeds `MAX_FILE_SIZE_MB`, or `document_type` isn't a registered schema slug.

**Solution:** Check the limit in `.env`, and confirm the slug against `GET /api/v1/documents`.

---

### Google Vision / Gemini calls fail with auth errors

**Cause:** `GOOGLE_APPLICATION_CREDENTIALS` isn't set or the service account JSON isn't reachable from the process.

**Solution:** Locally, point the env var at your credentials file. In Docker, mount the file and uncomment the `volumes` line in `docker-compose.yml` (see [Deployment with Docker](#deployment-with-docker)).

---

### OpenAI-compatible provider calls fail with `401`/`403`, or return malformed JSON

**Cause:** Missing/invalid `OPENAI_API_KEY`, a wrong `OPENAI_BASE_URL` for the target gateway, or the model doesn't support strict `json_schema` structured outputs.

**Solution:** Verify the key and base URL against your provider's docs (e.g. `https://openrouter.ai/api/v1` for OpenRouter). Structured-output failures automatically retry once in `json_object` mode, if that model still can't return valid JSON, switch to a model known to support function/schema calling.

---

### Docker container healthcheck stays `unhealthy`

**Cause:** The app crashed on startup, or is still initializing past the healthcheck's `start_period`.

**Solution:** `docker compose logs -f athena-api` to see the actual startup error, usually a bad `.env` value or an unreachable LLM/OCR backend.
