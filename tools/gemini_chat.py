#!/usr/bin/env python
"""Bot conversațional @gemini — răspunde pe issue/PR din cota GRATUITĂ Google AI Studio.

  python tools/gemini_chat.py <prompt.md> <raspuns.md>

Tiparul API e același cu tools/pr_review_gemini.py (cascada de aliasuri, reîncercări pe
coduri tranzitorii, fără `thinkingConfig` — respins de Gemini 3.x, IZZ-0075), dar output
e text liber, nu JSON: răspunsul merge ca comentariu GitHub, nu prin poarta de
falsificabilitate. Cheia e aceeași deja probată live de gemini-review.yml.
Contract: jurnalele -> stderr, `model=<slug>` -> stdout, răspunsul -> fișierul din argv[2].
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = (os.getenv("GEMINI_BASE_URL") or "https://generativelanguage.googleapis.com").rstrip("/")
ENDPOINT = BASE_URL + "/v1beta/models/{model}:generateContent?key={key}"

# Aliasuri, nu versiuni fixe — cele cu număr de versiune expiră la Google și dau 404
# "no longer available" (capcana documentată în pr_review_gemini.py și generator/providers/gemini.py).
MODELS = [os.getenv("GEMINI_CHAT_MODEL") or "gemini-flash-latest", "gemini-flash-lite-latest"]

# Coduri pe care API-ul însuși le declară temporare (aceeași listă probată în pr_review_gemini.py).
TRANZITORII = {429, 500, 502, 503, 504}
PAUZE = [4, 12, 30]


def _intreaba(key: str, prompt: str) -> tuple[str, str] | None:
    """(model, text) sau None. Corpul erorii se tipărește mereu (IZZ-0074)."""
    for model in MODELS:
        for incercare, pauza in enumerate([0] + PAUZE):
            if pauza:
                print(f">> aștept {pauza}s și reîncerc ({model})", file=sys.stderr)
                time.sleep(pauza)
            body = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0, "maxOutputTokens": 4096},
            }).encode("utf-8")
            req = urllib.request.Request(ENDPOINT.format(model=model, key=key), data=body,
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = json.load(r)
                candidat = (data.get("candidates") or [{}])[0]
                text = "".join(p.get("text", "") for p in (candidat.get("content") or {}).get("parts", []))
                if text.strip():
                    print(f">> model folosit: {model}", file=sys.stderr)
                    return model, text
                print(f">> {model}: răspuns gol (finishReason={candidat.get('finishReason')})",
                      file=sys.stderr)
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:200].replace("\n", " ")
                print(f">> {model} -> HTTP {e.code}: {detail}", file=sys.stderr)
                if e.code not in TRANZITORII:
                    break  # 400/403/404 nu se repară așteptând -> modelul următor
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                print(f">> {model} -> {type(e).__name__}: {e}", file=sys.stderr)
    return None


def main() -> int:
    if len(sys.argv) < 3:
        raise SystemExit("Utilizare: gemini_chat.py <prompt.md> <raspuns.md>")
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY lipsește.", file=sys.stderr)
        return 1
    prompt = open(sys.argv[1], encoding="utf-8").read()
    rezultat = _intreaba(key, prompt)
    if rezultat is None:
        print("Toate modelele Gemini au eșuat după reîncercări.", file=sys.stderr)
        return 1
    model, text = rezultat
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(text)
    print(model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
