from fastapi.testclient import TestClient

from backend.app import create_app

client = TestClient(create_app())


def test_cors_headers_present() -> None:
    resp = client.options(
        "/health",
        headers={
            "origin": "http://localhost:5173",
            "access-control-request-method": "GET",
        },
    )
    assert "access-control-allow-origin" in resp.headers


def test_request_id_header_present() -> None:
    resp = client.get("/health")
    assert "X-Request-ID" in resp.headers
