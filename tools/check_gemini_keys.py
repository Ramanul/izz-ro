"""Verifica accesul la catalogul Gemini, fara generare sau afisarea secretelor.

Ruleaza DOAR pe main prin workflow-ul dedicat. Nu dovedeste ca exista cota
pentru generare, ca proiectele sunt distincte sau ca un gateway este configurat.

Pe langa lista fixa, cheia 1 listeaza modelele gemini-* NOI din catalog (doar nume si
limite) si face UN apel minimal de proba pe cele care se potrivesc cu
GEMINI_PROBE_PATTERN: un model poate aparea in catalog cu cota zero pe free tier.
"""
import time
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

MODELS = ("gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
PROBE_PATTERN = os.getenv("GEMINI_PROBE_PATTERN") or r"gemini-4|hydrogen"
PROBE_MAX = 3
NEW_MAX = 30


def check_key(key, opener=urllib.request.urlopen):
    """Returneaza status fix si modelele gasite; niciodata detalii sau chei."""
    status, catalog = list_catalog(key, opener)
    return status, {name for name in catalog if name in MODELS}


def list_catalog(key, opener=urllib.request.urlopen):
    """Status + {nume: model} pentru modelele cu generateContent."""
    if not key:
        return "missing", {}
    found = {}
    token = ""
    try:
        for _ in range(10):
            query = {"pageSize": 1000}
            if token:
                query["pageToken"] = token
            request = urllib.request.Request(
                ENDPOINT + "?" + urllib.parse.urlencode(query),
                headers={"x-goog-api-key": key},
            )
            with opener(request, timeout=20) as response:
                data = json.load(response)
            for model in data.get("models", []):
                name = model.get("name", "").removeprefix("models/")
                if "generateContent" in model.get("supportedGenerationMethods", []):
                    found[name] = model
            token = data.get("nextPageToken") or ""
            if not token:
                return "ok", found
        return "incomplete", found
    except urllib.error.HTTPError as exc:
        return f"http_{exc.code}" if 100 <= exc.code <= 599 else "error", {}
    except Exception:
        return "error", {}


def new_models(catalog):
    """Modelele gemini-* din catalog care nu sunt in lista fixa, sortate."""
    return sorted(n for n in catalog if n.startswith("gemini-") and n not in MODELS)


def probe(key, model, opener=urllib.request.urlopen):
    """Un apel minimal; intoarce doar campuri fixe (fara text, fara detalii de eroare)."""
    body = json.dumps({
        "contents": [{"parts": [{"text": 'Raspunde exact cu JSON-ul {"ok": true}'}]}],
        "generationConfig": {"maxOutputTokens": 1024, "responseMimeType": "application/json"},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{ENDPOINT}/{urllib.parse.quote(model)}:generateContent", data=body,
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
    )
    start = time.monotonic()
    try:
        with opener(request, timeout=60) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        return {"http": exc.code, "ms": int((time.monotonic() - start) * 1000)}
    except Exception as exc:
        return {"http": "error", "err": type(exc).__name__}
    candidate = (data.get("candidates") or [{}])[0]
    # Partile `thought` (rationament) nu fac parte din raspuns; tokenii lor intra in plafon.
    parts = (candidate.get("content") or {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    try:
        json_ok = json.loads(text) == {"ok": True}
    except ValueError:
        json_ok = False
    usage = data.get("usageMetadata") or {}
    return {
        "http": 200, "ms": int((time.monotonic() - start) * 1000),
        "finish": candidate.get("finishReason", "?"), "json_ok": json_ok,
        "thoughts": usage.get("thoughtsTokenCount", 0), "out": usage.get("candidatesTokenCount", 0),
    }


def main():
    enabled = os.getenv("GEMINI_EXTRA_KEYS_ENABLED", "true").strip().lower() == "true"
    print(f"::notice title=Configuratie fallback::Chei suplimentare {'permise' if enabled else 'dezactivate'}")
    for number in range(1, 5):
        name = "GEMINI_API_KEY" if number == 1 else f"GEMINI_API_KEY_{number}"
        tokens = [part for part in re.split(r"[,\s]+", os.getenv(name, "").strip()) if part]
        key = tokens[0] if tokens else ""
        status, found = check_key(key)
        if number == 1 and status == "ok":
            new_status, catalog = list_catalog(key)
            if new_status == "ok":
                report_new(key, catalog)
        models = ", ".join(f"{i}={'da' if model in found else 'nu'}" for i, model in enumerate(MODELS, 1))
        level = "notice" if status == "ok" else "warning"
        print(f"::{level} title=Gemini cheia {number}::catalog={status}; modele {models}")
    mapping = "; ".join(f"{i}={model}" for i, model in enumerate(MODELS, 1))
    print(f"::notice title=Interpretare::{mapping}; catalogul nu garanteaza cota sau generare")


def report_new(key, catalog, opener=urllib.request.urlopen):
    fresh = new_models(catalog)
    shown = ", ".join(
        f"{n}(in={catalog[n].get('inputTokenLimit', '?')},out={catalog[n].get('outputTokenLimit', '?')})"
        for n in fresh[:NEW_MAX]
    )
    more = f" +{len(fresh) - NEW_MAX}" if len(fresh) > NEW_MAX else ""
    print(f"::notice title=Modele noi in catalog (cheia 1)::{len(fresh)}: {shown or '-'}{more}")
    try:
        pattern = re.compile(PROBE_PATTERN, re.IGNORECASE)
    except re.error:
        print("::warning title=Proba generare::GEMINI_PROBE_PATTERN invalid; folosesc implicitul")
        pattern = re.compile(r"gemini-4|hydrogen", re.IGNORECASE)
    candidates = [n for n in fresh if pattern.search(n)][:PROBE_MAX]
    if not candidates:
        print(f"::notice title=Proba generare::niciun model nou potrivit cu /{PROBE_PATTERN}/")
    for model in candidates:
        result = probe(key, model, opener)
        fields = "; ".join(f"{k}={v}" for k, v in result.items())
        level = "notice" if result.get("http") == 200 else "warning"
        print(f"::{level} title=Proba {model}::{fields}")


if __name__ == "__main__":
    main()
