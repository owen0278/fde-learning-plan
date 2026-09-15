"""D003 acceptance tests: run against solution.py.

    uv run pytest d003_async_batch -q

Tests inject deterministic callers through the `caller` parameter - no randomness,
no network, no API cost.
"""

import asyncio

import pytest

from d003_async_batch.solution import (
    BatchItem,
    FatalError,
    LLMError,
    RetryableError,
    batch_summarize,
    summarize_one,
)

# --------------------------------------------------------------------------- #
# deterministic fake callers
# --------------------------------------------------------------------------- #


def make_flaky(fail_times: int):
    """Fail with RetryableError the first `fail_times` calls, then succeed."""
    state = {"n": 0}

    async def caller(prompt: str) -> str:
        state["n"] += 1
        if state["n"] <= fail_times:
            raise RetryableError(f"fail #{state['n']}")
        return f"ok:{prompt}"

    return caller


# --------------------------------------------------------------------------- #
# error hierarchy
# --------------------------------------------------------------------------- #


def test_error_hierarchy():
    assert issubclass(RetryableError, LLMError)
    assert issubclass(FatalError, LLMError)


# --------------------------------------------------------------------------- #
# retry behaviour
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_retryable_error_is_retried_until_success():
    sem = asyncio.Semaphore(5)
    item = await summarize_one("x", make_flaky(2), sem=sem, max_retries=5)
    assert item.ok, item.error
    assert item.attempts == 3
    assert item.result == "ok:x"


@pytest.mark.asyncio
async def test_retryable_error_exhausting_retries_is_reported():
    sem = asyncio.Semaphore(5)
    item = await summarize_one("x", make_flaky(99), sem=sem, max_retries=3)
    assert not item.ok
    assert item.attempts == 3
    assert "retryable" in (item.error or "")


@pytest.mark.asyncio
async def test_fatal_error_is_not_retried():
    calls = {"n": 0}

    async def fatal(prompt: str) -> str:
        calls["n"] += 1
        raise FatalError("empty prompt")

    sem = asyncio.Semaphore(5)
    item = await summarize_one("", fatal, sem=sem, max_retries=4)
    assert not item.ok
    assert item.attempts == 1  # the whole point: one and done
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_timeout_is_treated_as_retryable():
    async def slow(prompt: str) -> str:
        await asyncio.sleep(5)
        return "too late"

    sem = asyncio.Semaphore(5)
    item = await summarize_one("x", slow, sem=sem, timeout=0.05, max_retries=2)
    assert not item.ok
    assert item.attempts == 2


# --------------------------------------------------------------------------- #
# batch behaviour
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_batch_returns_one_item_per_prompt():
    async def ok(prompt: str) -> str:
        return prompt.upper()

    items = await batch_summarize(["a", "b", "c"], ok, max_concurrency=2)
    assert len(items) == 3
    assert [i.index for i in items] == [0, 1, 2]
    assert [i.result for i in items] == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_one_failure_does_not_lose_other_results():
    async def mixed(prompt: str) -> str:
        if prompt == "bad":
            raise FatalError("bad input")
        return prompt.upper()

    items = await batch_summarize(["a", "bad", "c"], mixed, max_concurrency=3)
    assert len(items) == 3  # gather did not abort the siblings
    assert items[0].ok and items[2].ok
    assert not items[1].ok


@pytest.mark.asyncio
async def test_concurrency_is_bounded_by_the_semaphore():
    in_flight = {"now": 0, "peak": 0}

    async def tracked(prompt: str) -> str:
        in_flight["now"] += 1
        in_flight["peak"] = max(in_flight["peak"], in_flight["now"])
        await asyncio.sleep(0.02)
        in_flight["now"] -= 1
        return prompt

    await batch_summarize([f"p{i}" for i in range(20)], tracked, max_concurrency=4)
    assert in_flight["peak"] <= 4


@pytest.mark.asyncio
async def test_concurrency_beats_serial_on_wall_clock():
    async def slow(prompt: str) -> str:
        await asyncio.sleep(0.1)
        return prompt

    prompts = [f"p{i}" for i in range(20)]
    loop = asyncio.get_running_loop()

    t0 = loop.time()
    await batch_summarize(prompts, slow, max_concurrency=20)
    concurrent = loop.time() - t0

    t0 = loop.time()
    await batch_summarize(prompts, slow, max_concurrency=1)
    serial = loop.time() - t0

    assert concurrent < serial / 5


def test_batch_item_ok_property():
    assert BatchItem(0, "p", "r", None, 1, 0.1).ok
    assert not BatchItem(0, "p", None, "boom", 3, 0.1).ok
