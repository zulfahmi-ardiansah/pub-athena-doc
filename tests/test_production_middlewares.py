import pytest
from fastapi.testclient import TestClient
from fastapi import APIRouter
from src.app.main import create_app

client = TestClient(create_app())


def test_health_live_endpoint():
    resp = client.get("/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"


def test_health_ready_endpoint():
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["engine"]["status"] == "ready"
    assert data["checks"]["log_storage"]["status"] == "ready"
    assert data["checks"]["trace_storage"]["status"] == "ready"


def test_health_summary_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "otel_enabled" in data
    assert "pdp_masking_enabled" in data


def test_security_headers_present():
    resp = client.get("/health/live")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_request_and_correlation_id_headers():
    # If no header passed, should generate one
    resp = client.get("/health/live")
    assert "X-Request-ID" in resp.headers
    assert "X-Correlation-ID" in resp.headers

    # If incoming header is passed, should preserve it
    custom_req_id = "test-custom-req-12345"
    resp2 = client.get("/health/live", headers={"X-Request-ID": custom_req_id})
    assert resp2.headers.get("X-Request-ID") == custom_req_id


def test_error_handler_for_not_found():
    resp = client.get("/non-existent-path-for-testing")
    assert resp.status_code == 404
    data = resp.json()
    assert data["success"] is False
    assert "request_id" in data
    assert data["error"] == "HTTPException"


def test_error_handler_for_validation_error():
    # Calling extract endpoint without file payload
    resp = client.post("/api/v1/extract/identity_card")
    assert resp.status_code == 422
    data = resp.json()
    assert data["success"] is False
    assert "request_id" in data
    assert data["error"] == "ValidationError"
