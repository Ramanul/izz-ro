"""Provider Gemini prin REST (fara SDK/grpc). Cheia: GEMINI_API_KEY (din mediu, niciodata in cod)."""
import json
import os
import urllib.error
import urllib.request

from .base import Provider

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


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
                "thinkingConfig": {"thinkingBudget": 0},  # task simplu -> fara thinking (rapid, deterministic)
            },
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
