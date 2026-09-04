#!/usr/bin/env python3
"""Ce exista in repo dar nu e folosit de nimic: cod fara apelant, documente fara referinta.

DE CE EXISTA: repo-ul creste prin adaugare — o felie lasa in urma un spec, un modul, o
functie. Nimic nu le sterge, fiindca nimic nu le NUMARA. Masurat 2026-09-02, prima rulare:
8 definitii din 292 fara apelant in productie si 23 de fisiere de documentatie catre care
nu trimite nimeni (272 KB). Dosarul: `specs/arhitectura-cuplare.md` sect. 4f.

RAPORT, NU POARTA. Iese mereu cu 0. Un spec scris INAINTE de implementare are legitim zero
referinte, iar o functie noua poate astepta apelantul. O poarta care pica pe asta ar pedepsi
exact ordinea corecta de lucru (spec intai — sect. 5.1).

    python tools/nefolosit.py cod         functii/clase din generator/ fara apelant
    python tools/nefolosit.py documente   .md-uri catre care nu trimite nimeni
    python tools/nefolosit.py reguli      sectiunile CLAUDE.md, dupa cost per citare

DIRECTIA ERORII, declarata: prefer sa RATEZ cod mort decat sa declar mort ceva viu. De-aia
o referinta din sabloanele Jinja2 sau din `tests/` conteaza ca semn de viata, si de-aia
utilizarile se citesc din AST, nu prin cautare in text — `merge` apare in zeci de comentarii
romanesti („merge", „nu merge"), iar cautarea in text l-ar declara viu pe nedrept. Invers,
un apel construit dinamic (`getattr(modul, nume)`) nu se vede in AST: acolo unealta poate
raporta mort ceva viu, si de-aia raportul se citeste, nu se executa.
"""
import argparse
import ast
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _citeste(tipare) -> dict:
    d = {}
    for t in tipare:
        for p in ROOT.glob(t):
            if p.is_file() and "__pycache__" not in str(p):
                d[str(p.relative_to(ROOT))] = p.read_text(encoding="utf-8", errors="replace")
    return d


class _Utilizari(ast.NodeVisitor):
    """Numele CHIAR folosite: `Name` (bare), `Attribute` (`modul.nume`), importuri.

    Definitia nu se numara pe sine: `ast.FunctionDef` nu produce un `Name`.
    """

    def __init__(self):
        self.n = collections.Counter()

    def visit_Name(self, nod):
        self.n[nod.id] += 1

    def visit_Attribute(self, nod):
        self.n[nod.attr] += 1
        self.generic_visit(nod)

    def visit_ImportFrom(self, nod):
        for alias in nod.names:
            self.n[alias.name] += 1


def _utilizari(corpus: dict) -> dict:
    rez = {}
    for cale, text in corpus.items():
        v = _Utilizari()
        try:
            v.visit(ast.parse(text))
        except SyntaxError:
            pass
        rez[cale] = v.n
    return rez


def _in_text(nume: str, corpus: dict) -> int:
    tipar = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(nume)}(?![A-Za-z0-9_])")
    return sum(len(tipar.findall(t)) for t in corpus.values())


