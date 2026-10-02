"""Estimare conservatoare de tokeni înainte de trimitere (spec secțiunile 6, 15).

Regula: când providerul nu oferă usage exact, valoarea e marcată ESTIMATED, nu
prezentată ca exactă. Estimarea ~ chars/4 e deliberat pesimistă (+10%) pentru că
e folosită la poarta de buget: mai bine respingem devreme decât trecem plafonul.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

CHARS_PER_TOKEN = 4
SAFETY_FACTOR = 1.10


@dataclass
class RequestEstimate:
    input_tokens: int
    output_tokens: int
    total: int
    method: str = "estimate"

    @property
    def total_tokens(self) -> int:
        return self.total


def payload_chars(payload: dict) -> int:
    """Lungimea contextului care pleacă efectiv: mesaje + system + definitions de unelte."""
    parts: list[str] = []
    for message in payload.get("messages") or []:
        content = message.get("content")
        if isinstance(content, str):
            parts.append(content)
        else:
            parts.append(json.dumps(content, ensure_ascii=False))
    for tool in payload.get("tools") or []:
        parts.append(json.dumps(tool, ensure_ascii=False))
    return sum(len(p) for p in parts)


def estimate_request(payload: dict, default_output_tokens: int = 2048) -> RequestEstimate:
    max_tokens = int(payload.get("max_tokens") or payload.get("max_completion_tokens") or 0)
    output = max_tokens or default_output_tokens
    input_tokens = int(payload_chars(payload) / CHARS_PER_TOKEN * SAFETY_FACTOR) + 16
    return RequestEstimate(
        input_tokens=input_tokens,
        output_tokens=int(output * SAFETY_FACTOR),
        total=input_tokens + int(output * SAFETY_FACTOR),
    )


def estimate_text(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN) + 1
