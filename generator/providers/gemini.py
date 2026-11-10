"""Provider Gemini prin REST (fara SDK/grpc).

GEMINI_API_KEY poate contine mai multe chei (separate prin virgula/spatiu).
Cheile suplimentare sunt opt-in; cotele sunt per proiect, nu per cheie.
"""
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request

from .base import Provider

# Modelele sunt încercate serial, în ordinea configurată. GEMINI_MODEL rămâne
# compatibil pentru configurațiile vechi cu un singur model.
DEFAULT_MODELS = (
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
)


def _models() -> list[str]:
    configured = (os.getenv("GEMINI_MODELS") or os.getenv("GEMINI_MODEL") or "").strip()
    if not configured:
        return list(DEFAULT_MODELS)
    result = []
    for model in re.split(r"[,\s]+", configured):
        if model and model not in result:
            result.append(model)
    return result or list(DEFAULT_MODELS)


MODELS = _models()
MODEL = MODELS[0]
# Plafonul de output. Trebuie sa creasca CU config.BATCH_SIZE: un lot model-B de 10 articole
# produce ~2000 de tokeni de JSON, iar un array trunchiat e pierdut TACUT de _parse_json_array
# (regex-ul nu gaseste `]` de inchidere -> []). 8192 lasa spatiu pentru loturi si model C.
MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS") or "8192")
# finishReason al fiecărui răspuns 200, pe rulare (main.py îl pune în jurnalul de triaj).
MOTIVE_OPRIRE: dict = {}
# Baza URL a API-ului. Poti ruta prin Cloudflare AI Gateway (cache, retry,
# rate-limit, observabilitate) setand GEMINI_BASE_URL la URL-ul gateway-ului:
#   https://gateway.ai.cloudflare.com/v1/<account_id>/<gateway>/google-ai-studio
# Fara env -> direct la Google, comportament neschimbat. Calea si cheia raman la fel.
# `or` (nu doar default-ul getenv): in GitHub Actions ${{ vars.X }} nesetat da "",
# nu absenta -> tratam sirul gol tot ca "direct la Google".
BASE_URL = (os.getenv("GEMINI_BASE_URL") or "https://generativelanguage.googleapis.com").rstrip("/")
ENDPOINT = BASE_URL + "/v1beta/models/{model}:generateContent"
THROTTLE = float(os.getenv("GEMINI_THROTTLE", "4.0"))   # pauza intre apeluri: ~15 req/min, sub plafonul RPM free-tier (2s tripa 429 la mijloc de rulare)
RETRIES_PER_KEY = 2
REQUEST_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT") or "30")


def _keys() -> list:
    # Lista initiala ramane neschimbata, inclusiv cand contine deja mai multe chei.
    keys = [k for k in re.split(r"[,\s]+", os.getenv("GEMINI_API_KEY", "").strip()) if k]
    if os.getenv("GEMINI_EXTRA_KEYS_ENABLED", "").strip().lower() == "true":
        for name in ("GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4"):
            for key in re.split(r"[,\s]+", os.getenv(name, "").strip()):
                if key and key not in keys:
                    keys.append(key)
    return keys


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
                "temperature": 0.2, "maxOutputTokens": MAX_OUTPUT_TOKENS,
                "responseMimeType": "application/json",
            },
        }).encode("utf-8")

    def _complete(self, system: str, user: str) -> str:
        try:
            return self._complete_request(system, user)
        except Exception as exc:
            # Erorile upstream pot contine date sensibile, inclusiv in raspunsul HTTP.
            message = str(exc)
            for key in sorted(self._keys, key=len, reverse=True):
                message = message.replace(key, "[REDACTED]")
            raise RuntimeError(f"Gemini {type(exc).__name__}: {message}") from None

    def _complete_request(self, system: str, user: str) -> str:
        if not self._keys:
            raise RuntimeError("GEMINI_API_KEY lipsește.")
        if THROTTLE:
            time.sleep(THROTTLE)
        body = self._payload(system, user)
        last_exc = None
        # Încearcă modelele pe rând; fiecare cerere se încheie înaintea următoarei.
        for model in MODELS:
            model_rejected = False
            for _ in range(len(self._keys)):
                key = self._keys[self._idx]
                url = ENDPOINT.format(model=model)
                for attempt in range(RETRIES_PER_KEY):
                    try:
                        req = urllib.request.Request(
                            url, data=body, headers={"Content-Type": "application/json", "x-goog-api-key": key}
                        )
                        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                            data = json.load(resp)
                        # De ce s-a oprit modelul, numărat pe rulare: MAX_TOKENS taie coada unui
                        # lot, iar SAFETY/RECITATION pot întoarce 200 fără text.
                        motiv = ((data.get("candidates") or [{}])[0].get("finishReason")
                                 or "NECUNOSCUT")
                        MOTIVE_OPRIRE[motiv] = MOTIVE_OPRIRE.get(motiv, 0) + 1
                        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    except urllib.error.HTTPError as exc:
                        try:
                            detail = exc.read(600).decode("utf-8", "replace").strip()
                        except Exception:
                            detail = ""
                        if detail:
                            exc.msg = f"{exc.msg} | {detail}"
                        last_exc = exc
                        if exc.code in (429, 500, 502, 503, 504):
                            if attempt < RETRIES_PER_KEY - 1:
                                time.sleep(2 ** (attempt + 1))
                                continue
                            break  # limită/eroare temporară: încearcă următoarea cheie/model
                        if exc.code in (400, 404):
                            model_rejected = True
                            break  # model indisponibil sau incompatibil: încearcă următorul
                        raise
                    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                        last_exc = exc
                        break  # timeout/rețea: încearcă următoarea cheie/model
                self._idx = (self._idx + 1) % len(self._keys)
                if model_rejected:
                    break
        raise last_exc
