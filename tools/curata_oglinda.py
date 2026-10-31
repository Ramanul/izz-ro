#!/usr/bin/env python3
"""Curata oglinda GitHub Pages printr-un commit normal: fara checkout, fara force-push.

Doua comenzi, amandoua pe simulare pana la `--aplica`:

  imagini  O singura data. Sterge toate imaginile de articol (`cover`, `art`, `photo`) si
           rescrie paginile care inca le cer: scoate fotografia cu creditul ei si muta
           previzualizarea sociala pe coperta categoriei. Refuza sa publice daca ramane o
           singura referinta catre o imagine stearsa.
  plafon   La fiecare rulare a jobului `mirror`, dupa publicare. Masoara oglinda; peste 950 MB
           taie cele mai vechi pagini de articol pana la 850 MB. Paginile raman in istoricul
           git, deci se pot recupera. Refuzul inseamna job rosu, adica e-mail la proprietar.

DE CE COMMIT CONSTRUIT, NU CHECKOUT. Oglinda are zeci de mii de fisiere, iar imaginile nu
trebuie descarcate ca sa fie sterse. Clona ramane fara fisiere, se aduc doar paginile HTML in
loturi, iar `git fast-import` scrie commitul direct peste parinte. Fara `--force` nicaieri: un
push respins lasa oglinda neatinsa, iar rularea urmatoare o ia de la capat.

NU STERGE niciodata pagini mai noi de `ZILE_MINIME` si nici mai mult de `MAX_FRACTIE` dintr-o
data: o masuratoare gresita trebuie sa dea refuz, nu o arhiva golita.
"""
from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
import time
from datetime import date, datetime, timedelta, timezone

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADACINA)
from generator import config  # noqa: E402
from tools import masoara_oglinda as masurare  # noqa: E402

URL_CITIRE = f"https://github.com/{masurare.REPO}.git"
URL_SSH = f"git@github.com:{masurare.REPO}.git"

ZILE_MINIME = 21
MAX_FRACTIE = 0.30
LOT_ADUCERE = 4000

_CATEGORIE = "|".join(config.CATEGORIES)
_NUME_IMAGINE = r"(?:cover\.jpg|art\.jpg|art\.webp|art-card\.webp|photo\.jpg|photo\.webp)"
# Acelasi tipar de slug pentru ce se sterge si pentru ce se cauta in pagini: daca ar diferi, o
# imagine s-ar putea sterge fara ca verificarea sa-i vada referinta.
_SLUG = r"""[^/"'?\s<>]+"""
IMAGINE = re.compile(rf"(?:{_CATEGORIE})/{_SLUG}/{_NUME_IMAGINE}")
ARTICOL = re.compile(rf"(?:{_CATEGORIE})/(?![0-9]+/)[^/]+/index\.html")
REFERINTA = re.compile(rf"/(?:{_CATEGORIE})/{_SLUG}/{_NUME_IMAGINE}")
FIGURA = re.compile(r'[ \t]*<figure class="article-art-fig">.*?</figure>[ \t]*\n?', re.S)
CARD = re.compile(r'<a class="card-media card-media--fullbleed"[^>]*><picture>.*?</picture></a>'
                  r'(?:\s*<p class="card-credit">.*?</p>)?', re.S)
COPERTA = re.compile(rf"https://izz\.ro/({_CATEGORIE})/{_SLUG}/cover\.jpg(?:\?v=[0-9a-f]+)?")
DATA = re.compile(rb'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})'
                  rb'|article:published_time"\s+content="(\d{4}-\d{2}-\d{2})')
CALE_SIGURA = re.compile(r"[\x21\x23-\x7e]+")

# Fara descarcari ascunse: o imagine ceruta din greseala trebuie sa dea eroare, nu 3 GB de trafic.
FARA_DESCARCARI = dict(os.environ, GIT_NO_LAZY_FETCH="1")


class Refuz(Exception):
    """Curatarea se opreste inainte sa publice ceva."""


