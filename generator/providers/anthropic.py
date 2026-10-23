"""Provider Anthropic (comutabil pentru calitate mai buna). Cheia: ANTHROPIC_API_KEY."""
import os

from .base import Provider

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
# Același plafon ca Gemini (`gemini.py`): un lot dialectic de 3 clustere (E2) are ~1.500 de
# tokeni măsurați pe Gemini, iar 1024 l-ar fi trunchiat pe ORICE comutare la Anthropic —
# parserul tolerant ar fi salvat doar obiectele întregi, restul s-ar fi amânat tăcut.
MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self):
        self._client = None
        self._key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    def available(self) -> bool:
        if not self._key:
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    def _ensure(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._key)
        return self._client

    def _complete(self, system: str, user: str) -> str:
        client = self._ensure()
        msg = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in msg.content if block.type == "text").strip()
