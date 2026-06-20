"""Provider Anthropic (comutabil pentru calitate mai buna). Cheia: ANTHROPIC_API_KEY."""
import os

from .base import Provider

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


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

    def complete(self, system: str, user: str) -> str:
        client = self._ensure()
        msg = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in msg.content if block.type == "text").strip()
