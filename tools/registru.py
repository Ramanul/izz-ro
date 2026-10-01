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


def id_duplicate(rows: list[dict]) -> list[str]:
    """ID-urile revendicate de mai mult de un rand. Garda pura: intoarce incalcarile, nu ridica.

    DE CE (`IZZ-0241`, masurat 2026-08-21): `_next_id` calculeaza `max+1` pe vederea PROPRIE
    despre registru, deci doua sesiuni paralele pornite din acelasi `main` nimeresc aceeasi cifra.
    S-a intamplat de doua ori intr-o singura zi -- IZZ-0237 revendicat si de #204 si de #205,
    IZZ-0238 si de #204 si de #206 -- si nimic nu a semnalat-o, fiindca `registru.py` avea garda
    pe TITLU duplicat (`_cheie`) si niciuna pe ID.

    Alocarea nu poate fi facuta sigura INTRE ramuri fara un lacat partajat, pe care nu-l avem:
    fiecare ramura e consistenta cu ea insasi. Ce se poate face, si face garda asta, e ca
    ciocnirea sa nu ATERIZEZE tacut -- `tests.yml` ruleaza pe starea MERGED a fiecarui PR, deci
    a doua ramura iese rosie in loc sa suprascrie linistit evidenta primei.
    """
    vazute: dict[str, int] = {}
    for r in rows:
        vazute[r.get("id", "")] = vazute.get(r.get("id", ""), 0) + 1
    return [f"{i or '(gol)'} apare de {n} ori" for i, n in sorted(vazute.items()) if n > 1]


# Regula incepe AICI, nu retroactiv: registrul e append-only (§21) si o garda care ar cere
# rescrierea randurilor vechi ar incalca exact principiul pe care il apara. Randurile de
# dinainte raman cum sunt.
PRAG_FEREASTRA = 370


def masuratoare_fara_fereastra(rows: list[dict]) -> list[str]:
    """Randurile de zona `masuratoare` care nu spun CAND au fost masurate. Garda pura.

    DE CE (`IZZ-0367`, 2026-09-11). `IZZ-0362` a afirmat „traficul masurat e ~2.900/zi, marja
    de 34x" fara sa numeasca fereastra sau comanda. Randul vecin, `IZZ-0264`, numea run ID-ul
    si cele sapte zile. Diferenta nu e de stil: prima cifra nu poate fi nici verificata, nici
    infirmata, deci nu e o masuratoare -- e o impresie cu zecimale. Cand a fost recitita, nu
    s-a mai putut stabili daca includea sau nu ~1.400 de invocari de cron sterse intre timp,
    si a trebuit retrasa ca `masurat-fals`.

    Lectia a fost scrisa intai ca regula in `specs/STATE.md` -- adica proza, exact forma despre
    care aceeasi zi a demonstrat ca putrezeste. Asta e versiunea ei mecanica.

    CE NU VERIFICA, deliberat: daca metoda e numita, si daca fereastra e cea potrivita. Ambele
    cer judecata, iar o garda care are nevoie de judecata produce zgomot, nu semnal -- lectia
    proxy-ului „duplicare" din aceeasi zi, care marca 20+ mecanisme din 44 pentru ca imparteau
    un fisier. O data ISO in dovada e verificabila fara nicio interpretare, si e chiar bucata
    care lipsea la `IZZ-0362`.

    Randul propriu `IZZ-0365` ar pica regula asta -- spune „20+ semnale din 44" fara data. E
    lasat dinadins sub prag si numit aici, ca sa nu para ca pragul ascunde ceva.
    """
    incalcari = []
    for r in rows:
        if (r.get("zona") or "") != "masuratoare":
            continue
        if not (m := re.fullmatch(r"IZZ-(\d+)", r.get("id") or "")):
            continue
        if int(m.group(1)) < PRAG_FEREASTRA:
            continue
        if not re.search(r"\d{4}-\d{2}-\d{2}", r.get("dovada") or ""):
            incalcari.append(
                f"{r['id']} e de zona `masuratoare` dar dovada nu contine nicio data "
                "(AAAA-LL-ZZ): o cifra fara fereastra nu poate fi verificata"
            )
    return incalcari


