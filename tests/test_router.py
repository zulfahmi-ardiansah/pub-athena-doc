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
