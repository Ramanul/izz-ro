"""Provider Ollama (model local, gratuit, fara cheie API). Serverul trebuie sa ruleze pe masina
(`ollama serve`, sau service-ul pornit automat de aplicatia Ollama) — vezi `OLLAMA_BASE_URL`.
"""
import json
import os
import urllib.error
import urllib.request

from .base import Provider

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
BASE_URL = (os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
ENDPOINT = BASE_URL + "/api/chat"
TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))  # model local pe CPU/GPU modest -> mult mai lent decat un API cloud


class OllamaProvider(Provider):
    name = "ollama"

    def available(self) -> bool:
        # Nu cere cheie, dar serverul trebuie sa fie sus — verifica /api/tags, ieftin.
        try:
            req = urllib.request.Request(BASE_URL + "/api/tags")
            with urllib.request.urlopen(req, timeout=3):
                return True
        except (urllib.error.URLError, OSError):
            return False

    def _complete(self, system: str, user: str) -> str:
        body = json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",  # JSON mode nativ Ollama -- acelasi rol ca responseMimeType la Gemini
            "options": {"temperature": 0.2},
        }).encode("utf-8")
        req = urllib.request.Request(ENDPOINT, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read(600).decode("utf-8", "replace").strip()
            except Exception:
                detail = ""
            if detail:
                exc.msg = f"{exc.msg} | {detail}"
            raise
        return data["message"]["content"].strip()
