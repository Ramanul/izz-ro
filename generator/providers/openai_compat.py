"""Provider generic pentru endpointuri compatibile OpenAI Chat Completions.

Este optional si nu schimba fluxul implicit Gemini/Ollama. Se activeaza explicit prin
AI_ROUTER_MODE=multi si AI_FALLBACK_PROVIDERS, iar cheile raman in mediu/secrete.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import Provider


class OpenAICompatibleProvider(Provider):
    def __init__(self, name: str, key_env: str, base_url: str, model_env: str, default_model: str, timeout_env: str = "AI_PROVIDER_TIMEOUT"):
        self.name = name
        self.key_env = key_env
        self.base_url = (os.getenv(base_url, base_url) if base_url.startswith("http") else os.getenv(base_url, "")).rstrip("/")
        self.model = os.getenv(model_env, default_model)
        self.timeout = float(os.getenv(timeout_env, "45"))

    def available(self) -> bool:
        return bool(os.getenv(self.key_env, "").strip()) and bool(self.base_url) and bool(self.model)

    def _complete(self, system: str, user: str) -> str:
        key = os.getenv(self.key_env, "").strip()
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as exc:
            detail = exc.read(800).decode("utf-8", "replace")
            raise RuntimeError(f"{self.name} HTTP {exc.code}: {detail}") from exc
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, AttributeError, TypeError) as exc:
            raise RuntimeError(f"{self.name} returned an unexpected response shape") from exc


def configured_compatible_providers() -> list[Provider]:
    """Construieste numai providerii ale caror chei exista; ordinea este configurabila."""
    catalog = {
        "groq": ("GROQ_API_KEY", "GROQ_BASE_URL", "https://api.groq.com/openai/v1", "GROQ_MODEL", "openai/gpt-oss-20b"),
        "cerebras": ("CEREBRAS_API_KEY", "CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1", "CEREBRAS_MODEL", "gpt-oss-120b"),
        "mistral": ("MISTRAL_API_KEY", "MISTRAL_BASE_URL", "https://api.mistral.ai/v1", "MISTRAL_MODEL", "mistral-small-latest"),
        "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1", "OPENROUTER_MODEL", "openai/gpt-oss-20b:free"),
        "perplexity": ("PERPLEXITY_API_KEY", "PERPLEXITY_BASE_URL", "https://api.perplexity.ai", "PERPLEXITY_MODEL", "sonar"),
        "upstage": ("UPSTAGE_API_KEY", "UPSTAGE_BASE_URL", "https://api.upstage.ai/v1", "UPSTAGE_MODEL", "solar-pro"),
        # Scaleway modelează endpointul și modelul prin configurație; nu presupunem
        # un model implicit deoarece catalogul lor se poate schimba și trebuie opt-in.
        "scaleway": ("SCALEWAY_API_KEY", "SCALEWAY_BASE_URL", "", "SCALEWAY_MODEL", ""),
    }
    requested = [x.strip().lower() for x in os.getenv("AI_FALLBACK_PROVIDERS", "").split(",") if x.strip()]
    providers = []
    for name in requested:
        spec = catalog.get(name)
        if not spec:
            continue
        key_env, base_env, default_base, model_env, default_model = spec
        base = os.getenv(base_env, default_base)
        provider = OpenAICompatibleProvider(name, key_env, base, model_env, default_model)
        if provider.available():
            providers.append(provider)
    return providers
