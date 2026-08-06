#!/usr/bin/env python
"""Recenzor de PR pe cota GRATUITA Gemini (1500 cereri/zi), cu poarta de falsificabilitate.

  python tools/pr_review_gemini.py <numar_pr>

De ce exista, cand avem deja `claude-code-review.yml`: recenzorul Claude ruleaza pe cota
proprietarului si cade tacut cand ea se termina (masurat pe PR #88 -- 427ms, cost 0, zero
inferenta). `GEMINI_API_KEY` era deja secret in repo, folosit doar de pipeline, iar nivelul
gratuit Gemini e de 1500 de cereri pe zi -- practic neatins de cateva PR-uri pe saptamana.
Deci: al doilea recenzor, pe alt furnizor, care nu concureaza pe aceeasi cota.
Inlocuieste Gemini Code Assist (IZZ-0067), care tace pe PR-uri de la #136.

REGULA CARE FACE DIFERENTA fata de „inca un bot care comenteaza":
o constatare fara `fisier` + `linie` + reproducere este ARUNCATA, mecanic, inainte sa ajunga
la om. Un model care nu poate arata unde e problema nu a gasit o problema, a produs o parere --
iar o parere nefalsificabila costa mai mult decat tacerea, fiindca proprietarul nu o poate
arbitra. Cate au fost aruncate se TIPARESTE si intra in comentariu: fara taieri tacute.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE_URL = (os.getenv("GEMINI_BASE_URL") or "https://generativelanguage.googleapis.com").rstrip("/")
ENDPOINT = BASE_URL + "/v1beta/models/{model}:generateContent?key={key}"

# Aliasul, nu versiunea fixa: numele cu numar de versiune expira la Google si dau 404
# "no longer available" -- capcana documentata deja in generator/providers/gemini.py:16.
# Lista e o cascada: primul care nu da 404 castiga. Al doilea e cel dovedit ca merge azi
# (il foloseste pipeline-ul), deci scriptul nu poate ramane fara model.
MODELS = [os.getenv("GEMINI_REVIEW_MODEL") or "gemini-flash-latest", "gemini-flash-lite-latest"]

# NU e o masuratoare -- e o margine derivata din cota gratuita: nivelul gratuit da 250k
# tokeni/minut, iar 120k caractere de diff inseamna ~30-40k tokeni, deci o singura cerere
# incape cu mult loc. Feliile din acest repo sunt mici prin regula (CLAUDE.md sectiunea 5.3),
# deci pragul n-ar trebui atins; cand e atins, comentariul o SPUNE.
MAX_DIFF = 120_000

PROMPT = """Esti recenzor de cod pe un generator static de stiri scris in Python.

