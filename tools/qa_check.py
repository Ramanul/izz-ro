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
    C = [a for a in pub if a.get("model") == "C"]

    incoherent = [a for a in C if not sources_coherent(a)]
    fallback = [a for a in pub if a.get("processed_by") == "fallback"]

    # categorii goale (printre cele declarate)
    cats = {a.get("category") for a in pub}
    empty_cats = [c for c in config.CATEGORIES if c not in cats]

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
    print(f"categorii goale                  : {empty_cats or 'niciuna'}")
    print(f"fallback (fara AI)               : {len(fallback)} ({len(fallback)/n*100:.0f}%)")
    print(f"posibile duplicate de eveniment  : {dup} ({dup/n*100:.0f}%)  (warn > {DUP_WARN_RATE*100:.0f}%)")

    fail = []
    if len(incoherent) > INCOHERENT_MAX:
        fail.append(f"{len(incoherent)} clustere C cu surse incoerente au scapat de gate")
    if empty_cats:
        fail.append(f"categorii goale: {', '.join(empty_cats)}")
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
    sys.exit(main())