def cod() -> int:
    py_cod = _citeste(["generator/**/*.py", "tools/**/*.py", "scripts/**/*.py"])
    py_test = _citeste(["tests/*.py"])
    sabloane = _citeste(["templates/**/*.html"])
    u_cod, u_test = _utilizari(py_cod), _utilizari(py_test)

    rez = []
    for cale, text in py_cod.items():
        if not cale.startswith("generator/"):
            continue
        try:
            arbore = ast.parse(text)
        except SyntaxError:
            continue
        for nod in arbore.body:
            if not isinstance(nod, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            nume = nod.name
            intern = u_cod[cale][nume]
            extern = sum(c[nume] for k, c in u_cod.items() if k != cale)
            if intern or extern or _in_text(nume, sabloane):
                continue
            linii = (nod.end_lineno or nod.lineno) - nod.lineno + 1
            rez.append((linii, cale, nume, nod.lineno,
                        sum(c[nume] for c in u_test.values())))

    rez.sort(reverse=True)
    total = sum(1 for t in py_cod.values() for n in ast.parse(t).body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
    print(f"{'fisier:linie':<34} {'nume':<22} {'linii':>5} {'teste':>6}")
    print("-" * 72)
    for linii, cale, nume, nr, teste in rez:
        print(f"{cale + ':' + str(nr):<34} {nume:<22} {linii:>5} {teste:>6}")
    fara_test = sum(1 for r in rez if r[4] == 0)
    print(f"\n{len(rez)} definitii fara apelant in productie sau sabloane "
          f"(din {total} in generator/, tools/, scripts/); {fara_test} n-au nici test.")
    print("Coloana `teste` > 0 = functia e tinuta in viata DOAR de suita. Nu e automat de")
    print("sters: sect. 10 apara logica de sinteza, iar `state.merge` e declarat cod mort")
    print("cunoscut in specs/STATE.md — se raporteaza, nu se curata din proprie initiativa.")
    return 0


def documente() -> int:
    tinte = sorted(set(_citeste(["*.md", "specs/*.md", "notes/*.md"])))
    corpus = _citeste([
        "*.md", "specs/*.md", "notes/*.md", "sessions/*.md", "handoff/**/*.md",
        ".claude/**/*.md", ".claude/**/*.json", ".claude/**/*.sh", ".claude/**/*.py",
        "generator/**/*.py", "tools/**/*.py", "scripts/**/*.py", "tests/*.py",
        ".github/**/*.yml",
    ])
    rand = []
    for cale in tinte:
        nume = pathlib.Path(cale).name
        tipar = re.compile(re.escape(nume))
        unde = sorted({c for c, t in corpus.items() if c != cale and tipar.search(t)})
        rand.append((len(unde), (ROOT / cale).stat().st_size, cale, unde))
    rand.sort()

    orfane = [r for r in rand if r[0] == 0]
    print(f"{'ref':>4} {'octeti':>7}  fisier")
    print("-" * 72)
    for n, octeti, cale, unde in rand:
        sufix = "  <-- ORFAN" if n == 0 else (
            "  (" + ", ".join(pathlib.Path(u).name for u in unde[:2]) + ")" if n <= 2 else "")
        print(f"{n:>4} {octeti:>7}  {cale}{sufix}")
    print(f"\n{len(orfane)} fisiere fara nicio referinta, {sum(r[1] for r in orfane)} octeti.")
    print("NU costa tokeni per tura — nu se incarca. Costa la CAUTARE: cine deschide `specs/`")
    print("citeste numele directorului ca pe o promisiune de stare, si trebuie sa trieze.")
    return 0


def reguli() -> int:
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    poz = [(m.group(1), m.start(), m.group(2))
           for m in re.finditer(r"^## (\d+[a-z]?)\. (.+)$", claude, flags=re.M)]
    corpus = {c: t for c, t in _citeste([
        "*.md", "specs/*.md", "notes/*.md", "sessions/*.md", "handoff/**/*.md",
        ".claude/**/*.md", ".claude/**/*.json", ".claude/**/*.sh", ".claude/**/*.py",
        "generator/**/*.py", "tools/**/*.py", "scripts/**/*.py", "tests/*.py",
        ".github/**/*.yml",
    ]).items() if c != "CLAUDE.md"}

    rez = []
    for i, (nr, start, titlu) in enumerate(poz):
        sfarsit = poz[i + 1][1] if i + 1 < len(poz) else len(claude)
        octeti = len(claude[start:sfarsit].encode("utf-8"))
        tipar = re.compile(rf"(?:§|sect\.?\s*|sec[tț]iunea\s*)\s*{re.escape(nr)}(?![0-9a-z])", re.I)
        unde = {c for c, t in corpus.items() if tipar.search(t)}
        garda = any(c.startswith("tests/") for c in unde)
        rez.append((octeti / max(len(unde), 1), nr, octeti, len(unde), garda, titlu))

    rez.sort(reverse=True)
    print(f"{'§':<5} {'octeti':>7} {'citari':>7} {'oct/citare':>11} {'garda':>6}  titlu")
    print("-" * 84)
    for cost, nr, octeti, n, garda, titlu in rez:
        print(f"{nr:<5} {octeti:>7} {n:>7} {cost:>11.0f} {'DA' if garda else '—':>6}  {titlu[:38]}")
    total = len(claude.encode("utf-8"))
    fara = sum(o for _, _, o, _, g, _ in rez if not g)
    print(f"\nCLAUDE.md: {total} octeti, platiti la FIECARE tura.")
    print(f"In sectiuni fara garda mecanica: {fara} ({100 * fara / total:.0f}%).")
    print("Citarile masoara daca regula e purtata de masinaria repo-ului (test, agent, hook),")
    print("NU daca e respectata: sect. 12a a fost urmata azi fara ca nimeni sa scrie '§12a'.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nume, ajutor in (("cod", "functii/clase fara apelant"),
                         ("documente", ".md-uri fara referinta"),
                         ("reguli", "sectiunile CLAUDE.md, dupa cost per citare")):
        sub.add_parser(nume, help=ajutor)
    args = ap.parse_args()
    return {"cod": cod, "documente": documente, "reguli": reguli}[args.cmd]()


if __name__ == "__main__":
    sys.exit(main())