def rescrie_pagina(html: str) -> str:
    """Pagina fara dependenta de imaginile de articol. Restul textului ramane neatins."""
    def fara_imagine(potrivire: re.Match) -> str:
        return "" if REFERINTA.search(potrivire.group(0)) else potrivire.group(0)

    html = CARD.sub(fara_imagine, FIGURA.sub(fara_imagine, html))
    return COPERTA.sub(lambda m: f"https://izz.ro/og/{m.group(1)}.jpg", html)


def data_pagina(continut: bytes) -> str | None:
    potrivire = DATA.search(continut)
    if not potrivire:
        return None
    return (potrivire.group(1) or potrivire.group(2)).decode("ascii")


def alege_de_taiat(pagini: list[tuple[str, str, int]], de_eliberat: int, azi: date) -> tuple[list[str], int]:
    """Cele mai vechi pagini (data, cale, octeti) care elibereaza `de_eliberat` octeti."""
    prag = (azi - timedelta(days=ZILE_MINIME)).isoformat()
    alese: list[str] = []
    eliberat = 0
    for data, cale, marime in sorted(pagini):
        if eliberat >= de_eliberat:
            break
        if data >= prag:
            raise Refuz(f"plafonul ar taia pagini din ultimele {ZILE_MINIME} zile ({cale}, {data})")
        alese.append(cale)
        eliberat += marime
    if eliberat < de_eliberat:
        raise Refuz(f"toate paginile eligibile elibereaza doar {eliberat} din {de_eliberat} octeti")
    if len(alese) > len(pagini) * MAX_FRACTIE:
        raise Refuz(f"taierea ar sterge {len(alese)} din {len(pagini)} pagini, peste {MAX_FRACTIE:.0%}")
    return alese, eliberat


def git(depozit: str, *argumente: str, intrare: bytes | None = None, mediu: dict | None = None) -> bytes:
    return subprocess.run(["git", "-C", depozit, *argumente], input=intrare, capture_output=True,
                          check=True, env=mediu or FARA_DESCARCARI).stdout


def cloneaza(sursa: str, depozit: str) -> str:
    subprocess.run(["git", "clone", "--quiet", "--bare", "--depth", "1", "--single-branch",
                    "--branch", masurare.RAMURA, "--filter=blob:none", sursa, depozit], check=True)
    return git(depozit, "rev-parse", f"refs/heads/{masurare.RAMURA}").decode().strip()


def listeaza(depozit: str, commit: str) -> dict[str, str]:
    """Cale -> sha, din arbore. Nu are nevoie de fisiere descarcate."""
    fisiere = {}
    for rand in git(depozit, "ls-tree", "-r", "-z", commit).decode().split("\0"):
        if rand:
            meta, cale = rand.split("\t", 1)
            fisiere[cale] = meta.split()[2]
    return fisiere


def aduce(depozit: str, sha_uri: list[str]) -> None:
    """Paginile cerute, in loturi. Aceeasi comanda pe care git o foloseste pentru un fisier lipsa."""
    for i in range(0, len(sha_uri), LOT_ADUCERE):
        git(depozit, "-c", "fetch.negotiationAlgorithm=noop", "fetch", "origin", "--no-tags",
            "--no-write-fetch-head", "--recurse-submodules=no", "--filter=blob:none", "--stdin",
            intrare="\n".join(sha_uri[i:i + LOT_ADUCERE]).encode(), mediu=dict(os.environ))


def citeste(depozit: str, pagini: dict[str, str]):
    """(cale, continut) pentru fiecare pagina, printr-un singur proces `cat-file --batch`."""
    proces = subprocess.Popen(["git", "-C", depozit, "cat-file", "--batch"], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, env=FARA_DESCARCARI)

    def trimite() -> None:
        for sha in pagini.values():
            proces.stdin.write(f"{sha}\n".encode())
        proces.stdin.close()

    threading.Thread(target=trimite, daemon=True).start()
    try:
        for cale in pagini:
            antet = proces.stdout.readline().decode().split()
            if antet[-1] == "missing":
                raise Refuz(f"pagina {cale} n-a fost adusa, deci verificarea ar fi incompleta")
            continut = proces.stdout.read(int(antet[2]))
            proces.stdout.read(1)
            yield cale, continut
    finally:
        # Altfel, un refuz lasa procesul viu, iar pe Windows directorul temporar nu se mai sterge.
        proces.kill()
        proces.wait()