Raspunde EXCLUSIV cu JSON valid, fara markdown, fara ```:
{"findings": [{"file": "cale/relativa.py", "line": 42, "severity": "error|warning",
"claim": "ce e gresit, o propozitie", "repro": "intrarea concreta care sparge si ce iese gresit",
"fix": "propunerea de cod, scurta"}]}

Reguli stricte:
- `file` si `line` sunt OBLIGATORII si trebuie sa existe in diff. O constatare fara ele
  este aruncata automat, deci nu o scrie.
- `repro` trebuie sa fie o intrare/stare concreta, nu o ingrijorare generala. Daca nu poti
  numi una, nu e o constatare.
- Nu raporta stil, formatare sau preferinte. Doar: corectitudine, securitate, cazuri limita.
- Daca diff-ul e corect, raspunde {"findings": []}. Zero constatari e un raspuns bun.

Diff-ul:
"""


def _sh(args: list) -> str:
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=True).stdout


def _obiect(raw: str) -> dict:
    """Gemini 3.x returneaza uneori obiectul INVELIT INTR-O LISTA -- IZZ-0076, acelasi
    tipar ca in generator/process.py:86-88. Fara asta, `.get` ar arunca AttributeError."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(data, list):
        data = next((x for x in data if isinstance(x, dict)), None)
    return data if isinstance(data, dict) else {}


def filtreaza(findings, atinse: set) -> tuple[list, list]:
    """Poarta de falsificabilitate: (pastrate, aruncate). O constatare trece DOAR daca are
    fisier atins de PR + linie intreaga + reproducere nevida. Restul pleaca, cu motiv."""
    pastrate, aruncate = [], []
    for f in findings:
        if not isinstance(f, dict):
            aruncate.append((str(f)[:60], "constatare care nu e obiect"))
            continue
        fisier, linie = f.get("file"), f.get("line")
        if not fisier or not isinstance(linie, int) or isinstance(linie, bool):
            aruncate.append((f.get("claim", "?"), "fara fisier:linie"))
        elif fisier not in atinse:
            aruncate.append((f.get("claim", "?"), f"fisier neatins de PR ({fisier})"))
        elif not str(f.get("repro") or "").strip():
            aruncate.append((f.get("claim", "?"), "fara reproducere"))
        else:
            pastrate.append(f)
    return pastrate, aruncate


# Coduri pe care API-ul insusi le declara temporare. 503 spune literal "Spikes in demand
# are usually temporary. Please try again later." -- masurat pe prima rulare live (PR #150),
# unde o versiune fara reincercare a tratat 503 ca fatal si a iesit in 10 secunde.
TRANZITORII = {429, 500, 502, 503, 504}
# Pauzele cresc; prima e >= 4s fiindca throttle-ul de 4s al pipeline-ului a fost cauza-radacina
# masurata a limitarilor de RPM pe acelasi cont (IZZ-0004).
PAUZE = [4, 12, 30]


def _ask(key: str, prompt: str) -> str | None:
    """Cascada peste MODELS, cu reincercare pe erorile pe care API-ul le declara temporare.
    404 = model retras -> urmatorul model, fara reincercare (nu se repara asteptand).
    Intoarce None daca nimic n-a mers -- apelantul TREBUIE sa faca esecul vizibil, nu sa
    iasa tacut: un check verde fara recenzie e mai rau decat un check rosu.
    Corpul erorii se tipareste mereu (IZZ-0074: un provider care il ascunde face
    diagnosticul imposibil)."""
    global ULTIMA_EROARE
    for model in MODELS:
        for incercare, pauza in enumerate([0] + PAUZE):
            if pauza:
                print(f">> astept {pauza}s si reincerc ({model}, incercarea {incercare + 1})")
                time.sleep(pauza)
            body = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                # Fara `thinkingConfig`: respins de modelele Gemini 3.x (IZZ-0075).
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
            }).encode("utf-8")
            req = urllib.request.Request(ENDPOINT.format(model=model, key=key), data=body,
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.load(r)
                print(f">> model folosit: {model}")
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:200].replace("\n", " ")
                ULTIMA_EROARE = f"{model} -> HTTP {e.code}: {detail}"
                print(f">> {ULTIMA_EROARE}")
                if e.code not in TRANZITORII:
                    break  # 400/403/404 nu se repara asteptand -> modelul urmator
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                ULTIMA_EROARE = f"{model} -> {type(e).__name__}: {e}"
                print(f">> {ULTIMA_EROARE}")
    return None


ULTIMA_EROARE = "necunoscuta"


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("Utilizare: pr_review_gemini.py <numar_pr>")
    pr = sys.argv[1]
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY lipseste - sar peste review.")
        return 0

    diff = _sh(["gh", "pr", "diff", pr])
    if not diff.strip():
        print("Diff gol - nimic de revizuit.")
        return 0
    trunchiat = len(diff) > MAX_DIFF
    if trunchiat:
        diff = diff[:MAX_DIFF]

    # Fisierele atinse de PR: ancora fata de care validam constatarile.
    atinse = {ln[6:] for ln in diff.splitlines() if ln.startswith("+++ b/")}

    raw = _ask(key, PROMPT + diff)
    if raw is None:
        # Esecul se face VIZIBIL, nu tacut. Pasul e `continue-on-error` in workflow, deci
        # jobul ramane verde -- iar un check verde care nu inseamna "revizuit" e fix modul
        # de esec pe care recenzorul asta trebuia sa-l elimine, nu sa-l adauge.
        subprocess.run(["gh", "pr", "comment", pr, "--body",
                        "## Recenzie Gemini — **NU a rulat**\n\n"
                        f"Toate modelele au esuat dupa reincercari. Ultima eroare:\n\n"
                        f"```\n{ULTIMA_EROARE}\n```\n\n"
                        "_Check-ul apare verde fiindca pasul e non-blocant; "
                        "acest comentariu exista ca absenta recenziei sa nu treaca drept recenzie._"],
                       check=False)
        print("Recenzia nu a rulat; comentariu de esec publicat.")
        return 0
    obiect = _obiect(raw)
    if not obiect:
        print("Raspuns non-JSON de la model; nimic de publicat.")
        print(raw[:500])
        return 0
    findings = obiect.get("findings") or []
    if not isinstance(findings, list):
        print(f"`findings` nu e lista ({type(findings).__name__}); nimic de publicat.")
        return 0

    pastrate, aruncate = filtreaza(findings, atinse)

    print(f"Constatari: {len(findings)} | pastrate: {len(pastrate)} | aruncate: {len(aruncate)}")
    for claim, motiv in aruncate:
        print(f"  ARUNCATA ({motiv}): {str(claim)[:90]}")

    linii = ["## Recenzie Gemini (cota gratuita)", ""]
    if pastrate:
        for f in sorted(pastrate, key=lambda x: (x.get("severity") != "error", x["file"])):
            sev = "**ERROR**" if f.get("severity") == "error" else "warning"
            linii += [f"### {sev} · `{f['file']}:{f['line']}`",
                      str(f.get("claim", "")).strip(), "",
                      f"**Reproducere:** {str(f.get('repro', '')).strip()}", ""]
            if f.get("fix"):
                linii += ["```python", str(f["fix"]).strip(), "```", ""]
    else:
        linii += ["Nicio constatare care sa treaca poarta.", ""]

    linii += ["---",
              f"_{len(findings)} constatari brute · {len(pastrate)} publicate · "
              f"{len(aruncate)} aruncate (fara `fisier:linie` sau fara reproducere)._"]
    if trunchiat:
        linii.append(f"_Diff trunchiat la {MAX_DIFF} caractere - PR-ul e mai mare._")

    subprocess.run(["gh", "pr", "comment", pr, "--body", "\n".join(linii)], check=True)
    print("Comentariu publicat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
