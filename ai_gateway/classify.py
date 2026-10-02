"""Clasificarea task-ului înainte de rutare (spec secțiunea 9).

A simple · B coding · C reasoning · D large_context · E search · F agentic.
Euristică pe conținutul cererii + override explicit prin header
`X-Task-Class` sau prin `metadata.task_class` din payload (clientul știe mai bine).
Clasa NU blochează nimic singură: alimentează scorul de calitate al modelului.
"""
from __future__ import annotations

from ai_gateway.estimate import payload_chars

TASK_ALIASES = {
    "a": "simple", "simple": "simple",
    "b": "coding", "coding": "coding",
    "c": "reasoning", "reasoning": "reasoning",
    "d": "large_context", "large_context": "large_context",
    "e": "search", "search": "search", "web": "search",
    "f": "agentic", "agentic": "agentic", "agent": "agentic",
}

REASONING_HINTS = ("arhitect", "architect", "trade-off", "tradeoff", "de ce", "why ",
                   "root cause", "cauză", "analizeaz", "compare", "design", "migrat",
                   "debugging", "securit")
CODING_HINTS = ("implement", "bug", "refactor", "fix ", "patch", "test ", "funcț",
                "function", "class ", "error", "traceback", "commit", "code")
SEARCH_HINTS = ("căut", "caut ", "search", "docs", "documenta", "versiune", "release",
                "stiri", "știri", "news", "azi", "astăzi", "prețuri actuale")


def classify(payload: dict, override: str | None = None, large_context_chars: int = 60_000,
             many_messages: int = 12) -> str:
    if override:
        normalized = TASK_ALIASES.get(override.strip().lower())
        if normalized:
            return normalized
    if payload.get("tools"):
        return "agentic"  # F: definiții de unelte = buclă agent (spec secțiunea 9.F)
    text = " ".join(
        m.get("content") if isinstance(m.get("content"), str) else ""
        for m in payload.get("messages") or []
    ).lower()
    messages = len(payload.get("messages") or [])
    chars = payload_chars(payload)
    if chars >= large_context_chars or messages >= many_messages:
        return "large_context"  # D
    if any(h in text for h in SEARCH_HINTS) and not any(h in text for h in CODING_HINTS):
        return "search"  # E
    if any(h in text for h in REASONING_HINTS):
        return "reasoning"  # C
    if any(h in text for h in CODING_HINTS):
        return "coding"  # B
    return "simple"  # A