def comite(depozit: str, parinte: str, sterse: list[str], rescrise: dict[str, bytes], mesaj: str) -> str:
    """Un commit normal peste `parinte`. Atinge doar caile date, restul arborelui ramane."""
    def date_(continut: bytes) -> bytes:
        return b"data %d\n%b\n" % (len(continut), continut)

    for cale in [*sterse, *rescrise]:
        if not CALE_SIGURA.fullmatch(cale):
            raise Refuz(f"cale neasteptata, nu o trimit prin fast-import: {cale!r}")
    ref = "refs/heads/curatare"
    flux = [f"commit {ref}\ncommitter izz-oglinda <actions@users.noreply.github.com> "
            f"{int(time.time())} +0000\n".encode(), date_(mesaj.encode()), f"from {parinte}\n".encode()]
    flux += [f"D {cale}\n".encode() for cale in sterse]
    for cale, continut in rescrise.items():
        flux += [f"M 100644 inline {cale}\n".encode(), date_(continut)]
    flux.append(b"\n")
    git(depozit, "fast-import", "--quiet", intrare=b"".join(flux))
    return git(depozit, "rev-parse", ref).decode().strip()


def impinge(depozit: str, commit: str, tinta: str | None = None) -> None:
    """Push obisnuit. `--no-thin` evita cautarea unor baze de delta printre fisierele nedescarcate."""
    mediu = dict(FARA_DESCARCARI)
    with tempfile.TemporaryDirectory() as tmp:
        cheie = os.environ.get("MIRROR_DEPLOY_KEY")
        if cheie and tinta is None:
            fisier = os.path.join(tmp, "cheie")
            with open(fisier, "w", encoding="ascii", newline="\n") as f:
                f.write(cheie.strip() + "\n")
            os.chmod(fisier, stat.S_IRUSR | stat.S_IWUSR)
            mediu["GIT_SSH_COMMAND"] = (f"ssh -i {fisier} -o IdentitiesOnly=yes "
                                        "-o StrictHostKeyChecking=accept-new")
            tinta = URL_SSH
        git(depozit, "push", "--no-thin", tinta or URL_CITIRE,
            f"{commit}:refs/heads/{masurare.RAMURA}", mediu=mediu)


def curata_imagini(sursa: str, aplica: bool, tinta: str | None = None) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        depozit = os.path.join(tmp, "oglinda.git")
        parinte = cloneaza(sursa, depozit)
        fisiere = listeaza(depozit, parinte)
        imagini = sorted(c for c in fisiere if IMAGINE.fullmatch(c))
        pagini = {c: s for c, s in fisiere.items() if c.endswith(".html")}
        aduce(depozit, sorted(set(pagini.values())))

        rescrise: dict[str, bytes] = {}
        ramase: list[tuple[str, str]] = []
        for cale, continut in citeste(depozit, pagini):
            text = continut.decode("utf-8")
            if not REFERINTA.search(text):
                continue
            noua = rescrie_pagina(text)
            ramasa = REFERINTA.search(noua)
            if ramasa:
                ramase.append((cale, ramasa.group(0)))
            rescrise[cale] = noua.encode("utf-8")
        if ramase:
            raise Refuz(f"{len(ramase)} pagini cer imagini si dupa rescriere, prima: {ramase[0]}")
        coperti = {c.split("/", 1)[0] for c in rescrise}
        lipsa = [c for c in coperti & set(config.CATEGORIES) if f"og/{c}.jpg" not in fisiere]
        if lipsa:
            raise Refuz(f"lipsesc copertile de categorie pentru {sorted(lipsa)}")
        if not imagini and not rescrise:
            return {"imagini": 0, "pagini": 0, "commit": None, "sterse": []}

        mesaj = f"curatare: {len(imagini)} imagini de articol sterse, {len(rescrise)} pagini rescrise"
        commit = comite(depozit, parinte, imagini, rescrise, mesaj)
        dupa = listeaza(depozit, commit)
        if set(fisiere) - set(dupa) != set(imagini) or set(dupa) - set(fisiere):
            raise Refuz("commitul construit nu sterge exact imaginile cerute")
        if aplica:
            impinge(depozit, commit, tinta)
        return {"imagini": len(imagini), "pagini": len(rescrise), "commit": commit, "sterse": imagini}


