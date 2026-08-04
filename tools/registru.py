#!/usr/bin/env python3
"""Registrul de deciziil: evidenta stricta a tot ce s-a propus, facut, respins sau anulat.

Spec: `specs/registru-decizii.md`. Problema pe care o rezolva: ca sa afli daca ceva a fost
propus/implementat/respins nu mai reincarci istoricul discutiilor, ci faci un `find` care intoarce
cateva linii. Costul de INTEROGARE e ce conteaza aici, nu cel de scriere.

    python tools/registru.py sync                    # regenereaza randurile derivate din PR-uri
    python tools/registru.py find fetch challenge    # cauta pe cuvinte (SI logic)
    python tools/registru.py find --stare respins    # filtreaza pe stare sau zona
    python tools/registru.py show IZZ-0042
    python tools/registru.py add --zona fetch --titlu "..." --stare respins \\
        --decident proprietar --motiv "..." [--dovada "#131"] [--leaga IZZ-0007]

Fisierul e `specs/registru.tsv`, append-only si versionat: ce s-a respins acum o luna trebuie sa
ramana citibil, cu motivul. TSV, nu CSV, fiindca motivele contin virgule tot timpul si nu vreau
ghilimele peste tot; tab-ul nu apare in textul scris de om.
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "specs", "registru.tsv")
COLS = ["id", "data", "zona", "titlu", "stare", "decident", "dovada", "motiv", "leaga"]

# Starile in care `motiv` e obligatoriu: fara el randul nu previne re-litigarea, adica nu isi face
# treaba. `sync` nu poate inventa motive, deci le semnaleaza in loc sa le fabrice.
NEEDS_MOTIV = {"respins", "abandonat", "anulat", "masurat-fals"}
STARI = {"propus", "acceptat", "implementat", "respins", "abandonat", "anulat",
         "blocat", "masurat-fals", "inchis-de-proprietar"}

# Scope-ul din titlul conventional-commit e cea mai buna aproximare a zonei pe care o avem gratis.
# Sinonimele se normalizeaza ca `find --zona fetch` sa nu rateze jumatate din randuri.
ZONA_ALIAS = {
    "quality": "render", "select": "render", "templates": "ui", "css": "ui", "design": "ui",
    "sources": "surse", "source": "surse", "feeds": "surse", "feed": "surse",
    "lint": "ci", "tests": "ci", "test": "ci", "workflow": "ci", "actions": "ci",
    "state": "proces", "docs": "proces", "spec": "proces", "process": "proces",
    "seo": "seo", "sitemap": "seo", "geo": "geo", "cluster": "cluster", "fetch": "fetch",
    "ai": "ai", "budget": "cost", "audit": "ci", "legal": "legal",
}


def _read() -> list[dict]:
    if not os.path.exists(PATH):
        return []
    with open(PATH, encoding="utf-8") as fh:
        lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
    if not lines:
        return []
    head = lines[0].split("\t")
    out = []
    for ln in lines[1:]:
        parts = ln.split("\t")
        parts += [""] * (len(head) - len(parts))
        out.append(dict(zip(head, parts)))
    return out


def _write(rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(COLS) + "\n")
        for r in sorted(rows, key=lambda r: r["id"]):
            fh.write("\t".join((r.get(c) or "").replace("\t", " ") for c in COLS) + "\n")


def _next_id(rows: list[dict]) -> str:
    nums = [int(m.group(1)) for r in rows if (m := re.fullmatch(r"IZZ-(\d+)", r["id"]))]
    return f"IZZ-{max(nums, default=0) + 1:04d}"


def _zona_din_titlu(titlu: str) -> str:
    m = re.match(r"\s*(\w+)\(([^)]+)\)", titlu)
    raw = (m.group(2) if m else (m.group(1) if (m := re.match(r"\s*(\w+):", titlu)) else "")).lower()
    return ZONA_ALIAS.get(raw, raw or "necunoscut")


def cmd_sync(_args) -> int:
    """Randurile derivate din PR-uri se GENEREAZA, nu se scriu de mana: zero tokeni de model.

    Idempotent si conservator: un PR deja prezent (dupa `#N` in `dovada`) nu se rescrie, ca sa nu
    stearga un `motiv` adaugat de om peste randul generat.
    """
    rows = _read()
    cunoscute = {m.group(0) for r in rows for m in [re.search(r"#\d+", r.get("dovada") or "")] if m}
    try:
        raw = subprocess.run(
            ["gh", "pr", "list", "--state", "all", "--limit", "500", "--json",
             "number,title,state,mergedAt,closedAt,createdAt,mergeCommit,author"],
            capture_output=True, text=True, check=True, cwd=ROOT).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"!! `gh` a esuat: {exc}", file=sys.stderr)
        return 1

    noi, fara_motiv = 0, []
    # Cronologic crescator, ca IZZ-0001 sa fie primul PR din proiect: id-urile devin monotone in
    # timp, deci un id mai mare inseamna mereu „mai recent" fara sa te uiti la coloana `data`.
    for pr in sorted(json.loads(raw), key=lambda p: p["number"]):
        eticheta = f"#{pr['number']}"
        if eticheta in cunoscute:
            continue
        if pr.get("mergedAt"):
            stare, data = "implementat", pr["mergedAt"][:10]
        elif pr.get("closedAt"):
            stare, data = "respins", pr["closedAt"][:10]
        else:
            stare, data = "propus", pr["createdAt"][:10]
        sha = ((pr.get("mergeCommit") or {}).get("oid") or "")[:8]
        rand = {
            "id": _next_id(rows), "data": data, "zona": _zona_din_titlu(pr["title"]),
            "titlu": pr["title"], "stare": stare,
            "decident": (pr.get("author") or {}).get("login", "?"),
            "dovada": eticheta + (f" {sha}" if sha else ""), "motiv": "", "leaga": "",
        }
        rows.append(rand)
        noi += 1
        if stare in NEEDS_MOTIV:
            fara_motiv.append(f"{rand['id']} {eticheta} {pr['title'][:60]}")

    _write(rows)
    print(f">> {noi} randuri noi din PR-uri; {len(rows)} in total")
    if fara_motiv:
        # Nu inventez motive. Un rand `respins` fara motiv e o gaura cunoscuta, nu o minciuna.
        print(">> randuri care CER un motiv scris de om (`registru.py add` nu le poate ghici):")
        for ln in fara_motiv:
            print("   " + ln)
    return 0


def cmd_add(args) -> int:
    if args.stare not in STARI:
        print(f"!! stare necunoscuta: {args.stare}\n   permise: {' '.join(sorted(STARI))}",
              file=sys.stderr)
        return 2
    if args.stare in NEEDS_MOTIV and not args.motiv:
        print(f"!! `{args.stare}` cere --motiv: randul fara motiv nu previne re-litigarea",
              file=sys.stderr)
        return 2
    rows = _read()
    rand = {"id": _next_id(rows), "data": args.data, "zona": args.zona, "titlu": args.titlu,
            "stare": args.stare, "decident": args.decident, "dovada": args.dovada or "",
            "motiv": args.motiv or "", "leaga": args.leaga or ""}
    rows.append(rand)
    _write(rows)
    print(f">> {rand['id']}  {rand['stare']}  {rand['titlu'][:70]}")
    return 0


def _cheie(titlu: str) -> str:
    """Titlul normalizat, pentru dedublare. Doi agenti care citesc jurnale diferite descriu acelasi
    lucru cu punctuatie si majuscule diferite; fara asta registrul se umple de duplicate."""
    return re.sub(r"[^a-z0-9]+", " ", titlu.lower()).strip()


def cmd_import(args) -> int:
    """Absoarbe linii TSV produse de agenti (backfill T2/T3), cu dedublare si validare.

    Formatul asteptat, FARA coloana `id` (o atribuie registrul):
        data	zona	titlu	stare	decident	dovada	motiv	leaga

    Randurile invalide se RESPING cu motivul afisat, nu se corecteaza tacut: un backfill care
    repara singur ce nu intelege produce exact genul de evidenta in care nu poti avea incredere.
    """
    rows = _read()
    vazute = {_cheie(r["titlu"]) for r in rows}
    with open(args.fisier, encoding="utf-8") as fh:
        linii = [ln.rstrip("\n") for ln in fh]

    adaugate = dubluri = respinse = 0
    for nr, ln in enumerate(linii, 1):
        if not ln.strip() or ln.strip().upper() == "NIMIC":
            continue
        p = ln.split("\t")
        if len(p) < 7:
            print(f"   respins linia {nr}: are {len(p)} coloane, trebuie 8"); respinse += 1
            continue
        p += [""] * (8 - len(p))
        data, zona, titlu, stare, decident, dovada, motiv, leaga = [x.strip() for x in p[:8]]
        if stare not in STARI:
            print(f"   respins linia {nr}: stare '{stare}'"); respinse += 1
            continue
        if stare in NEEDS_MOTIV and not motiv and not titlu.startswith("[FARA MOTIV IN SURSA]"):
            print(f"   respins linia {nr}: '{stare}' fara motiv"); respinse += 1
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data):
            print(f"   respins linia {nr}: data '{data}'"); respinse += 1
            continue
        if _cheie(titlu) in vazute:
            dubluri += 1
            continue
        rows.append({"id": _next_id(rows), "data": data, "zona": zona, "titlu": titlu,
                     "stare": stare, "decident": decident, "dovada": dovada,
                     "motiv": motiv, "leaga": leaga})
        vazute.add(_cheie(titlu))
        adaugate += 1

    _write(rows)
    print(f">> {adaugate} adaugate, {dubluri} dubluri sarite, {respinse} respinse; {len(rows)} in total")
    return 0


def _potrivit(r: dict, termeni: list[str], stare: str | None, zona: str | None) -> bool:
    if stare and r.get("stare") != stare:
        return False
    if zona and r.get("zona") != zona:
        return False
    hay = " ".join(r.get(c, "") for c in COLS).lower()
    return all(t.lower() in hay for t in termeni)


def cmd_find(args) -> int:
    rows = [r for r in _read() if _potrivit(r, args.termeni, args.stare, args.zona)]
    if not rows:
        print(">> nimic in registru pe filtrul asta. NU inseamna ca nu s-a incercat "
              "inainte de backfill — verifica pana unde a ajuns recuperarea (specs/registru-decizii.md).")
        return 0
    for r in rows:
        print(f"{r['id']}  {r['data']}  {r['stare']:<20} {r['zona']:<10} {r['titlu'][:70]}")
        if r.get("motiv"):
            print(f"          motiv: {r['motiv']}")
        if r.get("dovada"):
            print(f"          dovada: {r['dovada']}" + (f"  leaga: {r['leaga']}" if r.get("leaga") else ""))
    print(f">> {len(rows)} randuri")
    return 0


def cmd_show(args) -> int:
    for r in _read():
        if r["id"].lower() == args.id.lower():
            for c in COLS:
                if r.get(c):
                    print(f"{c:10s} {r[c]}")
            return 0
    print(f"!! {args.id} nu exista", file=sys.stderr)
    return 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sync", help="regenereaza randurile derivate din PR-uri").set_defaults(fn=cmd_sync)

    a = sub.add_parser("add", help="adauga o decizie care NU are PR")
    a.add_argument("--zona", required=True)
    a.add_argument("--titlu", required=True)
    a.add_argument("--stare", required=True)
    a.add_argument("--decident", default="claude")
    a.add_argument("--data", required=True, help="YYYY-MM-DD")
    a.add_argument("--dovada", default="")
    a.add_argument("--motiv", default="")
    a.add_argument("--leaga", default="")
    a.set_defaults(fn=cmd_add)

    i = sub.add_parser("import", help="absoarbe linii TSV de la agenti, cu dedublare si validare")
    i.add_argument("fisier")
    i.set_defaults(fn=cmd_import)

    f = sub.add_parser("find", help="cauta pe cuvinte (SI logic) si/sau filtre")
    f.add_argument("termeni", nargs="*")
    f.add_argument("--stare")
    f.add_argument("--zona")
    f.set_defaults(fn=cmd_find)

    s = sub.add_parser("show", help="un rand intreg")
    s.add_argument("id")
    s.set_defaults(fn=cmd_show)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
