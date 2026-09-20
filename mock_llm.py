"""A deterministic-enough mock LLM response for the tracker demo."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass(slots=True)
class MockResponse:
    content: str
    usage: dict[str, int]


def complete(prompt: str, *, rng: random.Random | None = None) -> MockResponse:
    """Return a response with realistic usage data and occasional failures."""
    rng = rng or random.Random()
    prompt_tokens = max(8, len(prompt.split()) + rng.randint(5, 20))
    completion_tokens = rng.randint(20, 100)
    delay = rng.uniform(0.005, 0.025)
    if rng.random() < 0.08:
        delay += 0.08
    time.sleep(delay)
    if rng.random() < 0.06:
        raise RuntimeError("mock provider timeout")
    return MockResponse(
        content="Mock answer generated from the prompt.",
        usage={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    )
