"""Provider Gemini (implicit, gratuit). Cheia: GEMINI_API_KEY (din mediu, niciodata in cod)."""
import os

from .base import Provider

MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self):
        self._model = None
        self._key = os.getenv("GEMINI_API_KEY", "").strip()

    def available(self) -> bool:
        if not self._key:
            return False
        try:
            import google.generativeai as genai  # noqa: F401
            return True
        except ImportError:
            return False

    def _ensure(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self._key)
            self._model = genai.GenerativeModel(MODEL)
        return self._model

    def complete(self, system: str, user: str) -> str:
        model = self._ensure()
        resp = model.generate_content(f"{system}\n\n{user}")
        return (resp.text or "").strip()