def _write(rows: list[dict]) -> None:
    if dubluri := id_duplicate(rows):
        raise SystemExit("!! ID duplicat in registru, nu am scris nimic: " + "; ".join(dubluri)
                         + "\n   registrul e append-only (§20): renumeroteaza randul nou,"
                           " nu-l suprascrie pe cel existent.")
    if fara := masuratoare_fara_fereastra(rows):
        raise SystemExit("!! masuratoare fara fereastra, nu am scris nimic:\n   "
                         + "\n   ".join(fara)
                         + "\n   pune data (si, daca ai, comanda sau run ID-ul) in `dovada`.")
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(COLS) + "\n")
        for r in sorted(rows, key=lambda r: r["id"]):
            fh.write("\t".join((r.get(c) or "").replace("\t", " ") for c in COLS) + "\n")


def _numere(text: str) -> set[int]:
    return {int(m.group(1)) for m in re.finditer(r"^IZZ-(\d+)\t", text, re.M)}


def ids_din_toate_refurile() -> set[int]:
    """ID-urile din `specs/registru.tsv` asa cum arata pe FIECARE ref din repo.

    DE CE EXISTA (2026-09-14). `_next_id` citea doar working tree-ul, deci doua sesiuni
    paralele porniser de la acelasi main vedeau acelasi maxim si alocau AMANDOUA acelasi ID.
    Garda de duplicate (`id_duplicate`) verifica un SINGUR fisier, deci nu vedea nimic; iar la
    merge cele doua randuri sunt linii diferite, deci git le imbina curat si duplicatul
    ateriza pe main in tacere.

    Masurat, de trei ori acelasi defect:
      · IZZ-0327 — commit 76f0df0 (2026-09-09): „ID dublat IZZ-0327 sesiuni paralele".
      · IZZ-0321 — consemnat `masurat-fals`: „registru.py add aloca un ID liber" nu era
        adevarat, fiindca „liber" insemna „liber in working tree".
      · IZZ-0385 — 2026-09-14: pe main e constatarea despre clona shallow, in PR #344 e
        fereastra TTL. Doua decizii diferite, acelasi ID, ambele scrise de bunacredinta.
      · IZZ-0375 consemnase deja consecinta: un PR care renumeroteaza un ID intre timp
        mergeuit nu se mai poate rebaza curat.

    Deci nu e o scapare, e o proprietate a alocatorului. Se repara la ALOCARE, unde decizia
    se ia, nu la merge, unde e prea tarziu.

    Degradeaza curat: fara git, sau cu un ref fara fisierul asta, se intoarce ce s-a putut
    citi. Un ID sarit e ieftin; un ID dublat costa un rebase imposibil.
    """
    try:
        refs = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes"],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if refs.returncode != 0:
        return set()
    gasite: set[int] = set()
    for ref in refs.stdout.split():
        fisier = subprocess.run(
            ["git", "show", f"{ref}:specs/registru.tsv"],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=60,
        )
        if fisier.returncode == 0:
            gasite |= _numere(fisier.stdout)
    return gasite


def _next_id(rows: list[dict]) -> str:
    nums = {int(m.group(1)) for r in rows if (m := re.fullmatch(r"IZZ-(\d+)", r["id"]))}
    nums |= ids_din_toate_refurile()
    return f"IZZ-{max(nums, default=0) + 1:04d}"


def _titluri_pe_ref(text: str) -> dict[str, str]:
    return {
        linie.split("\t", 4)[0]: linie.split("\t", 4)[3]
        for linie in text.splitlines()
        if linie.startswith("IZZ-") and linie.count("\t") >= 4
    }


def coliziuni_intre_refuri(titluri_pe_ref: dict[str, dict[str, str]]) -> list[str]:
    """ID-uri carora doua refuri le dau TITLURI diferite — adica doua decizii, un singur ID.

    Alocatorul reparat opreste coliziunile VIITOARE, dar nu le vede pe cele deja scrise pe
    ramuri deschise. Iar merge-ul nu le vede nici el: randurile sunt linii diferite, deci git
    le imbina curat si duplicatul ateriza pe main in tacere — apoi §20 (append-only) interzice
    rescrierea lui, si singura iesire e un rebase care nu mai e curat (IZZ-0375).

    Detectia se face pe TITLU, nu pe randul intreg: acelasi rand editat (o dovada adaugata,
    o stare mutata din `propus` in `implementat`) e evolutie normala, nu coliziune.
    """
    vazute: dict[str, dict[str, str]] = {}
    for ref, titluri in titluri_pe_ref.items():
        for izz, titlu in titluri.items():
            vazute.setdefault(izz, {})[titlu] = ref
    return [
        f"{izz}: " + " vs ".join(f"{ref} „{t[:60]}…\"" for t, ref in sorted(v.items(), key=lambda x: x[1]))
        for izz, v in sorted(vazute.items()) if len(v) > 1
    ]


