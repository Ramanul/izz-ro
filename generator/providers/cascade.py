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
        self._caderi: dict = {}

    def available(self) -> bool:
        return any(p.available() for p in self._providers)

    def caderi_pe_provider(self) -> dict:
        """{nume_provider: cate apeluri i-au esuat} in rularea curenta.

        DE CE EXISTA (`IZZ-0282`, 2026-09-03): `_complete` de mai jos cheama `p._complete`,
        nu `p.complete`, deci OCOLESTE wrapper-ul din `base.py` care numara `calls` si
        `failures`. Cand Gemini cade la fiecare apel si Ollama salveaza fiecare articol,
        `provider.failures` ramane 0 si `ai_last_error` ramane None — corect pentru garda de
        cadere SISTEMICA din `main.py:82` (articolele chiar s-au procesat), dar orb pentru
        operare: providerul principal poate fi mort de zile fara nicio urma in `build.json`.

        Contorul nu schimba ce se publica. Face numarabil ce era invizibil — aceeasi forma
        cu contorul de pierderi la ingestie (`IZZ-0272`).
        """
        return dict(self._caderi)

    def _complete(self, system: str, user: str) -> str:
        last_exc = None
        for p in self._providers:
            if not p.available():
                continue
            try:
                return p._complete(system, user)
            except Exception as exc:
                self._caderi[p.name] = self._caderi.get(p.name, 0) + 1
                last_exc = exc
                continue
        raise last_exc or RuntimeError("niciun provider din cascada disponibil")
