"""D004 starter: fill in the TODOs, then compare against main.py.

Before coding, settle these in your head:
  - Which of my errors mean "the client messed up" (400) vs "we messed up" (5xx)?
  - What must be created ONCE at startup instead of on every request?
  - How will I test this without spending money on real API calls?
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from d002_message_models.solution import ChatRequest, ChatResponse  # noqa: E402
from d003_async_batch.solution import (  # noqa: E402
    BatchItem,
    Caller,
    FatalError,
    LLMError,
    RetryableError,
    batch_summarize,
    fake_call_llm,
)


# TODO 1: a Settings model (max_concurrency / timeout / max_retries)
#   plus get_settings() and get_caller() providers.
#   These exist so tests can swap them out - that is the whole point of Depends.
class Settings(BaseModel):
    max_concurrency: int = 10
    timeout: float = 2.0
    max_retries: int = 3


_settings = Settings()


def get_settings() -> Settings:
    return _settings


def get_caller() -> Caller:
    return fake_call_llm


# TODO 2: lifespan - create shared state before `yield`, clean up after.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: e.g. app.state.settings = _settings
    raise NotImplementedError("TODO 2 - startup")
    yield
    # shutdown: close pools / flush buffers
    raise NotImplementedError("TODO 2 - shutdown")


app = FastAPI(title="mini-llm-gateway", version="0.1.0", lifespan=lifespan)


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
        index=item.index,
        result=item.result,
        error=item.error,
        attempts=item.attempts,
    )


# TODO 3: map internal errors to HTTP status codes.
#   FatalError       -> 400  (client sent bad input)
#   RetryableError   -> 504  (upstream down after retries)
#   anything else    -> 500  (never leak internals)
def _raise_http(exc: LLMError) -> None:
    raise NotImplementedError("TODO 3")


# TODO 4: GET /health -> {"status": "ok"}
@app.get("/health")
async def health() -> dict[str, str]:
    raise NotImplementedError("TODO 4")


# TODO 5: POST /v1/chat
#   - take the last message content as the prompt
#   - empty prompt -> FatalError -> 400
#   - reuse batch_summarize with max_concurrency=1
#   - on failure map through _raise_http
#   - annotate `-> ChatResponse` so the docs and validation are generated
@app.post("/v1/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    caller: Caller = Depends(get_caller),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    raise NotImplementedError("TODO 5")


# TODO 6: POST /v1/batch -> BatchResponse with per-item results
@app.post("/v1/batch", response_model=BatchResponse)
async def batch(
    req: BatchRequest,
    caller: Caller = Depends(get_caller),
    settings: Settings = Depends(get_settings),
) -> BatchResponse:
    raise NotImplementedError("TODO 6")