def taie_la_plafon(sursa: str, aplica: bool, marimi: dict[str, int], azi: date,
                   tinta: str | None = None) -> dict:
    de_eliberat = sum(marimi.values()) - masurare.TINTA_MB * masurare.MB
    with tempfile.TemporaryDirectory() as tmp:
        depozit = os.path.join(tmp, "oglinda.git")
        parinte = cloneaza(sursa, depozit)
        articole = {c: s for c, s in listeaza(depozit, parinte).items() if ARTICOL.fullmatch(c)}
        aduce(depozit, sorted(set(articole.values())))
        pagini = []
        for cale, continut in citeste(depozit, articole):
            data = data_pagina(continut)
            if data:
                pagini.append((data, cale, marimi.get(cale, len(continut))))
        alese, eliberat = alege_de_taiat(pagini, de_eliberat, azi)
        directoare = [cale.rsplit("/", 1)[0] for cale in alese]
        mesaj = f"plafon: {len(alese)} pagini vechi taiate, {eliberat / masurare.MB:.0f} MB eliberati"
        commit = comite(depozit, parinte, directoare, {}, mesaj)
        if aplica:
            impinge(depozit, commit, tinta)
        return {"pagini": len(alese), "eliberat": eliberat, "commit": commit, "sterse": directoare}


def comanda_imagini(aplica: bool) -> int:
    marimi = masurare.arbore()
    rezultat = curata_imagini(URL_CITIRE, aplica)
    inainte = sum(marimi.values())
    dupa = inainte - sum(marimi.get(c, 0) for c in rezultat["sterse"])
    print(f">> {rezultat['imagini']} imagini, {rezultat['pagini']} pagini rescrise; "
          f"{inainte / masurare.MB:,.0f} MB -> ~{dupa / masurare.MB:,.0f} MB; "
          f"{'PUBLICAT' if aplica else 'simulare'}: {rezultat['commit']}")
    return 0


def comanda_plafon(aplica: bool) -> int:
    marimi = masurare.arbore()
    repo_kb = masurare.cere_api(f"repos/{masurare.REPO}")["size"]
    masurare.publica_raport(masurare.raport(marimi, repo_kb))
    masurare.semnaleaza_repo(repo_kb)
    total = sum(marimi.values())
    stare = masurare.verdict(total)
    if stare == "ok":
        return 0
    if stare == "avertizare":
        print(f"::warning::oglinda are {total / masurare.MB:,.0f} MB; la "
              f"{masurare.PLAFON_MB} MB se taie automat cele mai vechi pagini")
        return 0
    rezultat = taie_la_plafon(URL_CITIRE, aplica, marimi, datetime.now(timezone.utc).date())
    ramas = total - rezultat["eliberat"]
    masurare.publica_raport(f"\nDupa taiere: {ramas / masurare.MB:,.0f} MB, {rezultat['pagini']} pagini "
                            f"vechi scoase ({'publicat' if aplica else 'simulare'}).")
    print(f"::warning::plafon: {rezultat['pagini']} pagini vechi taiate, oglinda ramane la "
          f"{ramas / masurare.MB:,.0f} MB")
    return 1 if masurare.verdict(ramas) == "rosu" else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Curata oglinda GitHub Pages printr-un commit normal.")
    parser.add_argument("comanda", choices=["imagini", "plafon"])
    parser.add_argument("--aplica", action="store_true", help="publica; fara el e simulare")
    argumente = parser.parse_args()
    comanda = comanda_imagini if argumente.comanda == "imagini" else comanda_plafon
    try:
        return comanda(argumente.aplica)
    except Refuz as refuz:
        print(f"::error::{refuz}")
    except subprocess.CalledProcessError as eroare:
        print(f"::error::git a esuat: {(eroare.stderr or b'').decode('utf-8', 'replace')[-500:]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
