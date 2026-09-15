"""D003 starter: fill in the TODOs, then compare against solution.py.

Think about these before coding:
  1. Where should the Semaphore be acquired - per item or once for the batch?
  2. Which exception types deserve a retry, and which must abort immediately?
  3. If one item explodes, should the other 999 lose their results?
"""

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


# TODO 1: define LLMError, then RetryableError and FatalError inheriting from it.
#   RetryableError -> timeout / 429 / 5xx, retrying can help
#   FatalError     -> empty prompt / bad auth, retrying is pointless
class LLMError(Exception):
    """Base class for every gateway error."""


class RetryableError(LLMError):
    """TODO 1"""


class FatalError(LLMError):
    """TODO 1"""


FAILURE_RATE = 0.25
Caller = Callable[[str], Awaitable[str]]


async def fake_call_llm(prompt: str) -> str:
    """Fake upstream: random latency, random transient failures. Do not edit."""
    await asyncio.sleep(random.uniform(0.05, 0.30))
    if not prompt.strip():
        raise FatalError("empty prompt")
    if random.random() < FAILURE_RATE:
        raise RetryableError("upstream 503")
    return f"summary({len(prompt)})"


@dataclass
class BatchItem:
    index: int
    prompt: str
    result: str | None
    error: str | None
    attempts: int
    elapsed: float

    @property
    def ok(self) -> bool:
        return self.error is None


async def summarize_one(
    prompt: str,
    caller: Caller = fake_call_llm,
    *,
    sem: asyncio.Semaphore,
    timeout: float = 1.0,
    max_retries: int = 3,
) -> BatchItem:
    """TODO 2: one call, throttled + timed out + retried. Never raises.

    Skeleton to complete:
        for attempt in range(max_retries):
            try:
                async with sem:
                    result = await asyncio.wait_for(caller(prompt), timeout=timeout)
                return BatchItem(...)          # success
            except FatalError as exc:
                last_error = ...; break        # never retry
            except (RetryableError, TimeoutError) as exc:
                last_error = ...
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.1 * 2**attempt + random.uniform(0, 0.05))
            except Exception as exc:
                last_error = ...; break        # unknown: record, do not crash the batch
        return BatchItem(...)                  # failure as data
    """
    raise NotImplementedError("TODO 2")


async def batch_summarize(
    prompts: list[str],
    caller: Caller = fake_call_llm,
    *,
    max_concurrency: int = 10,
    timeout: float = 1.0,
    max_retries: int = 3,
) -> list[BatchItem]:
    """TODO 3: build one Semaphore, fan out, fill in item.index, return the list."""
    raise NotImplementedError("TODO 3")


def report(items: list[BatchItem]) -> str:
    """TODO 4 (L2): total / ok / failed, success rate, p95 latency, first 3 failures."""
    raise NotImplementedError("TODO 4")


if __name__ == "__main__":
    random.seed(7)
    prompts = [f"ticket #{i}" for i in range(40)]
    items = asyncio.run(batch_summarize(prompts, max_concurrency=10))
    print(report(items))
