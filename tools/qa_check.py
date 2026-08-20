#!/usr/bin/env python
"""QA check — auditeaza setul PUBLICABIL (dupa quality_gate + dedup) si pica build-ul
daca scade calitatea. Ruleaza in GitHub Actions -> la exit!=0 owner-ul e anuntat automat.

  python tools/qa_check.py            # 0 = ok, 1 = probleme (peste prag)

Verifica: surse incoerente scapate de gate, categorii goale (=FAIL); plus rate de
fallback / duplicate (=warning). Pragurile sunt conservatoare ca sa nu inghete site-ul.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from generator import config                                   # noqa: E402
from generator.render import _quality_gate, _dedup, sources_coherent  # noqa: E402
from generator.util import title_tokens                        # noqa: E402
from tools.title_quality_audit import audit as audit_title_quality  # noqa: E402

STATE = os.path.join(ROOT, "data", "articles.json")
INCOHERENT_MAX = 0          # niciun C incoerent NU trebuie sa scape de gate
DUP_WARN_RATE = 0.08        # peste 8% duplicate -> doar avertisment


def _published() -> list:
    with open(STATE, encoding="utf-8") as fh:
        arts = _dedup(json.load(fh))
    return [a for a in arts if _quality_gate(a)]


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

    # duplicate de eveniment: titluri cu >=4 stem-uri comune
    stems = [({t[:6] for t in title_tokens(a.get("title", ""))}, a) for a in pub]
    dup = 0
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            if len(stems[i][0] & stems[j][0]) >= 4:
                dup += 1
                break

    print(f"=== QA izz.ro — {n} articole publicabile ({len(C)} C) ===")
    print(f"surse incoerente scapate de gate : {len(incoherent)}  (prag FAIL > {INCOHERENT_MAX})")
    print(f"categorii goale                  : {empty_cats or 'niciuna'}"
          + (f"  (in insamantare, doar warn: {empty_seed})" if empty_seed else ""))
    print(f"fallback (fara AI)               : {len(fallback)} ({len(fallback)/n*100:.0f}%)")
    print(f"posibile duplicate de eveniment  : {dup} ({dup/n*100:.0f}%)  (warn > {DUP_WARN_RATE*100:.0f}%)")
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
    if dup / n > DUP_WARN_RATE:
        print(f"!! AVERTISMENT: {dup/n*100:.0f}% duplicate (peste {DUP_WARN_RATE*100:.0f}%)")

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
