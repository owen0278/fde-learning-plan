"""D004 reference solution: an HTTP gateway over the D002 models and the D003 engine.

Run:   uv run uvicorn d004_fastapi_gateway.main:app --reload
Docs:  http://127.0.0.1:8000/docs
Test:  uv run pytest d004_fastapi_gateway -q
"""

import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from d002_message_models.solution import (  # noqa: E402
    ChatRequest,
    ChatResponse,
)
from d003_async_batch.solution import (  # noqa: E402
    BatchItem,
    Caller,
    FatalError,
    LLMError,
    RetryableError,
    batch_summarize,
    fake_call_llm,
)

# --------------------------------------------------------------------------- #
# Settings + dependencies: everything the routes need is injected, never hard-coded.
# --------------------------------------------------------------------------- #


class Settings(BaseModel):
    max_concurrency: int = 10
    timeout: float = 2.0
    max_retries: int = 3


_settings = Settings()


def get_settings() -> Settings:
    """Injected config. Tests override this to shrink timeouts."""
    return _settings


def get_caller() -> Caller:
    """Injected upstream. Tests override this with a deterministic fake."""
    return fake_call_llm


# --------------------------------------------------------------------------- #
# Lifespan: build shared resources once at startup, tear them down at shutdown.
# --------------------------------------------------------------------------- #


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    app.state.settings = _settings
    app.state.started = True
    print("gateway up")
    yield
    # shutdown: close pools, flush buffers
    app.state.started = False
    print("gateway down")


app = FastAPI(
    title="mini-llm-gateway",
    version="0.1.0",
    description="W01 capstone: D002 models + D003 concurrency, served over HTTP.",
    lifespan=lifespan,
)


# --------------------------------------------------------------------------- #
# Middleware: give every response a request id you can grep in logs.
# --------------------------------------------------------------------------- #


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class BatchRequest(BaseModel):
    prompts: list[str] = Field(min_length=1, max_length=1000)


class BatchItemOut(BaseModel):
    index: int
    result: str | None
    error: str | None
    attempts: int


class BatchResponse(BaseModel):
    total: int
    ok: int
    failed: int
    items: list[BatchItemOut]


def _to_out(item: BatchItem) -> BatchItemOut:
    return BatchItemOut(
        index=item.index, result=item.result, error=item.error, attempts=item.attempts
    )


# --------------------------------------------------------------------------- #
# Error mapping: this table is what makes the API usable by a real client.
# --------------------------------------------------------------------------- #


def _raise_http(exc: LLMError) -> None:
    if isinstance(exc, FatalError):
        # the caller sent something wrong -> they must fix it
        raise HTTPException(status_code=400, detail=f"bad request: {exc}") from exc
    if isinstance(exc, RetryableError):
        # we tried and upstream is down -> our problem to own
        raise HTTPException(status_code=504, detail="upstream unavailable after retries") from exc
    raise HTTPException(status_code=500, detail="internal error") from exc


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe. Customer ops will poll this."""
    return {"status": "ok"}


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    caller: Caller = Depends(get_caller),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """Single chat turn. Uses the D002 request/response models end to end."""
    prompt = req.messages[-1].content or ""
    if not prompt.strip():
        _raise_http(FatalError("last message has no content"))

    items = await batch_summarize(
        [prompt],
        caller,
        max_concurrency=1,
        timeout=settings.timeout,
        max_retries=settings.max_retries,
    )
    item = items[0]
    if not item.ok:
        _raise_http(RetryableError(item.error or "upstream failed"))

    from d002_message_models.solution import Choice, Message, Role, Usage

    return ChatResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        model=req.model,
        choices=[
            Choice(
                index=0,
                message=Message(role=Role.ASSISTANT, content=item.result),
                finish_reason="stop",
            )
        ],
        usage=Usage(prompt_tokens=len(prompt.split()), completion_tokens=len(item.result or "")),
    )


@app.post("/v1/batch", response_model=BatchResponse)
async def batch(
    req: BatchRequest,
    caller: Caller = Depends(get_caller),
    settings: Settings = Depends(get_settings),
) -> BatchResponse:
    """Batch processing. Partial failure is normal and reported per item."""
    items = await batch_summarize(
        req.prompts,
        caller,
        max_concurrency=settings.max_concurrency,
        timeout=settings.timeout,
        max_retries=settings.max_retries,
    )
    ok = sum(1 for i in items if i.ok)
    return BatchResponse(
        total=len(items),
        ok=ok,
        failed=len(items) - ok,
        items=[_to_out(i) for i in items],
    )


@app.get("/v1/demo-error")
async def demo_error() -> dict[str, str]:
    """Shows how an internal error becomes a clean HTTP response."""
    _raise_http(FatalError("this endpoint always fails, on purpose"))
    return {"unreachable": "yes"}
