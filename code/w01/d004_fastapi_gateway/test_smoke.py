"""D004 smoke tests: the API comes up and the happy paths work.

    uv run pytest d004_fastapi_gateway -q

D005 goes deeper (mocking, edge cases, coverage). These just prove the wiring is alive.
"""

import pytest
from fastapi.testclient import TestClient

from d004_fastapi_gateway.main import app, get_caller


@pytest.fixture
def client() -> TestClient:
    """A deterministic caller: never fails, so smoke tests stay stable."""

    async def ok_caller(prompt: str) -> str:
        return f"summary({len(prompt)})"

    app.dependency_overrides[get_caller] = lambda: ok_caller
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client: TestClient):
    assert client.get("/health").json() == {"status": "ok"}


def test_chat_returns_a_response(client: TestClient):
    r = client.post(
        "/v1/chat",
        json={"model": "m", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["choices"][0]["message"]["content"] == "summary(5)"
    assert body["usage"]["total_tokens"] > 0


def test_chat_rejects_empty_message(client: TestClient):
    r = client.post(
        "/v1/chat", json={"model": "m", "messages": [{"role": "user", "content": "  "}]}
    )
    assert r.status_code == 400
    assert "bad request" in r.json()["detail"]


def test_chat_rejects_out_of_range_temperature(client: TestClient):
    r = client.post(
        "/v1/chat",
        json={
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 9.9,
        },
    )
    assert r.status_code == 422  # pydantic validation, caught before our code runs


def test_batch_partial_failure_is_reported(client: TestClient):
    r = client.post("/v1/batch", json={"prompts": ["a", "b", "c"]})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert body["ok"] == 3


def test_batch_rejects_empty_list(client: TestClient):
    assert client.post("/v1/batch", json={"prompts": []}).status_code == 422


def test_request_id_header_is_present(client: TestClient):
    r = client.get("/health")
    assert r.headers.get("X-Request-ID")


def test_openapi_schema_is_generated(client: TestClient):
    """D002's pydantic models are what makes this work - no extra code."""
    schema = client.get("/openapi.json").json()
    assert "/v1/chat" in schema["paths"]
    assert "ChatRequest" in schema["components"]["schemas"]
    assert "ChatResponse" in schema["components"]["schemas"]
