# AGENTS.md

Athena is a FastAPI service that extracts structured JSON from Indonesian documents (KTP, NPWP, NIB, ...). Full setup and API docs: [README.md](README.md). This file is the standard for extending and working in this codebase.

## Project shape

- **Pipeline**: preprocess -> extract -> analyze -> validate -> deliver. Runs through one of three engines (`src/engines/`): `string_engine` (regex-only, no LLM, fastest/offline), `visual_engine` (sends the page image straight to a vision LLM), `hybrid_engine` (OCR/PDF text extraction, then a text LLM). Pick engine via the `ENGINE_TYPE` setting.
- **Document modules** live at `src/domain/documents/<slug>/`, one folder per document type (`identity_card`, `tax_number`, `business_number`). Each is a self-contained `BaseDocument` subclass (`src/domain/base.py`) registered in `src/domain/registry.py`. See "Adding a new document module" below before touching one.
- **LLM providers** (`src/providers/`): Google Gemini, OpenAI-compatible (covers OpenAI, OpenRouter, vLLM, LM Studio, Groq via `OPENAI_BASE_URL`), Ollama.
- **PI masking**: `src/utility/pi_sanitizer.py` auto-redacts NIK, NPWP, phone, email, and credit-card-shaped values from application logs when `PI_MASKING_ENABLED=true` (default). If a new document type's ID number is comparably sensitive personal data, add a matching `mask_xxx()` function there and a test in `tests/test_pi_sanitizer.py`. A business-registry number like NIB is public record and does not need masking — see the NIB module for that call already made.

## Commands

```bash
uv sync --extra dev                                    # install deps
uv run uvicorn src.app.main:app --reload --port 8000    # run dev server (also: http://localhost:8000/demo)
python -m pytest -q                                     # run the full test suite
python -m pytest tests/test_domain.py -q                 # run just the document-module tests
```

No linter or formatter is configured in this repo (no ruff/black config in `pyproject.toml`) — match the surrounding file's style by eye rather than running a tool. `pyright` is configured (`pyrightconfig.json`) but not installed in every environment; if it's available, run it, but don't treat its absence as a blocker.

## Code style

- Python 3.10+, Pydantic v2 (`BaseModel`, `Field`, `field_validator(mode="before")`).
- Type hints on all function signatures; `Optional[X]` over `X | None` (matches the rest of the codebase).
- No docstrings/comments unless they explain a non-obvious *why* (a quirk in the source document, a workaround). Don't restate what the code already says.
- Don't add abstractions, config flags, or error handling for cases the document/pipeline can't actually hit — this codebase favors small, direct, per-document-type files over shared frameworks.

## Adding a new document module

Work through these steps in order; each has its own completion criterion.

1. **Get a real sample.** Read an actual specimen of the document (a PDF/image in `reference/`, or one the user provides) before writing a single field. Done when you can list every printed field, every repeating/tabular structure, and every quirk (multi-value cells, placeholder dashes, textual dates) the source actually contains — not just the fields you'd guess it has. If several variants exist (e.g. the same document from different countries, like `passport`), read all of them before designing the schema: look for an invariant, standardized zone shared across every variant (a passport's MRZ, a QR/barcode payload) and prefer it over any single variant's visual labels, which differ by issuing region/language and can't be parsed with one generic regex.
2. **Scaffold the folder.** Create `src/domain/documents/<slug>/` with `schema.py`, `parser.py`, `prompt.py`, `__init__.py`, mirroring `src/domain/documents/tax_number/` file-for-file. `<slug>` is the descriptive English name, not an acronym (`tax_number`, not `npwp`). Done when all four files exist and import cleanly.
3. **Write the schema** (`schema.py`) per the schema reference below. Done when every field the sample showed has a `Field` entry and, where the raw text needs cleanup, a `field_validator`.
4. **Write the prompt** (`prompt.py`) per the prompt reference below. Done when the field/label/rule table covers every schema field and the guidelines call out every quirk step 1 found.
5. **Write the string parser** (`parser.py`) per the parser reference below. Done when every field regex-extractable from a single-page layout is covered; multi-page tabular fields are left `None` rather than forced.
6. **Register it.** Add the import and `self.register(XxxDocument())` line in `src/domain/registry.py`.
7. **Write tests** in `tests/test_domain.py`: schema validation, `get_json_schema()` + prompt content, string-parser output. Extend the slug list assertions in `test_document_registry` and `tests/test_router.py`. Done when `python -m pytest -q` is green.
8. **Document it.** Add a sample-JSON entry under "Supported Documents" in `README.md`.

