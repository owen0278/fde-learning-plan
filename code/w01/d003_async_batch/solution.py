"""D003 reference solution: concurrent batch LLM calls with throttling, timeout and retry.

Run:   uv run python d003_async_batch/solution.py
Test:  uv run pytest d003_async_batch -q
"""

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Errors: the whole retry strategy hangs on telling these two apart.
# --------------------------------------------------------------------------- #


class LLMError(Exception):
    """Base class for every gateway error."""


class RetryableError(LLMError):
    """Transient: timeout, 429, 5xx. Trying again can succeed."""


class FatalError(LLMError):
    """Permanent: empty prompt, bad auth, malformed params. Retrying only burns money."""


# --------------------------------------------------------------------------- #
# Fake upstream: deterministic enough to test, messy enough to be realistic.
# --------------------------------------------------------------------------- #

FAILURE_RATE = 0.25
Caller = Callable[[str], Awaitable[str]]


async def fake_call_llm(prompt: str) -> str:
    """Stand-in for a real call: random latency, random transient failures."""
    await asyncio.sleep(random.uniform(0.05, 0.30))
    if not prompt.strip():
        raise FatalError("empty prompt")
    if random.random() < FAILURE_RATE:
        raise RetryableError("upstream 503")
    return f"summary({len(prompt)})"


# --------------------------------------------------------------------------- #
# Result model: failures are DATA, not exceptions escaping the batch.
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# One item
# --------------------------------------------------------------------------- #


async def summarize_one(
    prompt: str,
    caller: Caller = fake_call_llm,
    *,
    sem: asyncio.Semaphore,
    timeout: float = 1.0,
    max_retries: int = 3,
) -> BatchItem:
    """Run a single call under a semaphore, with timeout and exponential backoff.

    Every failure is converted into a BatchItem so one bad row cannot kill the batch.
    """
    started = time.perf_counter()
    attempts = 0
    last_error: str | None = None

    for attempt in range(max_retries):
        attempts = attempt + 1
        try:
            async with sem:  # throttle: at most N calls in flight
                result = await asyncio.wait_for(caller(prompt), timeout=timeout)
            return BatchItem(
                index=-1,
                prompt=prompt,
                result=result,
                error=None,
                attempts=attempts,
                elapsed=time.perf_counter() - started,
            )
        except FatalError as exc:
            last_error = f"fatal: {exc}"
            break  # retrying cannot help
        except (RetryableError, TimeoutError) as exc:
            last_error = f"retryable: {exc}"
            if attempt < max_retries - 1:
                # exponential backoff + jitter, so failures do not re-spike together
                await asyncio.sleep((0.1 * 2**attempt) + random.uniform(0, 0.05))
        except Exception as exc:  # noqa: BLE001 - unknown errors must not kill the batch
            last_error = f"unexpected: {type(exc).__name__}: {exc}"
            break

    return BatchItem(
        index=-1,
        prompt=prompt,
        result=None,
        error=last_error,
        attempts=attempts,
        elapsed=time.perf_counter() - started,
    )


# --------------------------------------------------------------------------- #
# The batch
# --------------------------------------------------------------------------- #


async def batch_summarize(
    prompts: list[str],
    caller: Caller = fake_call_llm,
    *,
    max_concurrency: int = 10,
    timeout: float = 1.0,
    max_retries: int = 3,
) -> list[BatchItem]:
    """Fan out with a bounded number of in-flight calls.

    On failure semantics: gather() normally aborts siblings when one raises,
    but summarize_one never raises, so we always get a full result set.
    """
    sem = asyncio.Semaphore(max_concurrency)
    tasks = [
        summarize_one(p, caller, sem=sem, timeout=timeout, max_retries=max_retries) for p in prompts
    ]
    items = await asyncio.gather(*tasks)
    for i, item in enumerate(items):
        item.index = i
    return list(items)


def report(items: list[BatchItem]) -> str:
    ok = [i for i in items if i.ok]
    failed = [i for i in items if not i.ok]
    durations = sorted(i.elapsed for i in ok)
    p95 = durations[int(len(durations) * 0.95)] if durations else 0.0
    lines = [
        f"total={len(items)}  ok={len(ok)}  failed={len(failed)}",
        f"success_rate={len(ok) / len(items):.1%}" if items else "success_rate=n/a",
        f"p95_latency={p95:.2f}s",
    ]
    for i in failed[:3]:
        lines.append(f"  [{i.index}] attempts={i.attempts} {i.error}")
    if len(failed) > 3:
        lines.append(f"  ... and {len(failed) - 3} more")
    return "\n".join(lines)


async def main() -> None:
    random.seed(7)
    prompts = [f"ticket text #{i}: customer reported an issue" for i in range(40)]

    print("=== serial (baseline) ===")
    t0 = time.perf_counter()
    serial_ok = 0
    for p in prompts:
        try:
            await fake_call_llm(p)
            serial_ok += 1
        except LLMError:
            pass
    serial_elapsed = time.perf_counter() - t0
    print(f"ok={serial_ok}/{len(prompts)}  elapsed={serial_elapsed:.2f}s")

    print("\n=== concurrent (max_concurrency=10) ===")
    random.seed(7)
    t0 = time.perf_counter()
    items = await batch_summarize(prompts, max_concurrency=10)
    concurrent_elapsed = time.perf_counter() - t0
    print(report(items))
    speedup = serial_elapsed / concurrent_elapsed
    print(f"wall_clock={concurrent_elapsed:.2f}s  speedup={speedup:.1f}x")

    print("\n=== fatal errors are never retried ===")
    random.seed(7)
    bad = await batch_summarize(["", "   ", "valid text"], max_concurrency=3, max_retries=4)
    for i in bad:
        print(f"  [{i.index}] attempts={i.attempts} error={i.error}")


if __name__ == "__main__":
    asyncio.run(main())
