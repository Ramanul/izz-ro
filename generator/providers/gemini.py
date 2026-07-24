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

# `-latest` alias (nu o versiune fixata): modelele fixate sunt retrase periodic de
# Google (ex. gemini-2.5-flash-lite -> 404 "no longer available"), aliasul nu.
MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
# Baza URL a API-ului. Poti ruta prin Cloudflare AI Gateway (cache, retry,
# rate-limit, observabilitate) setand GEMINI_BASE_URL la URL-ul gateway-ului:
#   https://gateway.ai.cloudflare.com/v1/<account_id>/<gateway>/google-ai-studio
# Fara env -> direct la Google, comportament neschimbat. Calea si cheia raman la fel.
# `or` (nu doar default-ul getenv): in GitHub Actions ${{ vars.X }} nesetat da "",
# nu absenta -> tratam sirul gol tot ca "direct la Google".
BASE_URL = (os.getenv("GEMINI_BASE_URL") or "https://generativelanguage.googleapis.com").rstrip("/")
ENDPOINT = BASE_URL + "/v1beta/models/{model}:generateContent?key={key}"
THROTTLE = float(os.getenv("GEMINI_THROTTLE", "4.0"))   # pauza intre apeluri: ~15 req/min, sub plafonul RPM free-tier (2s tripa 429 la mijloc de rulare)
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
            # FARA thinkingConfig: gen. Gemini 3.x a inlocuit thinkingBudget si
            # raspunde 400 INVALID_ARGUMENT la el (alias -latest repointat pe
            # 3.5 Flash-Lite pe 2026-07-21 -> site inghetat 3 zile). Modelul nou
            # are "minimal thinking" implicit — echivalentul lui budget 0.
            "generationConfig": {
                "temperature": 0.2, "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
            },
        }).encode("utf-8")

    def _complete(self, system: str, user: str) -> str:
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
                    # corpul raspunsului contine motivul exact (ex. ce camp e refuzat
                    # la 400 INVALID_ARGUMENT) — fara el diagnosticul e ghicit
                    try:
                        detail = exc.read(600).decode("utf-8", "replace").strip()
                    except Exception:
                        detail = ""
                    if detail:
                        exc.msg = f"{exc.msg} | {detail}"
                    last_exc = exc
                    if exc.code in (429, 500, 503):
                        if attempt < RETRIES_PER_KEY - 1:
                            time.sleep(2 ** (attempt + 1))
                        break  # cheie limitata -> trece la urmatoarea
                    raise
            self._idx = (self._idx + 1) % len(self._keys)  # failover pe cheia urmatoare
        raise last_exc