def titluri_din_toate_refurile() -> dict[str, dict[str, str]]:
    """`{ref: {IZZ-xxxx: titlu}}` pentru fiecare ref care are fisierul. Gol fara git."""
    try:
        refs = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes"],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if refs.returncode != 0:
        return {}
    out: dict[str, dict[str, str]] = {}
    for ref in refs.stdout.split():
        fisier = subprocess.run(
            ["git", "show", f"{ref}:specs/registru.tsv"],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=60,
        )
        if fisier.returncode == 0:
            out[ref] = _titluri_pe_ref(fisier.stdout)
    return out


def titluri_pe_refuri(refuri: tuple[str, ...]) -> dict[str, dict[str, str]]:
    """`{ref: {IZZ-xxxx: titlu}}` pentru refurile cerute care au fisierul."""
    out: dict[str, dict[str, str]] = {}
    for ref in refuri:
        fisier = subprocess.run(
            ["git", "show", f"{ref}:specs/registru.tsv"],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=60,
        )
        if fisier.returncode == 0:
            out[ref] = _titluri_pe_ref(fisier.stdout)
    return out


def coliziuni_cu_baza(baza: str = "origin/main") -> list[str]:
    """Coliziunile pe care ramura CURENTA le-ar ateriza pe `baza`.

    DE CE NU TOATE REFURILE. Scanarea completa gaseste 29 de coliziuni (masurat 2026-09-14),
    dar aproape toate sunt pe ramuri moarte — `wip/portare-codex`, `ramanul-triage-blockers`,
    sesiuni abandonate — care nu vor ateriza niciodata. O garda care e rosie permanent din
    cauza lor ar fi ignorata in doua zile, exact ca una care nu poate pica (IZZ-0177).

    Perechea HEAD vs baza e insa exact riscul real si e verificabila offline: daca acelasi ID
    poarta titluri diferite pe cele doua, merge-ul asta LIVREAZA duplicatul. Diagnosticul larg
    ramane disponibil cu `--toate`.
    """
    return coliziuni_intre_refuri(titluri_pe_refuri((baza, "HEAD")))


def cmd_coliziuni(args) -> int:
    if getattr(args, "toate", False):
        gasite = coliziuni_intre_refuri(titluri_din_toate_refurile())
        unde = "intre TOATE refurile (inclusiv ramuri moarte, care nu vor ateriza)"
    else:
        gasite = coliziuni_cu_baza(args.baza)
        unde = f"pe care ramura curenta le-ar ateriza pe {args.baza}"
    if not gasite:
        print(f">> nicio coliziune de ID {unde}")
        return 0
    print(f"!! ID-uri cu titluri DIFERITE, {unde}:")
    for linie in gasite:
        print("   " + linie)
    print("\n   Registrul e append-only (§20), deci dupa aterizare duplicatul nu se mai poate")
    print("   rescrie, iar renumerotarea rupe rebase-ul (IZZ-0375). Repara ACUM, pe ramura")
    print("   nemergeuita: `python tools/registru.py add` aloca peste toate refurile.")
    return 1


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

    c = sub.add_parser(
        "coliziuni", help="ID-uri cu titluri diferite pe refuri diferite (doua decizii, un ID)")
    c.add_argument("--baza", default="origin/main", help="ref de comparatie (implicit origin/main)")
    c.add_argument("--toate", action="store_true",
                   help="scaneaza toate refurile, inclusiv ramuri moarte (diagnostic)")
    c.set_defaults(fn=cmd_coliziuni)

    s = sub.add_parser("show", help="un rand intreg")
    s.add_argument("id")
    s.set_defaults(fn=cmd_show)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
