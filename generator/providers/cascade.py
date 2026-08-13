"""Inlantuire de provideri: incearca pe rand, trece la urmatorul doar la ESEC (nu la fiecare
apel). Scop: cand providerul principal (Gemini/Anthropic) da 429/quota epuizata sau cheia
lipseste, un articol care altfel ar fi AMANAT (regula 'No mangled output', vezi process.py)
poate totusi sa primeasca titlu/teaser real de la Qwen local (Ollama) — gratuit, doar mai
lent. Niciodata invers: Gemini/Anthropic raman intai in lista, Ollama e completarea, nu
inlocuirea — la fel de rapid si de calitativ cand cloud-ul merge, nimic nu se schimba.
"""
from .base import Provider


class CascadeProvider(Provider):
    def __init__(self, providers: list):
        self._providers = providers
        self.name = "+".join(p.name for p in providers)

    def available(self) -> bool:
        return any(p.available() for p in self._providers)

    def _complete(self, system: str, user: str) -> str:
        last_exc = None
        for p in self._providers:
            if not p.available():
                continue
            try:
                return p._complete(system, user)
            except Exception as exc:
                last_exc = exc
                continue
        raise last_exc or RuntimeError("niciun provider din cascada disponibil")
