"""D005 reference tests: deep coverage of the D004 gateway, fully mocked.

    uv run pytest d005_testing -q
    uv run pytest d005_testing -q \
        --cov=d004_fastapi_gateway --cov-report=term-missing

Nothing here touches a real API. Every upstream behaviour is injected.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from d003_async_batch.solution import FatalError, RetryableError
from d004_fastapi_gateway.main import Settings, app, get_caller, get_settings

# --------------------------------------------------------------------------- #
# Fake upstreams
# --------------------------------------------------------------------------- #


def always_ok(prompt: str):
    async def _c(p: str) -> str:
        return f"summary({len(p)})"

    return _c


def always_fatal(prompt: str):
    async def _c(p: str) -> str:
        raise FatalError("rejected by upstream")

    return _c


def always_retryable(prompt: str):
    async def _c(p: str) -> str:
        raise RetryableError("upstream 503")

    return _c


def slow(prompt: str):
    async def _c(p: str) -> str:
        await asyncio.sleep(5)
        return "too late"

    return _c


def flaky(fail_times: int):
    state = {"n": 0}

    async def _c(p: str) -> str:
        state["n"] += 1
        if state["n"] <= fail_times:
            raise RetryableError("transient")
        return f"ok:{p}"

    return _c


def fails_for(substring: str):
    async def _c(p: str) -> str:
        if substring in p:
            raise FatalError(f"poisoned: {substring}")
        return f"ok:{p}"

    return _c


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def client():
    """Yields (client, apply) where apply installs overrides and auto-clears after."""

    def apply(caller=None, settings=None):
        if caller is not None:
            app.dependency_overrides[get_caller] = lambda: caller
        if settings is not None:
            app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as c:
        yield c, apply
    app.dependency_overrides.clear()


FAST = Settings(max_concurrency=5, timeout=0.2, max_retries=1)


# --------------------------------------------------------------------------- #
# 1. happy path
# --------------------------------------------------------------------------- #


def test_chat_happy_path(client):
    c, apply = client
    apply(caller=always_ok("x"), settings=FAST)
    r = c.post("/v1/chat", json={"model": "m", "messages": [{"role": "user", "content": "hello"}]})
    assert r.status_code == 200
    body = r.json()
    assert body["choices"][0]["message"]["content"] == "summary(5)"
    assert body["usage"]["total_tokens"] > 0  # computed_field in action
    assert body["choices"][0]["finish_reason"] == "stop"


def test_chat_uses_only_the_last_message(client):
    c, apply = client
    seen = []

    async def spy(p: str) -> str:
        seen.append(p)
        return "ok"

    apply(caller=spy, settings=FAST)
    r = c.post(
        "/v1/chat",
        json={
            "model": "m",
            "messages": [
                {"role": "system", "content": "ignore me"},
                {"role": "user", "content": "use me"},
            ],
        },
    )
    assert r.status_code == 200
    assert seen == ["use me"]


# --------------------------------------------------------------------------- #
# 2. client errors: 422 from pydantic, 400 from our business rules
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "payload",
    [
        {"model": "m", "messages": []},  # empty messages
        {"model": "m", "messages": [{"role": "user", "content": ""}]},  # empty content
        {"model": "m", "messages": [{"role": "tool", "content": "x"}]},  # tool without id
        {"model": "", "messages": [{"role": "user", "content": "hi"}]},  # empty model
        {"messages": [{"role": "user", "content": "hi"}]},  # missing model
    ],
    ids=["no-messages", "empty-content", "tool-no-id", "empty-model", "missing-model"],
)
def test_pydantic_rejects_bad_payloads(client, payload):
    c, _ = client
    assert c.post("/v1/chat", json=payload).status_code == 422


@pytest.mark.parametrize("bad_temp", [-0.1, 2.5, "hot", None])
def test_temperature_validation(client, bad_temp):
    c, _ = client
    if bad_temp is None:
        return  # None falls back to the default, which is valid
    r = c.post(
        "/v1/chat",
        json={
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": bad_temp,
        },
    )
    assert r.status_code == 422


def test_business_rule_produces_400_not_422(client):
    """Whitespace-only content is structurally valid, so our code must reject it."""
    c, apply = client
    apply(caller=always_ok("x"), settings=FAST)
    r = c.post("/v1/chat", json={"model": "m", "messages": [{"role": "user", "content": "   "}]})
    assert r.status_code == 400
    assert "bad request" in r.json()["detail"]


# --------------------------------------------------------------------------- #
# 3. upstream down -> 504, and retries actually happened
# --------------------------------------------------------------------------- #


def test_upstream_always_fails_gives_504(client):
    c, apply = client
    settings = Settings(max_concurrency=1, timeout=0.2, max_retries=3)
    apply(caller=always_retryable("x"), settings=settings)
    r = c.post("/v1/chat", json={"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 504
    assert "upstream unavailable" in r.json()["detail"]


def test_timeout_is_mapped_to_504(client):
    c, apply = client
    settings = Settings(max_concurrency=1, timeout=0.05, max_retries=1)
    apply(caller=slow("x"), settings=settings)
    r = c.post("/v1/chat", json={"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 504


def test_retry_count_is_visible_in_batch(client):
    """max_retries=3 on a permanently failing upstream -> attempts == 3."""
    c, apply = client
    settings = Settings(max_concurrency=1, timeout=0.2, max_retries=3)
    apply(caller=always_retryable("x"), settings=settings)
    r = c.post("/v1/batch", json={"prompts": ["a"]})
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["attempts"] == 3
    assert item["error"] is not None


# --------------------------------------------------------------------------- #
# 4. transient failure then success
# --------------------------------------------------------------------------- #


def test_transient_failure_recovers(client):
    c, apply = client
    settings = Settings(max_concurrency=1, timeout=0.2, max_retries=3)
    apply(caller=flaky(2), settings=settings)
    r = c.post("/v1/batch", json={"prompts": ["hello"]})
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["result"] == "ok:hello"
    assert item["attempts"] == 3  # 2 failures then success


# --------------------------------------------------------------------------- #
# 5. partial failure in a batch
# --------------------------------------------------------------------------- #


def test_batch_reports_partial_failure(client):
    c, apply = client
    settings = Settings(max_concurrency=3, timeout=0.2, max_retries=1)
    apply(caller=fails_for("BAD"), settings=settings)
    r = c.post("/v1/batch", json={"prompts": ["good1", "BAD", "good2"]})
    assert r.status_code == 200  # partial failure is NOT a 5xx
    body = r.json()
    assert body["total"] == 3
    assert body["ok"] == 2
    assert body["failed"] == 1
    assert body["items"][1]["error"] is not None
    assert body["items"][0]["result"] == "ok:good1"


def test_batch_preserves_input_order(client):
    c, apply = client
    apply(caller=always_ok("x"), settings=FAST)
    prompts = [f"p{i}" for i in range(10)]
    body = c.post("/v1/batch", json={"prompts": prompts}).json()
    assert [i["index"] for i in body["items"]] == list(range(10))


# --------------------------------------------------------------------------- #
# 6. settings injection is honoured
# --------------------------------------------------------------------------- #


def test_settings_override_changes_behaviour(client):
    c, apply = client
    # with max_retries=1 a flaky(2) caller fails; with 3 it recovers
    apply(caller=flaky(2), settings=Settings(max_concurrency=1, timeout=0.2, max_retries=1))
    assert c.post("/v1/batch", json={"prompts": ["x"]}).json()["failed"] == 1

    apply(caller=flaky(2), settings=Settings(max_concurrency=1, timeout=0.2, max_retries=3))
    assert c.post("/v1/batch", json={"prompts": ["x"]}).json()["ok"] == 1


# --------------------------------------------------------------------------- #
# 7. operational concerns
# --------------------------------------------------------------------------- #


def test_health_always_ok_even_when_upstream_is_down(client):
    c, apply = client
    apply(caller=always_retryable("x"), settings=FAST)
    assert c.get("/health").status_code == 200


def test_error_response_never_leaks_internals(client):
    c, _ = client
    r = c.get("/v1/demo-error")
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "Traceback" not in detail
    assert "File \"" not in detail


def test_request_id_is_unique_per_request(client):
    c, _ = client
    ids = {c.get("/health").headers["X-Request-ID"] for _ in range(5)}
    assert len(ids) == 5
