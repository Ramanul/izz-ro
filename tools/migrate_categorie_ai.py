#!/usr/bin/env python
"""Muta pe rubrica `ai` articolele deja publicate care sunt stiri de inteligenta artificiala.

  python tools/migrate_categorie_ai.py            # doar raporteaza (dry-run)
  python tools/migrate_categorie_ai.py --apply    # scrie articles.json + redirects

Rubrica `ai` a fost ceruta de owner pe 2026-08-21. Articolele deja procesate au categoria
INGHETATA in stare (`state.py`) si se recalculeaza doar la bump de PROMPT_VERSION, deci fara
migrarea asta rubrica ar porni goala si toate stirile de AI de pana acum ar ramane risipite
prin `tech`/`economic`/`extern`.

PERMALINKUL CONTINE CATEGORIA (`render.py`: `/{category}/{slug}/`), deci mutarea SCHIMBA URL-ul
fiecarui articol mutat. Fara 301, fiecare link deja indexat de Google sau distribuit pe retele
ar da 404 — exact problema rezolvata la redenumirea `zonal` -> `judetean`. Acolo a mers un
wildcard, fiindca toata categoria s-a mutat; aici articolele vin din categorii DIFERITE, deci
perechile vechi->nou se scriu una cate una in `data/redirects_migrare.tsv`, pe care
`render._write_redirects` il citeste la fiecare build.

Rubricile GEOGRAFICE (`config.PINNED_CATEGORIES`) sunt sarite deliberat: „LOCAL inseamna UNDE
se intampla, nu CINE publica" (regula owner 2026-08-02). O stire despre un startup de AI din
Timisoara ramane `local` — locul e subiectul, AI-ul e doar tema.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import config  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES = os.path.join(ROOT, "data", "articles.json")
REDIRECTS = os.path.join(ROOT, "data", "redirects_migrare.tsv")

# Termeni TARI: prezenta unuia singur e suficienta ca stirea sa fie despre AI.
# `Nvidia`, `robot`, `dronă autonomă` sunt DELIBERAT in afara listei — apar in stiri de
# hardware, de razboi si de bursa care nu sunt despre inteligenta artificiala. Masurat pe
# corpusul din 2026-08-21: regexul larg (cu Nvidia + drone) dadea 37 de potriviri, din care
# „Planul secret al Ucrainei de a ataca Moscova cu drone autonome" e o stire de razboi.
# DOUA regexuri, si separarea NU e cosmetica: acronimele se cauta CASE-SENSITIVE, restul nu.
# Masurat 2026-08-21: un singur regex cu `re.IGNORECASE` peste `\bA\.?I\.?\b` potrivea
# cuvantul romanesc „ai" si urca la 78 de articole, printre care „Sumudica critica pregatirea
# jucatorilor de la CFR Cluj" si „Ultrasii lui Dinamo s-au batut cu jandarmii" — zero AI in ele.
# Acronimul „AI" exista in romana ca verb; „inteligenta artificiala" nu.
ACRONIME = re.compile(r"\b(AI|A\.I\.|LLM|GPT-\d|LLM-uri|AGI)\b")
# Termeni TARI, insensibili la majuscule: prezenta unuia singur e suficienta.
# `Nvidia`, `robot`, `drona autonoma` sunt DELIBERAT in afara listei — apar in stiri de
# hardware, de razboi si de bursa care nu sunt despre inteligenta artificiala.
TERMENI = re.compile(
    r"(inteligen[\u021bt]ei? artificiale?|inteligen[\u021bt][\u0103a] artificial[\u0103a]|chatbot|"
    r"ChatGPT|OpenAI|Anthropic|DeepSeek|Copilot|Gemini|Mistral AI|"
    r"machine learning|deep learning|[\u00eei]nv[\u0103a][\u021bt]are automat[\u0103a]|model de limbaj)",
    re.IGNORECASE)


def _text(a: dict) -> str:
    """DOAR titlul — nu teaserul, nu sinteza.

    Diferenta e intre „stirea E despre AI" si „stirea POMENESTE AI", si e masurata, nu
    presupusa (2026-08-21, corpus de 5304 articole): cu teaser+sinteza ies 50 de potriviri,
    cu titlul singur 37. Cele 13 in plus sunt toate mentiuni in trecere — „Mercedes-Benz
    lanseaza faceliftul Clasei C" (teaserul zice ca asistentul de bord foloseste inteligenta
    artificiala), „Nestle vrea produse pentru utilizatorii de medicamente de slabit",
    „Google lanseaza Pixel 11". Niciuna nu e o stire de AI, si toate ar fi aterizat pe rubrica.
    Titlul e formulat de editor ca sa spuna SUBIECTUL; asta il face filtrul corect aici."""
    return " ".join(str(a.get(k) or "") for k in ("title", "display_title"))


def main() -> int:
    apply = "--apply" in sys.argv
    with open(ARTICLES, encoding="utf-8") as f:
        arts = json.load(f)
    lista = list(arts.values()) if isinstance(arts, dict) else arts

    pinned = getattr(config, "PINNED_CATEGORIES", set())
    mutate, perechi = [], []
    for a in lista:
        cat = a.get("category")
        if cat in pinned or cat == "ai" or not a.get("slug"):
            continue
        txt = _text(a)
        if not (TERMENI.search(txt) or ACRONIME.search(txt)):
            continue
        perechi.append((f"/{cat}/{a['slug']}/", f"/ai/{a['slug']}/"))
        mutate.append((cat, a.get("title") or ""))
        if apply:
            a["category"] = "ai"

    for cat, titlu in mutate:
        print(f"  [{cat:<9} -> ai] {titlu[:88]}")
    print(f"\n{len(mutate)} articole de mutat (din {len(lista)} publicate)")

    if not apply:
        print("\nDRY-RUN — nimic nu s-a scris. Ruleaza cu --apply.")
        return 0

    with open(ARTICLES, "w", encoding="utf-8") as f:
        # indent=2 = EXACT formatul scris de `state.py:208`. Cu orice alta valoare,
        # un fisier de 5300 de articole apare integral ca diff (129.000 de linii pentru
        # 37 de modificari) si review-ul devine imposibil.
        json.dump(arts, f, ensure_ascii=False, indent=2)
    vechi = set()
    if os.path.exists(REDIRECTS):
        with open(REDIRECTS, encoding="utf-8") as f:
            vechi = {ln.rstrip("\n") for ln in f if ln.strip()}
    linii = sorted(vechi | {f"{o}\t{n}" for o, n in perechi})
    with open(REDIRECTS, "w", encoding="utf-8") as f:
        f.write("\n".join(linii) + "\n")
    print(f"\nSCRIS: {ARTICLES}\nSCRIS: {REDIRECTS} ({len(linii)} redirecturi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
