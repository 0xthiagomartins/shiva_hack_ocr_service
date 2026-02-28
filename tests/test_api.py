import pytest
from fastapi.testclient import TestClient

from app.main import app

# Must match User created in conftest (Receipt has FK to user.id)
TEST_USER_ID = "test-user-id"

client = TestClient(app)

# Base64 mínimo de 1x1 pixel JPEG (válido)
MINIMAL_JPEG_B64 = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBEQACEQADAPEA/9k="


@pytest.fixture(autouse=True)
def mock_pipeline(monkeypatch):
    """Evita rodar Tesseract e LLM nos testes; apenas marca como processado."""
    def fake_run_pipeline(process_id: str, user_id: str, image_b64: str) -> None:
        from app.db import STATUS_PROCESSADO, set_status
        set_status(process_id, STATUS_PROCESSADO)
    monkeypatch.setattr("app.main.run_pipeline", fake_run_pipeline)


def test_process_ok():
    r = client.post(
        "/process",
        json={
            "process_id": "test-proc-1",
            "user_id": TEST_USER_ID,
            "image_b64": MINIMAL_JPEG_B64,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["process_id"] == "test-proc-1"
    assert data["status"] == "em processamento"
    assert "processamento" in data["message"].lower()


def test_process_missing_process_id():
    r = client.post(
        "/process",
        json={"user_id": "u", "image_b64": MINIMAL_JPEG_B64},
    )
    assert r.status_code == 422


def test_process_missing_user_id():
    r = client.post(
        "/process",
        json={"process_id": "p1", "image_b64": MINIMAL_JPEG_B64},
    )
    assert r.status_code == 422


def test_process_missing_image_b64():
    r = client.post(
        "/process",
        json={"process_id": "p1", "user_id": "u1"},
    )
    assert r.status_code == 422


def test_process_empty_process_id_returns_400():
    r = client.post(
        "/process",
        json={"process_id": "  ", "user_id": TEST_USER_ID, "image_b64": MINIMAL_JPEG_B64},
    )
    assert r.status_code == 400


def test_status_not_found():
    r = client.get("/status/nao-existe-123")
    assert r.status_code == 404


def test_status_after_process():
    pid = "status-test-1"
    client.post(
        "/process",
        json={"process_id": pid, "user_id": TEST_USER_ID, "image_b64": MINIMAL_JPEG_B64},
    )
    # Background task (mock) marca como processado
    r = client.get(f"/status/{pid}")
    assert r.status_code == 200
    data = r.json()
    assert data["process_id"] == pid
    assert data["status"] in ("em processamento", "processado")
