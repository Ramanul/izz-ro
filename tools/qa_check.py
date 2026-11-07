#!/usr/bin/env python
"""QA check — auditeaza setul PUBLICABIL (dupa quality_gate + dedup) si pica build-ul
daca scade calitatea. Ruleaza in GitHub Actions -> la exit!=0 owner-ul e anuntat automat.

  python tools/qa_check.py            # 0 = ok, 1 = probleme (peste prag)

Verifica: surse incoerente scapate de gate, categorii goale (=FAIL); plus rate de
fallback / duplicate (=warning). Pragurile sunt conservatoare ca sa nu inghete site-ul.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from generator import config                                   # noqa: E402
from generator.cluster import _strict_match                    # noqa: E402
from generator.render import _quality_gate, _dedup, sources_coherent  # noqa: E402
from generator.select import anunt_oficial_fara_corp           # noqa: E402
from generator.util import title_tokens                        # noqa: E402
from tools.title_quality_audit import audit as audit_title_quality  # noqa: E402

STATE = os.path.join(ROOT, "data", "articles.json")
INCOHERENT_MAX = 0          # niciun C incoerent NU trebuie sa scape de gate

# DOUA masuratori diferite, o singura poarta. „Suprapunerea de subiect" (>=4 stem-uri de titlu
# comune) a fost singura linie pana pe 7 nov 2026 si raporta 17% — dar masura SUBIECTUL, nu
# dublura: pe 6591 publicabile, 1100 de articole impart ≥4 stem-uri cu alt articol, in timp ce
# 0 perechi au acelasi `url` si doar 40 (0,6%) sunt aceeasi sursa cu titlu identic in 7 zile.
# La un agregator, „Black Friday" sau „Cernavoda" revin legitim saptamani la rand; o poarta pe
# cifra aia ar fi cerut sub-unirea unor stiri care nu sunt aceeasi stire. Poarta sta pe
# republicare, singura clasa care e defect prin constructie (aceeasi sursa, acelasi titlu).
SUPRA_WARN_RATE = 0.08          # informativ, fara poarta — vezi nota de mai sus
REPUBLICARE_ZILE = 7            # fereastra in care o republicare e dublura, nu reluare lunara
REPUBLICARE_WARN_RATE = 0.02    # 0,6% masurat 7 nov 2026; 2% lasa loc de variatie intre runde

# Diacriticele: MASURI PROXY separate pentru titlu si corp. Garda exacta ruleaza pe itemele
# proaspete, unde textul sursei mai exista; dupa scrub, QA nu poate confirma pierderea fata de
# sursa. Corpul e proxy-ul de avertizare, titlul e raportat separat fiindca multe titluri corecte
# nu contin cuvinte care cer diacritice. Anunturile oficiale fara corp sunt excluse din proxy-ul
# corpului: placeholder-ul nu e o sinteza degradabila. Referinta din 2026-10-04 (13/747) folosea
# proxy-ul combinat vechi, deci nu e direct comparabila cu masuratorile separate de acum.
DIAC_WARN_RATE = 0.05
DIAC_FEREASTRA_ORE = 72


def _fara_diacritice(a: dict) -> bool:
    """True daca corpul publicabil nu are diacritice (proxy pentru text degradat)."""
    if anunt_oficial_fara_corp(a):
        return False
    diac = "ăâîșțĂÂÎȘȚ"
    corp = _corp(a)
    return bool(corp.strip()) and not any(ch in diac for ch in corp)


def _corp(a: dict) -> str:
    return (a.get("synthesis") if a.get("model") == "C" else a.get("teaser")) or ""


def _titlu_fara_diacritice(a: dict) -> bool:
    """Proxy raport-only: multe titluri corecte nu au nevoie de diacritice."""
    diac = "ăâîșțĂÂÎȘȚ"
    title = a.get("title") or ""
    return bool(title.strip()) and not any(ch in diac for ch in title)


def _published() -> list:
    with open(STATE, encoding="utf-8") as fh:
        arts = _dedup(json.load(fh))
    return [a for a in arts if _quality_gate(a)]


def _republicari(pub: list) -> list[tuple]:
    """Perechile (sursa, titlu identic) publicate la <= REPUBLICARE_ZILE zile distanta.

    Singura clasa de „dublura" care e defect prin constructie: nu subiect comun, ci exact
    aceeasi sursa cu exact acelasi titlu, in aceeasi fereastra. `url` identic e prins mai sus,
    in `render._dedup`; aici ramane ce trece de el (aceeasi sursa isi republica anuntul).
    """
    from datetime import datetime

    grupuri: dict[tuple[str, str], list] = {}
    for a in pub:
        cheie = ((a.get("source_name") or "").strip().lower(),
                 (a.get("title") or "").strip().lower())
        if not cheie[1]:
            continue
        grupuri.setdefault(cheie, []).append(a)
    perechi = []
    for grup in grupuri.values():
        if len(grup) < 2:
            continue
        grup.sort(key=lambda x: x.get("published") or "")
        for i in range(len(grup) - 1):
            try:
                delta = (datetime.fromisoformat(grup[i + 1]["published"])
                         - datetime.fromisoformat(grup[i]["published"]))
            except (ValueError, KeyError):
                continue
            if delta.days <= REPUBLICARE_ZILE:
                perechi.append((grup[i], grup[i + 1]))
    return perechi


_CUVANT_DIA = re.compile(r"[A-Za-zăâîșțĂÂÎȘȚşţŞŢ][A-Za-zăâîșțĂÂÎȘȚşţŞŢ-]*")


def _fara_diacritice_cuvant(w: str) -> str:
    import unicodedata

    cheie = unicodedata.normalize("NFD", w.lower())
    cheie = "".join(c for c in cheie if not unicodedata.combining(c))
    return cheie.replace("ş", "s").replace("ţ", "t")


def _lexicon_diacritice(arts: list) -> dict[str, set[str]]:
    """Formele cu diacritice vazute in corpus, cheie = forma fara diacritice.

    Proxy-ul vechi numara ORICE titlu fara diacritice — inclusiv titlurile corecte
    („Cancelarul german Friedrich Merz a vizitat Kievul"). Aici intrebarea e alta: exista in
    corpus un cuvant pe care il scrie CU diacritice si pe care titlul asta il scrie fara?
    Lexiconul se construieste din starea insasi, deci nu cere dictionar extern si nu poate
    diverge de limbajul publicatiei.

    Doar `ș`/`ț`/`î` (nu `ă`): acolo stau omografele care ar produce fals-pozitive —
    „la adresa" / „adresă", „prima" / „primă", „data" / „dată", „publica" / „publică" —
    iar un cuvant ca „apariție" nu are forma corecta fara diacritice. Consecinta: cifra e o
    limita INFERIOARA (prinde „presedintele", nu prinde „dupa").
    """
    lex: dict[str, set[str]] = {}
    for a in arts:
        texte = [a.get("title") or "", a.get("teaser") or ""]
        if isinstance(a.get("synthesis"), str):
            texte.append(a["synthesis"])
        for text in texte:
            for w in _CUVANT_DIA.findall(text):
                if not any(ch in "șțîȘȚÎ" for ch in w):
                    continue
                cheie = _fara_diacritice_cuvant(w)
                if len(cheie) >= 4:
                    lex.setdefault(cheie, set()).add(w.lower())
    return {k: v for k, v in lex.items() if len(v) == 1}


def _titluri_cu_pierderi(pub: list, arts: list | None = None) -> list[dict]:
    """Titlurile fara nicio diacritica in care >=2 cuvinte au in corpus o forma diacritizata."""
    if arts is None:
        with open(STATE, encoding="utf-8") as fh:
            arts = json.load(fh)
    lex = _lexicon_diacritice(arts)
    pierderi = []
    for a in pub:
        titlu = (a.get("title") or "").strip()
        if not titlu or any(ch in "ăâîșțĂÂÎȘȚ" for ch in titlu):
            continue
        gasite = []
        for poz, w in enumerate(_CUVANT_DIA.findall(titlu)):
            # Numele proprii raman neatinse: „Rosu" poate fi si „Roșu", si un nume de familie,
            # iar prima litera majuscula nu distinge, in romana, numele de inceputul frazei —
            # de aceea primul cuvant e exceptat (acolo majuscula e doar ortografie).
            if len(w) < 4 or (poz > 0 and w[0].isupper()):
                continue
            cheie = _fara_diacritice_cuvant(w)
            if cheie in lex:
                gasite.append(w.lower())
        if len(set(gasite)) >= 2:
            pierderi.append({"title": titlu, "cuvinte": sorted(set(gasite))})
    return pierderi


def main() -> int:
    pub = _published()
    n = len(pub)
    with open(STATE, encoding="utf-8") as fh:
        title_report = audit_title_quality(json.load(fh))
    C = [a for a in pub if a.get("model") == "C"]

    incoherent = [a for a in C if not sources_coherent(a)]
    fallback = [a for a in pub if a.get("processed_by") == "fallback"]

    # categorii goale (printre cele declarate); cele in insamantare doar avertizeaza
    cats = {a.get("category") for a in pub}
    seed = getattr(config, "SEED_CATEGORIES", set())
    empty_all = [c for c in config.CATEGORIES if c not in cats]
    empty_cats = [c for c in empty_all if c not in seed]
    empty_seed = [c for c in empty_all if c in seed]

    # suprapunere de subiect: titluri cu >=4 stem-uri comune (informativ — vezi SUPRA_WARN_RATE)
    stems = [({t[:6] for t in title_tokens(a.get("title", ""))}, a) for a in pub]
    supra = 0
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            if len(stems[i][0] & stems[j][0]) >= 4:
                supra += 1
                break

    # republicari: aceeasi sursa + titlu identic, in fereastra scurta — singura clasa care e
    # dublura prin constructie, deci singura care are poarta.
    rep = _republicari(pub)
    rep_arts = {a.get("slug") for p in rep for a in p}

    print(f"=== QA izz.ro — {n} articole publicabile ({len(C)} C) ===")
    print(f"surse incoerente scapate de gate : {len(incoherent)}  (prag FAIL > {INCOHERENT_MAX})")
    print(f"categorii goale                  : {empty_cats or 'niciuna'}"
          + (f"  (in insamantare, doar warn: {empty_seed})" if empty_seed else ""))
    print(f"fallback (fara AI)               : {len(fallback)} ({len(fallback)/n*100:.0f}%)")
    print(f"suprapunere de subiect (informativ): {supra} ({supra/n*100:.0f}%)"
          f"  (fara poarta; masoara subiectul, nu dublura)")
    print(f"republicari (sursa+titlu id., {REPUBLICARE_ZILE}z): {len(rep_arts)} "
          f"({len(rep_arts)/n*100:.1f}%)  (warn > {REPUBLICARE_WARN_RATE*100:.0f}%)")

    # Sinteze C strict-asemanatoare — sub-unirea story-urilor (IZZ-0419, REPORT-ONLY).
    # Doua sinteze C care trec pragul `_strict_match` (acelasi folosit la absorbirea
    # cross-run) ar trebui sa fie ACELASI story: cazul real ANAF din 1 oct — doua sinteze
    # la 8 minute distanta despre aceleasi controale (notes/story-intelligence/
    # audit-arhitectura.md §D). Metrica masoara dimensiunea problemei inainte de Etapa 5;
    # relaxarea clusteringului e zona protejata (§10 directiva) si nu se atinge aici.
    c_stems = [({t[:6] for t in title_tokens(a.get("title", ""))}, a) for a in C]
    perechi_story = []
    for i in range(len(c_stems)):
        for j in range(i + 1, len(c_stems)):
            inter = len(c_stems[i][0] & c_stems[j][0])
            union = len(c_stems[i][0] | c_stems[j][0])
            if _strict_match(inter, union):
                perechi_story.append((c_stems[i][1], c_stems[j][1]))
    # diacritice: doar pe fereastra recenta — reflecta ce produce providerul ACUM, nu media
    # istorica (care ar ascunde o regresie de prompt in masa). Vezi DIAC_WARN_RATE.
    from datetime import datetime, timedelta, timezone
    cut = (datetime.now(timezone.utc) - timedelta(hours=DIAC_FEREASTRA_ORE)).isoformat()
    recente = [a for a in pub if (a.get("published") or "") >= cut]
    titluri_cu_text = [a for a in recente if (a.get("title") or "").strip()]
    corpuri_cu_text = [a for a in recente
                       if not anunt_oficial_fara_corp(a) and _corp(a).strip()]
    fara = [a for a in corpuri_cu_text if _fara_diacritice(a)]
    titluri_fara = [a for a in titluri_cu_text if _titlu_fara_diacritice(a)]
    with open(STATE, encoding="utf-8") as fh:
        titluri_pierdute = _titluri_cu_pierderi(titluri_fara, json.load(fh))
    print(f"titluri recente fara diacritice  : {len(titluri_fara)}/{len(titluri_cu_text)}"
          f" ({len(titluri_fara)/max(len(titluri_cu_text),1)*100:.1f}%)"
          "  (limita superioara: include titluri corecte fara diacritice)")
    print(f"  din care cu pierderi probabile   : {len(titluri_pierdute)}"
          "  (lexicon din corpus, ș/ț/î; limita inferioara — vezi _lexicon_diacritice)")
    print(f"corpuri recente fara diacritice   : {len(fara)}/{len(corpuri_cu_text)}"
          f" ({len(fara)/max(len(corpuri_cu_text),1)*100:.1f}%)"
          + (f"  (warn > {DIAC_WARN_RATE*100:.0f}%)" if fara else ""))

    print(f"sinteze C strict-asemanatoare    : {len(perechi_story)} perechi "
          "(report-only, sub-unire story — IZZ-0419)")
    for x, y in perechi_story[:5]:
        print(f"    · {x.get('published', '')[:16]} / {y.get('published', '')[:16]}  "
              f"{x.get('title', '')[:60]}")
    print(
        "titluri oficiale >110 la afișare : "
        f"{title_report['display_titles_over_limit']}  (prag FAIL > 0)"
    )
    print(f"titluri oficiale afișate goale   : {title_report['empty_display_titles']}  (prag FAIL > 0)")

    fail = []
    if len(incoherent) > INCOHERENT_MAX:
        fail.append(f"{len(incoherent)} clustere C cu surse incoerente au scapat de gate")
    if empty_cats:
        fail.append(f"categorii goale: {', '.join(empty_cats)}")
    if title_report["contract"]["status"] != "pass":
        fail.append(
            "contractul titlurilor oficiale a eșuat: "
            f"{title_report['display_titles_over_limit']} peste limită, "
            f"{title_report['empty_display_titles']} goale"
        )
    if rep_arts and len(rep_arts) / n > REPUBLICARE_WARN_RATE:
        print(f"!! AVERTISMENT: {len(rep_arts)/n*100:.1f}% republicari "
              f"(peste {REPUBLICARE_WARN_RATE*100:.0f}%) — aceeasi sursa, titlu identic, "
              f"{REPUBLICARE_ZILE} zile")
    if supra / n > SUPRA_WARN_RATE:
        print(f"   nota: suprapunere de subiect {supra/n*100:.0f}% (informativ, fara poarta)")
    if corpuri_cu_text and len(fara) / len(corpuri_cu_text) > DIAC_WARN_RATE:
        print(f"!! AVERTISMENT: {len(fara)/len(corpuri_cu_text)*100:.0f}% corpuri recente fara diacritice "
              f"(peste {DIAC_WARN_RATE*100:.0f}%) — vezi linia «>> diacritice:» din logul de build "
              "pentru cate au fost semnalate si cate reparate")

    if fail:
        print("\nFAIL:")
        for f in fail:
            print("  -", f)
        return 1
    print("\nOK: calitatea publicabila trece pragurile.")
    return 0


if __name__ == "__main__":
    # Windows: cp1252 nu are „ș"/„ț", deci un `print` cu diacritice arunca
    # UnicodeEncodeError si scriptul iese cu 1 — indistingibil de un esec real de
    # continut. Masurat 2026-08-20: `qa_check.py` iesea cu 1 pe date valide, iar cu
    # PYTHONIOENCODING=utf-8 cu 0. In CI (Linux, UTF-8) nu se vede. Acelasi idiom ca
    # in `scan_homepages.py`, extins la toate punctele de intrare cu diacritice.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
