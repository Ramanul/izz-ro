#!/usr/bin/env python
"""Jurnal de munca si consum, o linie per slice verificat — plus raportul citibil.

  python tools/log_slice.py --account B --slice geo-categorii --approach solo \\
      --diff-lines 42 --tokens-k 18 --notes "3 categorii geo, 96/96 teste"
  python tools/log_slice.py --report          # regenereaza COORD-DASHBOARD.md din log

De ce exista: ca decizia „delegam sau facem singuri" sa se ia pe date, nu pe impresii.
Regula curenta (de revizuit cand avem >20 de randuri): delegam implementarea estimata la
peste ~5k tokeni; sub atat, overheadul de spec + review depaseste economia.

Fisierul `specs/metrics.csv` e CSV, append-only, scris de AMBELE conturi (coloana `account`).
Raportul e markdown fiindca GitHub il randeaza in browser si ambele conturi pot scrie in el —
artefactele claude.ai sunt per-cont si nu se pot partaja intre conturi (masurat 2026-07-24).
Stdlib only, fara retea, fara efecte in afara celor doua fisiere.
"""
import argparse
import csv
import os
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "specs", "metrics.csv")
REPORT = os.path.join(ROOT, "COORD-DASHBOARD.md")
COLUMNS = ["date", "account", "slice", "approach", "executor_branch",
           "diff_lines", "duration_min", "tokens_k", "notes"]
APPROACHES = ["solo", "devin", "oc", "jules", "agent", "ci"]


