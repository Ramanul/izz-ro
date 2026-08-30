#!/usr/bin/env python3
"""Rezumatul zilnic de revizuire: ce e nou si ce e riscant, nu ce s-a publicat.

DE CE EXISTA (K12, `IZZ-0255`). `REVIEW.md` descrie o rutina zilnica de ~15 minute:
deschizi site-ul, citesti titlurile de azi, corectezi in `moderation.yaml`. Masurat pe
2026-08-30: fisierul a fost atins de 4 ori in 71 de zile, niciodata ca moderare, iar
`blocklist_urls`, `corrections`, `featured` si `approved` sunt goale. Intrebat despre
rutina, proprietarul a raspuns „care rutina?".

Concluzia lui, nu a mea: nu textul se rescrie, se construieste MECANISMUL care aduce
revizuirea la el. De-aia scriptul asta nu listeaza ce s-a publicat — masurat, 529 de
articole si 44 de sinteze C pe zi, deci o lista ar esua exact ca rutina. Listeaza doar
EXCEPTIILE, cu URL-ul gata de lipit in `moderation.yaml`.

**Proprietatea care il tine viu: o zi normala incape in trei randuri.** Daca rezumatul
creste la fiecare rulare, nu mai e citit, si atunci n-am rezolvat nimic — am mutat
esecul in alt fisier.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

RADACINA = Path(__file__).resolve().parents[1]
PRAG_VOLUM = 3.0    # de cate ori peste mediana proprie a sursei devine „neobisnuit"
MIN_ISTORIC = 3     # sub atatea zile de istoric, mediana nu inseamna nimic


def ziua(articol: dict) -> str:
    return (articol.get("published") or "")[:10]


def surse_noi(articole: list[dict], zi: str) -> list[str]:
    """Surse care apar ASTAZI pentru prima oara. O sursa noua e risc editorial: nimeni
    nu i-a citit inca stilul, iar cele doua incidente de securitate au venit pe surse
    locale abia intrate (Rovinari, Cajvana)."""
    vazute_inainte = {a.get("source") for a in articole if ziua(a) < zi}
    de_azi = {a.get("source") for a in articole if ziua(a) == zi}
    return sorted(s for s in de_azi - vazute_inainte if s)


def volum_neobisnuit(articole: list[dict], zi: str, prag: float = PRAG_VOLUM) -> list[tuple[str, int, float]]:
    """(sursa, azi, mediana) pentru sursele care publica mult peste propriul obicei.

    Comparatia e cu MEDIANA SURSEI, nu cu un prag global: o sursa nationala face 30 de
    articole pe zi in mod normal, o primarie face 1. Un prag global ar semnala mereu
    aceleasi surse mari si niciodata anomalia reala.
    """
    pe_zi: dict[str, Counter] = defaultdict(Counter)
    for a in articole:
        if (z := ziua(a)) and a.get("source"):
            pe_zi[a["source"]][z] += 1
    gasite = []
    for sursa, zile in pe_zi.items():
        azi = zile.get(zi, 0)
        istoric = [n for z, n in zile.items() if z < zi]
        if azi and len(istoric) >= MIN_ISTORIC:
            med = statistics.median(istoric)
            if med and azi >= prag * med:
                gasite.append((sursa, azi, float(med)))
    return sorted(gasite, key=lambda t: -t[1])


def titluri_suspecte(articole: list[dict], zi: str) -> list[tuple[str, str, str]]:
    """(sursa, titlu, url) pentru itemele pe care garda de ingestie le-ar semnala.

    In mod normal e GOALA: garda respinge la ingestie. Un rand aici inseamna ca ceva a
    trecut, deci e exact clasa care merita ochi de om.
    """
    try:
        sys.path.insert(0, str(RADACINA))
        from generator import guard
    except ImportError:
        return []
    gasite = []
    for a in articole:
        if ziua(a) != zi:
            continue
        titlu = a.get("title") or ""
        motiv = guard.verdict(titlu) or guard.anomalie(titlu, a.get("source_lang") or "ro")
        if motiv:
            gasite.append((a.get("source") or "?", titlu, a.get("original_link") or ""))
    return gasite


def rezumat(articole: list[dict], zi: str) -> str:
    """Rezumatul, ca text. O zi fara exceptii incape in trei randuri — asta e scopul."""
    de_azi = [a for a in articole if ziua(a) == zi]
    c = sum(1 for a in de_azi if a.get("model") == "C")
    linii = [f"## Revizuire {zi}",
             "",
             f"**{len(de_azi)} articole**, din care **{c} sinteze C**, "
             f"de la **{len({a.get('source') for a in de_azi})} surse**."]

    if (suspecte := titluri_suspecte(articole, zi)):
        linii += ["", "### ⚠ Au trecut de garda — de verificat acum", ""]
        linii += [f"- `{s}` — {t}  \n  {u}" for s, t, u in suspecte[:10]]

    if (noi := surse_noi(articole, zi)):
        linii += ["", f"### Surse noi ({len(noi)})", "",
                  "Nimeni nu le-a citit inca stilul. Ambele incidente de securitate au venit "
                  "pe surse locale abia intrate.", "",
                  "  " + ", ".join(f"`{s}`" for s in noi[:15])]

    if (volum := volum_neobisnuit(articole, zi)):
        linii += ["", f"### Volum neobisnuit ({len(volum)})", ""]
        linii += [f"- `{s}`: **{n}** azi, mediana proprie {m:.0f}" for s, n, m in volum[:8]]

    if not (suspecte or noi or volum):
        linii += ["", "**Nimic de facut.** Nicio exceptie."]
    else:
        linii += ["", "---", "",
                  "Actiunea se face in `moderation.yaml` (`blocklist_urls`, `corrections`, "
                  "`suppress_sources`). Se aplica imediat cu **Actions -> build -> Run workflow**, "
                  "sau la urmatorul build automat, in pana la ~2h."]
    return "\n".join(linii)


def main(argv: list[str]) -> int:
    cale = RADACINA / "data" / "articles.json"
    date_ = json.loads(cale.read_text(encoding="utf-8"))
    articole = date_["articles"] if isinstance(date_, dict) and "articles" in date_ else date_
    # Argument gol = negiven: workflow-ul trimite `"$ZI"` citat, iar `inputs.zi` e gol la
    # rularile programate. Fara verificarea asta, ziua ar fi sirul vid si rezumatul ar iesi
    # mereu „0 articole" — un esec tacut, exact clasa pe care repo-ul o urmareste.
    dat = argv[1].strip() if len(argv) > 1 else ""
    zi = dat or str((datetime.now(timezone.utc) - timedelta(days=1)).date())
    print(rezumat(articole, zi))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
