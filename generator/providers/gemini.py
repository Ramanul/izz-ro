"""Provider Gemini prin REST (fara SDK/grpc). Cheia: GEMINI_API_KEY (din mediu, niciodata in cod).

Free-tier are limite pe minut: la 429/503 reincercam cu backoff exponential (se auto-regleaza).
"""
import json
import os
import time
import urllib.error
import urllib.request

from .base import Provider

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
MAX_RETRIES = 5


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self):
        self._key = os.getenv("GEMINI_API_KEY", "").strip()

    def available(self) -> bool:
        return bool(self._key)

    def complete(self, system: str, user: str) -> str:
        url = ENDPOINT.format(model=MODEL, key=self._key)
        body = json.dumps({
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingBudget": 0},  # task simplu -> fara thinking
            },
        }).encode("utf-8")

        last_exc = None
        for attempt in range(MAX_RETRIES):
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=40) as resp:
                    data = json.load(resp)
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except urllib.error.HTTPError as exc:
                last_exc = exc
                if exc.code in (429, 500, 503) and attempt < MAX_RETRIES - 1:
                    retry_after = exc.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after and retry_after.isdigit() else 2 ** (attempt + 1)
                    time.sleep(min(wait, 30))
                    continue
                raise
        raise last_exc
