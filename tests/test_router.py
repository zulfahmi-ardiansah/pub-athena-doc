import pytest
from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "active_backend" in data


def test_list_documents_endpoint():
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    slugs = [d["slug"] for d in data["documents"]]
    assert "identity_card" in slugs
    assert "tax_number" in slugs


def test_demo_endpoint():
    response = client.get("/demo")
    assert response.status_code == 200
    assert "Athena Document Extractor" in response.text


def test_engine_singleton_dependency():
    from src.app.api.deps import get_engine_singleton
    from src.engines.base import BaseExtractionEngine
    engine1 = get_engine_singleton()
    engine2 = get_engine_singleton()
    assert isinstance(engine1, BaseExtractionEngine)
    assert engine1 is engine2

