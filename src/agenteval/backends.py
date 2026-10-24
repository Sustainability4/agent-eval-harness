"""Pluggable LLM backends. Each exposes complete(system, user, prefix=None) -> str.

Select with --backend {anthropic,gemini,openai,mock}. Keys come from the
environment (or a .env file in the working directory): ANTHROPIC_API_KEY,
GEMINI_API_KEY (or GOOGLE_API_KEY), OPENAI_API_KEY.
`prefix` is a large, stable block (the corpus) sent before the user text;
backends that support prompt caching cache it.
After each call a backend sets `last_meta` (tokens, stop reason, ids) so runs
can be costed and refusals told apart from parse failures.
The mock backend needs no key and exists so the whole pipeline can be tested;
its outputs are NOT meaningful judgments and are labelled as such.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Dict, Optional, Protocol

# USD per million tokens (input, output), list prices as of October 2026; check your console.
# Cache writes cost 1.25x input and cache reads 0.1x input.
ANTHROPIC_PRICES = {
    "claude-fable-5-1": (10.00, 50.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1.00, 5.00),
}

# Models that reject output_config.effort.
_NO_EFFORT = ("claude-haiku-4", "claude-sonnet-4-5", "claude-3")


class Backend(Protocol):
    name: str
    last_meta: Dict[str, Any]

    def complete(self, system: str, user: str, prefix: Optional[str] = None) -> str: ...


def _join(prefix: Optional[str], user: str) -> str:
    return f"{prefix}\n\n{user}" if prefix else user


class AnthropicBackend:
    """Temperature is not set: current Claude models reject non-default sampling.
    Thinking depth is controlled with `effort` instead, where the model supports it."""

    def __init__(self, model: str = "claude-opus-5-5", effort: Optional[str] = "medium"):
        import anthropic  # lazy import

        self.client = anthropic.Anthropic(max_retries=6)
        self.model = model
        self.effort = effort if effort and not model.startswith(_NO_EFFORT) else None
        self.name = f"anthropic:{model}" + (f"-{self.effort}" if self.effort else "")
        self.last_meta: Dict[str, Any] = {}

    def complete(self, system: str, user: str, prefix: Optional[str] = None) -> str:
        content = [{"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}}] if prefix else []
        content.append({"type": "text", "text": user})
        extra = {"output_config": {"effort": self.effort}} if self.effort else {}
        # Thinking is on for most current models and counts toward max_tokens, so leave headroom.
        r = self.client.messages.create(model=self.model, max_tokens=16000, system=system,
                                        messages=[{"role": "user", "content": content}], **extra)
        u = r.usage
        self.last_meta = {
            "model": r.model, "effort": self.effort, "stop_reason": r.stop_reason, "request_id": r._request_id,
            "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
            "cache_creation_input_tokens": u.cache_creation_input_tokens or 0,
            "cache_read_input_tokens": u.cache_read_input_tokens or 0,
        }
        if r.stop_reason == "refusal":
            self.last_meta["refusal_category"] = r.stop_details.category if r.stop_details else None
            return ""
        return "".join(b.text for b in r.content if b.type == "text")


def anthropic_cost(meta: Dict[str, Any]) -> Optional[float]:
    """USD for one call from its last_meta, or None if the model has no price entry."""
    model = str(meta.get("model", ""))
    price = next((v for k, v in ANTHROPIC_PRICES.items() if model.startswith(k)), None)
    if price is None:
        return None
    pin, pout = price
    return (meta.get("input_tokens", 0) * pin + meta.get("cache_creation_input_tokens", 0) * pin * 1.25
            + meta.get("cache_read_input_tokens", 0) * pin * 0.1 + meta.get("output_tokens", 0) * pout) / 1e6


class GeminiBackend:
    """Runs at the model's default sampling, like the Claude backend, so judges are compared on vendor defaults."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        from google import genai  # lazy import

        key = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
        self.client = genai.Client(api_key=key)
        self.model = model
        self.name = f"gemini:{model}"
        self.last_meta: Dict[str, Any] = {}

    def complete(self, system: str, user: str, prefix: Optional[str] = None) -> str:
        from google.genai import types

        r = self.client.models.generate_content(
            model=self.model, contents=_join(prefix, user),
            config=types.GenerateContentConfig(system_instruction=system or None),
        )
        u = r.usage_metadata
        self.last_meta = {
            "model": self.model,
            "finish_reason": str(r.candidates[0].finish_reason) if r.candidates else None,
            "input_tokens": (u.prompt_token_count or 0) if u else 0,
            "output_tokens": ((u.candidates_token_count or 0) + (u.thoughts_token_count or 0)) if u else 0,
        }
        return r.text or ""


class Throttled:
    """Wraps a backend so it makes at most `rpm` calls per minute, for free tiers with per-minute limits."""

    def __init__(self, inner: Backend, rpm: float):
        self.inner, self.interval, self._last = inner, 60.0 / rpm, float("-inf")
        self.name = inner.name

    @property
    def last_meta(self) -> Dict[str, Any]:
        return self.inner.last_meta

    def complete(self, system: str, user: str, prefix: Optional[str] = None) -> str:
        import time

        wait = self._last + self.interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        return self.inner.complete(system, user, prefix)


class OpenAIBackend:
    def __init__(self, model: str = "gpt-4o-mini"):
        from openai import OpenAI  # lazy import

        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.model = model
        self.name = f"openai:{model}"
        self.last_meta: Dict[str, Any] = {}

    def complete(self, system: str, user: str, prefix: Optional[str] = None) -> str:
        r = self.client.chat.completions.create(
            model=self.model, temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": _join(prefix, user)}],
        )
        return r.choices[0].message.content or ""


class MockBackend:
    """Deterministic stand-in. Follows the gold plan when acting as an agent and
    produces hash-seeded scores when acting as a judge. For plumbing tests only."""

    name = "mock"

    def __init__(self, seed: int = 0):
        self.seed = seed
        self.last_meta: Dict[str, Any] = {}

    def complete(self, system: str, user: str, prefix: Optional[str] = None) -> str:
        if "MOCK_AGENT_PLAN" in user:
            # The agent harness embeds the gold plan step it expects next (mock only).
            m = re.search(r"MOCK_AGENT_PLAN:(.*)$", user, re.S)
            return m.group(1).strip() if m else '{"action": "final", "answer": "unknown"}'
        if "Score the trajectory" in user:
            h = int(hashlib.sha256((user + str(self.seed)).encode()).hexdigest(), 16)
            scores = {}
            for i, cid in enumerate(["C1", "C2", "C3", "C4", "C5", "C6", "C7"]):
                scores[cid] = (h >> (4 * i)) % 3
            return json.dumps({"scores": scores, "rationale": {c: "mock backend: not a real judgment" for c in scores}})
        return '{"action": "final", "answer": "unknown"}'


def make_backend(kind: str, model: str | None = None, effort: str | None = "medium") -> Backend:
    kind = kind.lower()
    if kind == "anthropic":
        return AnthropicBackend(model or "claude-opus-5-5", effort=effort)
    if kind == "gemini":
        return GeminiBackend(model or "gemini-2.5-flash")
    if kind == "openai":
        return OpenAIBackend(model or "gpt-4o-mini")
    if kind == "mock":
        return MockBackend()
    raise ValueError(f"unknown backend {kind}")
