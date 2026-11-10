"""Verifica accesul la catalogul Gemini, fara generare sau afisarea secretelor.

Ruleaza DOAR pe main prin workflow-ul dedicat. Nu dovedeste ca exista cota
pentru generare, ca proiectele sunt distincte sau ca un gateway este configurat.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

MODELS = ("gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


def check_key(key, opener=urllib.request.urlopen):
    """Returneaza status fix si modelele gasite; niciodata detalii sau chei."""
    if not key:
        return "missing", set()
    found = set()
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
                if name in MODELS and "generateContent" in model.get("supportedGenerationMethods", []):
                    found.add(name)
            token = data.get("nextPageToken") or ""
            if not token:
                return "ok", found
        return "incomplete", found
    except urllib.error.HTTPError as exc:
        return f"http_{exc.code}" if 100 <= exc.code <= 599 else "error", set()
    except Exception:
        return "error", set()


def main():
    enabled = os.getenv("GEMINI_EXTRA_KEYS_ENABLED", "true").strip().lower() == "true"
    print(f"::notice title=Configuratie fallback::Chei suplimentare {'permise' if enabled else 'dezactivate'}")
    for number in range(1, 5):
        name = "GEMINI_API_KEY" if number == 1 else f"GEMINI_API_KEY_{number}"
        tokens = [part for part in re.split(r"[,\s]+", os.getenv(name, "").strip()) if part]
        status, found = check_key(tokens[0] if tokens else "")
        models = ", ".join(f"{i}={'da' if model in found else 'nu'}" for i, model in enumerate(MODELS, 1))
        level = "notice" if status == "ok" else "warning"
        print(f"::{level} title=Gemini cheia {number}::catalog={status}; modele {models}")
    mapping = "; ".join(f"{i}={model}" for i, model in enumerate(MODELS, 1))
    print(f"::notice title=Interpretare::{mapping}; catalogul nu garanteaza cota sau generare")


if __name__ == "__main__":
    main()
