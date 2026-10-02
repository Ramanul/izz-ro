#!/usr/bin/env python
"""Bot conversațional @ai — modele gratuite OpenRouter (`:free`), fără card.

  python tools/openrouter_chat.py <prompt.md> <raspuns.md>

Catalogul `:free` se schimbă zilnic (măsurat 2-3 oct 2026: modele care erau gratuite ieri
au dispărut azi), deci răspunsul NU promite un model anume: aliasul cerut se încearcă
primul, iar routerul `openrouter/free` + cascada acoperă orice zi. Modelul EFECTIV care a
răspuns e raportat în comentariu, ca să nu existe iluzia că altceva a răspuns.
Cota contului: 50 cereri/zi, ÎMPĂRȚITĂ cu claude CLI și OpenCode (același cont OpenRouter).
Contract: jurnalele -> stderr, `model=<slug>` -> stdout, răspunsul -> fișierul din argv[2].
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ENDPOINT = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/") + "/chat/completions"

# Doar modele dovedite gratuite la ultima verificare a catalogului (3 oct 2026).
# Inkling e EXCLUS: prin API brut dă mereu 403 "only available on agentic harnesses"
# (măsurat 2 și 3 oct — trece doar prin OpenCode/harness, nu direct).
CASCADA = [
    "openrouter/free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "qwen/qwen3.8-27b:free",
    "google/gemma-4-31b-it:free",
]
# deepseek/kimi/glm/grok NU sunt gratuite azi -> cererea cade pe cascada; comentariul
# numește modelul efectiv. Când revin în catalogul :free, se adaugă aici.
ALIAS = {
    "nemotron": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "qwen": "qwen/qwen3.8-27b:free",
    "gemma": "google/gemma-4-31b-it:free",
}

# 429 la modelele :free = congestionare, nu cont blocat (măsurat 2 oct: 2×429 pe qwen).
TRANZITORII = {429, 408, 500, 502, 503, 504}
PAUZE = [0, 5]

TRIGGER = re.compile(r"@(ai|deepseek|qwen|kimi|glm|grok|nemotron|gemma|inkling)\b")


def _alias_din_body(body: str) -> str:
    """Primul declanșator din text + eventual cuvântul de după el.
    '@ai qwen ce părere ai' -> 'qwen'; '@qwen singur' -> 'qwen'; '@ai (întrebare)' -> 'ai'."""
    m = TRIGGER.search(body or "")
    if not m:
        return ""
    rest = body[m.end():].lstrip()
    cuvant = re.split(r"[\s:,;.!?()]", rest, maxsplit=1)[0].lower() if rest else ""
    if cuvant and (cuvant in ALIAS or "/" in cuvant or TRIGGER.fullmatch("@" + cuvant)):
        return cuvant
    return m.group(1)


def _ordine(alias: str) -> list:
    if "/" in alias:  # slug complet dat de utilizator (ex. când revine deepseek/...:free)
        cap = [alias]
    else:
        cap = [ALIAS[alias]] if alias in ALIAS else []
    return cap + [m for m in CASCADA if m not in cap]


def _intreaba(key: str, prompt: str, ordine: list) -> tuple[str, str] | None:
    for model in ordine:
        for pauza in PAUZE:
            if pauza:
                print(f">> aștept {pauza}s și reîncerc ({model})", file=sys.stderr)
                time.sleep(pauza)
            body = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }).encode("utf-8")
            req = urllib.request.Request(ENDPOINT, data=body, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": "https://github.com/Ramanul/izz-ro",
                "X-Title": "izz-ro-ai-bot",
            })
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = json.load(r)
                text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                if text.strip():
                    folosit = data.get("model") or model
                    print(f">> model folosit: {folosit}", file=sys.stderr)
                    return folosit, text
                print(f">> {model}: răspuns gol", file=sys.stderr)
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:200].replace("\n", " ")
                print(f">> {model} -> HTTP {e.code}: {detail}", file=sys.stderr)
                if e.code not in TRANZITORII:
                    break  # model indisponent/404 -> următorul, nu așteptăm
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                print(f">> {model} -> {type(e).__name__}: {e}", file=sys.stderr)
    return None


def main() -> int:
    if len(sys.argv) < 3:
        raise SystemExit("Utilizare: openrouter_chat.py <prompt.md> <raspuns.md>")
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        print("OPENROUTER_API_KEY lipsește.", file=sys.stderr)
        return 1
    prompt = open(sys.argv[1], encoding="utf-8").read()
    ordine = _ordine(_alias_din_body(os.getenv("COMMENT_BODY", "")))
    rezultat = _intreaba(key, prompt, ordine)
    if rezultat is None:
        print("Toate modelele gratuite au eșuat sau sunt congestionate.", file=sys.stderr)
        return 1
    model, text = rezultat
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(text)
    print(f"model={model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
