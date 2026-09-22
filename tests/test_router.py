import io
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from src.app.main import app
from src.app.api.deps import get_engine_singleton
from src.engines.base import BaseExtractionEngine, ExtractionResult, ExtractionError
from src.utility.trace_utils import save_request_trace

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "active_engine" in data
    assert "ocr_backend" in data
    assert "llm_provider" in data
    assert "llm_text_provider" in data
    assert "llm_vision_provider" in data
    assert "keep_trace_artifacts" in data


def test_list_documents_endpoint():
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    slugs = [d["slug"] for d in data["documents"]]
    assert "identity_card" in slugs
    assert "tax_number" in slugs
    assert "business_identification_number" in slugs


def test_demo_endpoint():
    response = client.get("/demo")
    assert response.status_code == 200
    assert "Athena Document Extractor" in response.text


def test_engine_singleton_dependency():
    engine1 = get_engine_singleton()
    engine2 = get_engine_singleton()
    assert isinstance(engine1, BaseExtractionEngine)
    assert engine1 is engine2


def test_save_request_trace_utility(tmp_path):
    dummy_result = ExtractionResult(
        data={"id_number": "1234567890123456", "full_name": "TEST USER"},
        trace={
            "engine": "hybrid_engine",
            "stages": [
                {
                    "stage": 1,
                    "name": "extraction_pipeline",
                    "details": {
                        "pages": [
                            {
                                "page": 1,
                                "type": "image_ocr",
                                "preprocessing": {
                                    "deskew_applied": True,
                                    "images": {
                                        "deskewed": b"\x89PNG\r\n\x1a\nfake_deskew",
                                        "contrast_enhanced": b"\x89PNG\r\n\x1a\nfake_contrast",
                                        "preprocessed": b"\x89PNG\r\n\x1a\nfake_final"
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    )

    req_id = "test-uuid-12345"
    trace_dir, sanitized_trace = save_request_trace(
        request_id=req_id,
        file_bytes=b"dummy file content",
        filename="test_card.png",
        document_type="identity_card",
        extraction_result=dummy_result,
        trace_base_dir=str(tmp_path)
    )

    assert trace_dir.exists()
    assert sanitized_trace is not None
    assert (trace_dir / "original_test_card.png").read_bytes() == b"dummy file content"
    assert (trace_dir / "page_1_deskewed.png").read_bytes() == b"\x89PNG\r\n\x1a\nfake_deskew"
    assert (trace_dir / "page_1_contrast_enhanced.png").read_bytes() == b"\x89PNG\r\n\x1a\nfake_contrast"
    assert (trace_dir / "page_1_preprocessed.png").read_bytes() == b"\x89PNG\r\n\x1a\nfake_final"
    assert (trace_dir / "trace.json").exists()

    trace_json_content = json.loads((trace_dir / "trace.json").read_text(encoding="utf-8"))
    assert trace_json_content["request_id"] == req_id
    assert trace_json_content["document_type"] == "identity_card"
    assert trace_json_content["data"]["id_number"] == "1234567890123456"


def test_extract_endpoint_deletes_trace_folder_by_default_on_success(monkeypatch, tmp_path):
    mock_engine = MagicMock(spec=BaseExtractionEngine)
    mock_engine.name = "hybrid_engine"
    mock_engine.extract = AsyncMock(return_value=ExtractionResult(
        data={"id_number": "3171010101900001", "full_name": "BUDI SANTOSO"},
        trace={"engine": "hybrid_engine", "stages": []}
    ))

    app.dependency_overrides[get_engine_singleton] = lambda: mock_engine

    from src.config.settings import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "keep_trace_artifacts", False)
    monkeypatch.setattr(settings, "trace_dir", str(tmp_path))

    try:
        dummy_file = io.BytesIO(b"fake image bytes")
        response = client.post(
            "/api/v1/extract/identity_card",
            files={"file": ("sample_ktp.png", dummy_file, "image/png")},
            params={"trace": "false"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "request_id" in data
        req_id = data["request_id"]
        # Trace object should not be in JSON when trace=false
        assert "trace" not in data
        # Trace folder should be deleted by default on success
        assert "trace_dir" not in data
        target_dir = tmp_path / req_id
        assert not target_dir.exists()
    finally:
        app.dependency_overrides.clear()


def test_extract_endpoint_keeps_trace_folder_when_keep_trace_true(monkeypatch, tmp_path):
    mock_engine = MagicMock(spec=BaseExtractionEngine)
    mock_engine.name = "hybrid_engine"
    mock_engine.extract = AsyncMock(return_value=ExtractionResult(
        data={"id_number": "3171010101900001", "full_name": "BUDI SANTOSO"},
        trace={
            "engine": "hybrid_engine",
            "stages": [
                {
                    "stage": 1,
                    "name": "extraction_pipeline",
                    "details": {
                        "pages": [
                            {
                                "page": 1,
                                "type": "image_ocr",
                                "preprocessing": {
                                    "images": {
                                        "preprocessed": b"\x89PNG\r\n\x1a\npreprocessed_img"
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    ))

    app.dependency_overrides[get_engine_singleton] = lambda: mock_engine

    from src.config.settings import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "trace_dir", str(tmp_path))

    try:
        dummy_file = io.BytesIO(b"fake image bytes")
        response = client.post(
            "/api/v1/extract/identity_card",
            files={"file": ("sample_ktp.png", dummy_file, "image/png")},
            params={"trace": "true", "keep_trace": "true"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "request_id" in data
        req_id = data["request_id"]
        assert "trace_dir" in data
        assert "trace" in data

        target_dir = tmp_path / req_id
        assert target_dir.exists()
        assert (target_dir / "original_sample_ktp.png").exists()
        assert (target_dir / "page_1_preprocessed.png").exists()
        assert (target_dir / "trace.json").exists()
    finally:
        app.dependency_overrides.clear()


def test_extract_endpoint_supports_query_overrides():
    mock_engine = MagicMock(spec=BaseExtractionEngine)
    mock_engine.name = "hybrid_engine"
    mock_engine.extract = AsyncMock(return_value=ExtractionResult(
        data={"id_number": "3171010101900001", "full_name": "BUDI SANTOSO"},
        trace=None
    ))

    app.dependency_overrides[get_engine_singleton] = lambda: mock_engine

    try:
        dummy_file = io.BytesIO(b"fake image bytes")
        response = client.post(
            "/api/v1/extract/identity_card",
            files={"file": ("sample_ktp.png", dummy_file, "image/png")},
            params={"analysis_mode": "string", "pipeline": "ocr,visual_llm"}
        )

        assert response.status_code == 200
        mock_engine.extract.assert_awaited_once()
        call_kwargs = mock_engine.extract.call_args[1]
        assert call_kwargs["analysis_mode_override"] == "string"
        assert call_kwargs["pipeline_override"] == ["ocr", "visual_llm"]
    finally:
        app.dependency_overrides.clear()


def test_extract_endpoint_returns_trace_on_failure_when_trace_true():
    mock_engine = MagicMock(spec=BaseExtractionEngine)
    mock_engine.name = "hybrid_engine"
    mock_engine.extract = AsyncMock(side_effect=ExtractionError(
        message="Ollama produced invalid JSON: ",
        trace={
            "engine": "hybrid_engine",
            "stages": [
                {"stage": 1, "name": "extraction_pipeline", "status": "completed", "details": {}},
                {
                    "stage": 2,
                    "name": "text_analysis",
                    "status": "failed",
                    "details": {"error": "Ollama produced invalid JSON: ", "error_type": "ValueError"}
                }
            ]
        }
    ))

    app.dependency_overrides[get_engine_singleton] = lambda: mock_engine

    try:
        dummy_file = io.BytesIO(b"fake image bytes")
        response = client.post(
            "/api/v1/extract/identity_card",
            files={"file": ("sample_ktp.png", dummy_file, "image/png")},
            params={"trace": "true"}
        )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "request_id" in data
        assert "Ollama produced invalid JSON" in data["error"]
        assert "trace" in data
        assert data["trace"]["engine"] == "hybrid_engine"
        assert len(data["trace"]["stages"]) == 2
        assert data["trace"]["stages"][1]["status"] == "failed"
    finally:
        app.dependency_overrides.clear()
