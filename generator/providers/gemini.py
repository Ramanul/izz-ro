"""Provider Gemini prin REST (fara SDK/grpc).

GEMINI_API_KEY poate contine MAI MULTE chei (separate prin virgula/spatiu): la 429
pe o cheie, trece automat pe urmatoarea (failover) — dubleaza quota free-tier.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

from .base import Provider

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
THROTTLE = float(os.getenv("GEMINI_THROTTLE", "2.0"))   # pauza intre apeluri, anti rate-limit
RETRIES_PER_KEY = 2


def _keys() -> list:
    return [k for k in re.split(r"[,\s]+", os.getenv("GEMINI_API_KEY", "").strip()) if k]


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self):
        self._keys = _keys()
        self._idx = 0  # cheia curenta (persista intre apeluri -> evita cheile moarte)

    def available(self) -> bool:
        return bool(self._keys)

    def _payload(self, system: str, user: str) -> bytes:
        return json.dumps({
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.2, "maxOutputTokens": 1024,
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }).encode("utf-8")

    def complete(self, system: str, user: str) -> str:
        if THROTTLE:
            time.sleep(THROTTLE)
        body = self._payload(system, user)
        last_exc = None
        # incearca fiecare cheie, cu cateva reincercari pe cheie
        for _ in range(len(self._keys)):
            key = self._keys[self._idx]
            url = ENDPOINT.format(model=MODEL, key=key)
            for attempt in range(RETRIES_PER_KEY):
                try:
                    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=40) as resp:
                        data = json.load(resp)
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                except urllib.error.HTTPError as exc:
                    last_exc = exc
                    if exc.code in (429, 500, 503):
                        if attempt < RETRIES_PER_KEY - 1:
                            time.sleep(2 ** (attempt + 1))
                        break  # cheie limitata -> trece la urmatoarea
                    raise
            self._idx = (self._idx + 1) % len(self._keys)  # failover pe cheia urmatoare
        raise last_exc