When a real extraction run comes back wrong (a field misformatted, a structure flattened that shouldn't be), fix it in **both** the prompt (guides the LLM) and the schema validator (catches it even when the LLM ignores the prompt), then add a regression test built from the actual bad output — never fix only one side.

## Schema reference (`schema.py`)

- Every field is `Optional[str]` with `Field(description=..., examples=[...])`. No enums, even for fields that look closed-set (investment status, gender) — OCR/LLM noise must not hard-fail validation.
- One `@field_validator(..., mode="before")` per field needing cleanup: strip the Indonesian source label prefix (`re.sub(r"^LABEL\s*[:\.]?\s*", "", ...)`), then normalize format.
- **All dates** normalize to ISO 8601 `YYYY-MM-DD` via `src/utility/date_utils.normalize_to_iso_date()` — it also parses Indonesian textual dates ("22 Oktober 2021"). Never leave a raw `DD-MM-YYYY` or textual date un-normalized.
- Flat strings by default. Introduce a nested `List[SomeItem]` model only for a genuinely repeating/tabular source structure. Go one level deeper only when a single row can independently repeat again (e.g. one KBLI row carrying several separate license entries, each with its own status and remarks) — collapsing that into a joined string loses real information.
- A schema with a nested model produces `$defs`/`$ref` in its JSON schema. `GoogleGenAIProvider._sanitize_schema_for_gemini` (`src/providers/google_provider.py`) must keep `$defs` (recurse into it, don't drop it) or the Gemini SDK's own schema resolver breaks with a `KeyError` on the nested model's name. Confirm with:
  ```bash
  python -c "from src.domain.documents.<slug>.schema import <Schema> as S; from src.providers.google_provider import GoogleGenAIProvider as P; print(P._sanitize_schema_for_gemini(S.model_json_schema()).get('\$defs'))"
  ```

## Prompt reference (`prompt.py`)

Two functions: `get_<slug>_system_prompt()` and `get_<slug>_user_prompt(raw_text)`. The system prompt is a markdown field/label/rule table followed by a numbered "STRICT GUIDELINES" block: zero-hallucination, output-format rules (e.g. the ISO date instruction), and an explicit rule for every ambiguous case the real sample showed (multi-value cells, placeholder dashes → null, multi-entry sub-rows). The user prompt wraps the OCR text in a fenced code block.

## Parser reference (`parser.py`)

A `XxxStringParser.parse(raw_text) -> XxxSchema` classmethod, regex only, no LLM, used by `string_engine`. Its output passes through `Schema.model_validate()`, so raw regex matches get cleaned by the schema's own validators — the parser doesn't need to normalize dates or strip labels itself. Leave a field `None` rather than force a fragile regex over a multi-page or table structure; the LLM-based engines (`hybrid_engine`, `visual_engine`) cover that case.

A document's standardized zone (e.g. a passport's MRZ) is fixed-position and identical across every variant, so it's a *stronger* case for a full deterministic parser than a single-country document's labels ever are — parse it by character position, not by label matching. See `src/domain/documents/passport/parser.py` for the pattern.

## Testing

`python -m pytest -q` must pass before any module is considered done. Tests never call a live LLM provider or OCR backend — those are mocked (see `tests/conftest.py`), so the full suite runs offline in a few seconds. The string parser and schema validators are pure-Python and fully testable without any fixtures beyond a literal OCR-text string.