def _safe(text: str) -> str:
    """Escapare pentru aplicatii de calcul tabelar: o celula care incepe cu =, +, -, @
    sau cu tab/CR e interpretata drept formula la deschiderea CSV-ului. Prefixul ' o
    neutralizeaza vizual, fara sa afecteze parsarea CSV."""
    text = text or ""
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def append(args) -> int:
    row = {
        "date": date.today().isoformat(),
        "account": args.account,
        "slice": _safe(args.slice),
        "approach": args.approach,
        "executor_branch": _safe(args.executor_branch),
        "diff_lines": args.diff_lines,
        "duration_min": args.duration_min if args.duration_min is not None else "",
        "tokens_k": args.tokens_k if args.tokens_k is not None else "",
        "notes": _safe(args.notes),
    }
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    is_new = not os.path.isfile(LOG)
    with open(LOG, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        if is_new:
            w.writeheader()
        w.writerow(row)
    print(",".join(str(row[c]) for c in COLUMNS))
    return 0


def _rows() -> list:
    if not os.path.isfile(LOG):
        return []
    with open(LOG, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _num(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def report() -> int:
    rows = _rows()
    if not rows:
        print("Jurnal gol — nimic de raportat.")
        return 0

    by_acct = defaultdict(lambda: {"n": 0, "lines": 0, "tok": 0})
    by_appr = defaultdict(lambda: {"n": 0, "lines": 0, "tok": 0})
    for r in rows:
        for bucket, key in ((by_acct, r.get("account") or "?"),
                            (by_appr, r.get("approach") or "?")):
            b = bucket[key]
            b["n"] += 1
            b["lines"] += _num(r.get("diff_lines"))
            b["tok"] += _num(r.get("tokens_k"))

    tot_tok = sum(b["tok"] for b in by_acct.values())
    tot_lines = sum(b["lines"] for b in by_acct.values())

    out = []
    out.append("# Munca si consumul — jurnal comun A + B\n")
    out.append("> Generat din `specs/metrics.csv` cu `python tools/log_slice.py --report`.")
    out.append("> Ambele conturi scriu in el. Nu edita tabelele de mai jos manual — se suprascriu.")
    out.append("> **Cine lucreaza acum si ce e blocat** nu sta aici (s-ar invechi intre rulari), "
               "ci pe canalul live: [issue #83](https://github.com/Ramanul/izz-ro/issues/83) — "
               "intentia se anunta acolo INAINTE de a atinge fisiere.\n")
    out.append(f"**{len(rows)} slice-uri** · **{tot_lines} linii** de diff · "
               f"**~{tot_tok}k tokeni** raportati\n")

    out.append("## Pe cont\n")
    out.append("| cont | slice-uri | linii diff | ~tokeni (k) |")
    out.append("|---|---:|---:|---:|")
    for k in sorted(by_acct):
        b = by_acct[k]
        out.append(f"| {k} | {b['n']} | {b['lines']} | {b['tok']} |")

    out.append("\n## Pe mod de lucru\n")
    out.append("| mod | slice-uri | linii diff | ~tokeni (k) | tokeni / 100 linii |")
    out.append("|---|---:|---:|---:|---:|")
    for k in sorted(by_appr, key=lambda x: -by_appr[x]["n"]):
        b = by_appr[k]
        eff = f"{b['tok'] * 100 / b['lines']:.0f}" if b["lines"] else "—"
        out.append(f"| {k} | {b['n']} | {b['lines']} | {b['tok']} | {eff} |")

    out.append("\n## Slice-uri, cele mai recente primele\n")
    out.append("| data | cont | slice | mod | linii | ~tok | note |")
    out.append("|---|---|---|---|---:|---:|---|")
    for r in sorted(rows, key=lambda r: r.get("date", ""), reverse=True)[:40]:
        note = (r.get("notes") or "").replace("|", "\\|")[:70]
        out.append(f"| {r.get('date','')} | {r.get('account','')} | {r.get('slice','')} "
                   f"| {r.get('approach','')} | {r.get('diff_lines','')} "
                   f"| {r.get('tokens_k','')} | {note} |")

    out.append("\n---\n")
    out.append("## Ce costa efectiv\n")
    out.append("Contraintuitiv, si e important ca sa nu se optimizeze lucrul gresit "
               "(masurat de contul A prin API, 2026-07-24):\n")
    out.append("| resursa | cost | de ce |")
    out.append("|---|---|---|")
    out.append("| minute GitHub Actions | **zero** | repo public → minute gratuite si nelimitate; "
               "129 min intr-o zi = 0 lei |")
    out.append("| tururi de conversatie | **cota Claude a owner-ului** | resursa cu adevarat "
               "limitata; fiecare mesaj costa |")
    out.append("| rulari `pipeline` | **cota AI Gemini** | singurul workflow care consuma "
               "altceva decat minute |\n")
    out.append("**Regula care rezulta:** nu „rulati mai putine workflow-uri\", ci "
               "**muta in Actions tot ce e mecanic si taie din tururile de conversatie**. "
               "CI-ul e cel mai ieftin executor pe care il avem, nu cel mai scump — "
               "si e singurul care ajunge la internetul real.\n")
    out.append("**Cum se citeste `tokeni / 100 linii`:** cost aproximativ al modului de lucru. "
               "Numarul mic = ieftin pentru cat livreaza. Coloana e utila abia dupa ~20 de "
               "randuri; sub atat, variatia intre slice-uri o face inselatoare.\n")
    out.append("**Tokenii sunt estimati de cel care raporteaza**, nu masurati automat — "
               "sunt un ordin de marime, nu o factura.\n")

    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"Scris {REPORT} — {len(rows)} slice-uri, ~{tot_tok}k tokeni.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true", help="regenereaza COORD-DASHBOARD.md si iese")
    ap.add_argument("--account", choices=["A", "B", "owner"], help="cine a facut slice-ul")
    ap.add_argument("--slice", help="numele slice-ului (kebab-case)")
    ap.add_argument("--approach", choices=APPROACHES, help="cum a fost facut")
    ap.add_argument("--diff-lines", type=int, help="linii schimbate (git diff --stat)")
    ap.add_argument("--executor-branch", default="", help="branch-ul executorului, daca a fost unul")
    ap.add_argument("--duration-min", type=int, default=None)
    ap.add_argument("--tokens-k", type=int, default=None, help="tokeni estimati, in mii")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    if args.report:
        return report()
    missing = [f for f in ("account", "slice", "approach", "diff_lines")
               if getattr(args, f.replace("-", "_")) is None]
    if missing:
        ap.error("lipsesc: " + ", ".join("--" + m.replace("_", "-") for m in missing)
                 + "  (sau foloseste --report)")
    return append(args)


if __name__ == "__main__":
    raise SystemExit(main())
