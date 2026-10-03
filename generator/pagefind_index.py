"""Cautarea site-ului: index static Pagefind, generat IN pipeline (nu manual).

DE CE EXISTA. Cautarea de pana pe 2026-10-03 (`static/search.js`) descarca tot
`search-index.json` si facea `indexOf` pe TITLU normalizat: potrivire doar in titlu,
fara nicio ierarhie a rezultatelor, iar costul era intregul JSON la prima tasta apasata.
Pagefind construieste la build un index BM25 real, cu stemmer de romana si pliere de
diacritice, iar clientul descarca doar bucata de index care contine termenii cautati —
masurat pe randarea reala: un singur fisier `.pf_index` de ~17 KB pentru un termen obisnuit.

DE CE E AICI, NU INTR-UN SCRIPT SEPARAT. Cerinta e ca indexul sa apara la FIECARE build
fara comanda manuala. `render.build()` cheama `ruleaza()` dupa ce a scris tot HTML-ul,
deci il primesc automat toate cele trei cai de build: local, `tests.yml` (jobul html-gate
randeaza output-ul real) si Cloudflare Workers Builds — a carui comanda de build sta in
Settings, NU in repo, deci nu poate fi schimbata dintr-un diff. Aici e singurul loc din
care o schimbare de cod ajunge si pe izz.ro.

PLAFONUL DE FISIERE, masurat si nu presupus (specs/cautare-pagefind.md). Pe Workers Free
o versiune de Worker are cel mult 20.000 de fisiere statice, iar un deploy supradimensionat
e refuzat TACUT (incidentul din 2026-08-21: job verde, site inghetat 21 de ore). Pagefind
scrie UN fisier de fragment PER PAGINA — asta e forma indexului, nu o setare. Masurat pe
randarea reala din 2026-10-03 (9.451 de pagini de articol publicate, 14.483 de fisiere in
output inainte de indexare):

    cu fragmente:   9.458 fisiere in plus -> 23.941 total  (19,7% PESTE plafon)
    fara fragmente:    52 fisiere in plus -> 14.535 total  (marja 2.465 fata de buget)

De aceea `curata_bundle()` sterge `fragment/`. Pretul, spus pe fata: fara fragment clientul
nu mai poate cere excerptul din corpul articolului, deci rezultatele arata titlul (cu
termenii marcati), categoria si data. Ce NU se pierde e tocmai ce conta: POTRIVIREA se face
in continuare pe titlu + textul rezumatului, iar `harta_url_id()` citeste fragmentele
INAINTE sa le stearga, ca mapa de rezultate (`search-index.json`) sa poata lega id-ul
Pagefind de articol fara inca o cerere HTTP.

ESUARE. Indexul e un adaos, nu o conditie de publicare: daca binarul lipseste sau Pagefind
iese cu eroare, randarea continua fara `_pagefind/`, iar pagina /cauta/ cade pe cautarea
simplificata (doar titluri) si spune asta in pagina. Un build care moare din cauza cautarii
ar ingheta site-ul — exact incidentul pe care bugetul de fisiere il apara. Exceptia e
`PAGEFIND_STRICT=1` (folosit de poarta HTML din `tests.yml`): acolo esecul TREBUIE sa pice,
ca o regresie de pipeline sa fie rosie in PR, nu invizibila pe live.

`PAGEFIND_ENABLED=0` sare de tot peste indexare. E opt-out explicit si are un singur
consumator legitim: jobul `mirror` din `build.yml`, care publica pe gh-pages si nu serveste
niciodata /cauta/ — vezi comentariul din `ruleaza()`.
"""
import gzip
import json
import logging
import os
import shutil
import subprocess
import time

# Romana, fortat. Fara asta Pagefind deduce limba din `<html lang>` pagina cu pagina; un
# articol cu un citat lung intr-o alta limba ar putea fi indexat cu alt stemmer, adica
# doua reguli de normalizare in acelasi index. `--force-language` face indexul omogen.
LIMBA = "ro"
SUBDIR = "_pagefind"
# Semnatura pe care Pagefind o pune la inceputul oricarui fisier comprimat din bundle.
# Verificata, nu presupusa: `harta_url_id()` o cere explicit si ridica daca lipseste, ca o
# schimbare de format intr-o versiune viitoare sa pice aici, nu sa produca o mapa goala.
SEMANTURA = b"pagefind_dcd"

# Fisiere din bundle pe care izz.ro nu le cere niciodata. UI-urile Pagefind au etichete
# englezesti si stiluri proprii — noi avem UI propriu (`templates/search.html`), in romana
# si pe sistemul φ din `static/styles.css`. `pagefind-highlight.js` ar marca termenii pe
# pagina de articol, dar ar costa o cerere in plus pe FIECARE pagina a site-ului; e lasat
# afara deliberat (specs/cautare-pagefind.md, „Urmatorul pas").
NEFOLOSITE = (
    "pagefind-ui.js", "pagefind-ui.css",
    "pagefind-modular-ui.js", "pagefind-modular-ui.css",
    "pagefind-component-ui.js", "pagefind-component-ui.css",
    "pagefind-highlight.js",
)


def binar() -> str | None:
    """Calea executabilului Pagefind, sau None daca nu e instalat.

    Ordinea e deliberata: un override explicit din mediu (debug local, o gazda fara pip),
    apoi wheel-ul PyPI `pagefind-bin` — care e in `requirements.txt`, deci il au si CI si
    Cloudflare Builds fara nicio comanda in plus — apoi PATH, pentru cine ruleaza `npx`.
    """
    din_mediu = (os.getenv("PAGEFIND_BIN") or "").strip()
    if din_mediu:
        return din_mediu if os.path.isfile(din_mediu) else None
    try:
        from pagefind_bin import get_executable
    except ImportError:
        pass
    else:
        try:
            cale = get_executable()
        except (FileNotFoundError, OSError):
            pass
        else:
            if os.path.isfile(cale):
                return str(cale)
    for nume in ("pagefind_extended", "pagefind"):
        gasit = shutil.which(nume)
        if gasit:
            return gasit
    return None


def _indexeaza(exe: str, out_dir: str) -> dict:
    """Ruleaza indexatorul peste `out_dir`. Ridica `RuntimeError` la esec."""
    tinta = os.path.join(out_dir, SUBDIR)
    proc = subprocess.run(
        [exe, "--site", out_dir, "--output-path", tinta, "--force-language", LIMBA],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"pagefind a iesit cu cod {proc.returncode}: "
            f"{(proc.stderr or proc.stdout or '').strip()[-600:]}")
    return {"iesire": (proc.stdout or "") + (proc.stderr or "")}


def _pagini_indexate(out_dir: str) -> int:
    """Cate pagini a indexat Pagefind, citit din manifestul lui (nu din log)."""
    cale = os.path.join(out_dir, SUBDIR, "pagefind-entry.json")
    try:
        with open(cale, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError):
        return 0
    return sum(int(v.get("page_count") or 0)
               for v in (manifest.get("languages") or {}).values())


def harta_url_id(out_dir: str) -> dict:
    """`{url_pagina: id_pagefind}`, citit din fragmente INAINTE de stergere.

    Id-ul Pagefind (`ro_1a2b3c4`) e tot numele fisierului de fragment si e singurul lucru
    pe care il intoarce `pagefind.search()` inainte de `data()`. Fara mapa asta clientul ar
    trebui sa ceara fragmentul ca sa afle URL-ul rezultatului — adica exact fisierul pe care
    il stergem ca sa incapa in plafonul de fisiere. O citim la build, o data, si o punem in
    `search-index.json`.

    Ridica daca formatul nu e cel asteptat: o mapa GOALA ar trece testele si ar lasa pagina
    de cautare fara niciun rezultat, adica un esec tacut — cel mai scump fel de esec din
    repo-ul asta.
    """
    director = os.path.join(out_dir, SUBDIR, "fragment")
    if not os.path.isdir(director):
        return {}
    harta = {}
    for nume in sorted(os.listdir(director)):
        if not nume.endswith(".pf_fragment"):
            continue
        id_pagina = nume[: -len(".pf_fragment")]
        with open(os.path.join(director, nume), "rb") as fh:
            brut = fh.read()
        try:
            decomprimat = gzip.decompress(brut)
        except OSError as exc:
            raise RuntimeError(f"fragmentul {nume} nu e gzip valid: {exc}") from exc
        if not decomprimat.startswith(SEMANTURA):
            raise RuntimeError(
                f"fragmentul {nume} nu incepe cu {SEMANTURA!r}: formatul Pagefind s-a "
                "schimbat. Actualizeaza SEMANTURA/harta_url_id() impreuna cu versiunea "
                "fixata in requirements.txt — nu face mapa optionala.")
        try:
            url = json.loads(decomprimat[len(SEMANTURA):]).get("url")
        except ValueError as exc:
            raise RuntimeError(f"fragmentul {nume} nu e JSON valid: {exc}") from exc
        if url:
            harta[url] = id_pagina
    return harta


def curata_bundle(out_dir: str) -> int:
    """Sterge din bundle ce nu se serveste niciodata. Intoarce cate fisiere a scos.

    `fragment/` e marea majoritate (un fisier per pagina) si e singurul lucru care ar sparge
    plafonul gazdei; UI-urile sunt cateva sute de KB de cod mort. Verificat prin masurare,
    nu prin estimare: 11.114 fisiere sterse la randarea din 2026-10-03.
    """
    radacina = os.path.join(out_dir, SUBDIR)
    if not os.path.isdir(radacina):
        return 0
    scoase = 0
    fragmente = os.path.join(radacina, "fragment")
    if os.path.isdir(fragmente):
        scoase += sum(len(fs) for _, _, fs in os.walk(fragmente))
        shutil.rmtree(fragmente)
    for nume in NEFOLOSITE:
        cale = os.path.join(radacina, nume)
        if os.path.isfile(cale):
            os.remove(cale)
            scoase += 1
    return scoase


def numara_fisiere(out_dir: str) -> int:
    """Cate fisiere a ramas sa aiba bundle-ul — cifra care intra in bugetul gazdei."""
    radacina = os.path.join(out_dir, SUBDIR)
    if not os.path.isdir(radacina):
        return 0
    return sum(len(fs) for _, _, fs in os.walk(radacina))


def ruleaza(out_dir: str, strict: bool | None = None) -> dict:
    """Construieste indexul in `out_dir/_pagefind` si intoarce statistici.

    Nu ridica niciodata in modul normal: un index lipsa inseamna cautare simplificata,
    nu site jos. Cu `strict=True` (sau `PAGEFIND_STRICT=1`) ridica — asa verifica poarta
    HTML din `tests.yml` ca pipeline-ul chiar produce indexul.
    """
    if strict is None:
        strict = os.getenv("PAGEFIND_STRICT", "") == "1"
    statistici = {"ok": False, "pagini": 0, "fisiere": 0, "sterse": 0,
                  "secunde": 0.0, "motiv": "", "harta": {}}
    # Opt-out explicit, nu implicit: singurul loc care il foloseste e jobul `mirror` din
    # build.yml, care publica pe gh-pages cu `keep_files: true`. Acolo indexul n-are la ce
    # sa foloseasca (oglinda serveste pagini de articol la 404, nu /cauta/), iar bucatile de
    # index sunt nume-amprentate: ~50 de fisiere noi la fiecare republicare, de ~12 ori pe zi,
    # intr-un repo al carui plafon de 1 GB e deja masurat lunar.
    if os.getenv("PAGEFIND_ENABLED", "1") == "0":
        statistici["motiv"] = "dezactivat (PAGEFIND_ENABLED=0)"
        print(">> cautare: indexul Pagefind e dezactivat pentru build-ul asta")
        return statistici
    inceput = time.monotonic()
    try:
        exe = binar()
        if not exe:
            raise RuntimeError(
                "binarul Pagefind lipseste (pip install pagefind-bin, PAGEFIND_BIN, sau "
                "pagefind in PATH)")
        _indexeaza(exe, out_dir)
        statistici["harta"] = harta_url_id(out_dir)
        statistici["sterse"] = curata_bundle(out_dir)
        statistici["pagini"] = _pagini_indexate(out_dir)
        statistici["fisiere"] = numara_fisiere(out_dir)
        statistici["ok"] = True
    except (OSError, RuntimeError, ValueError) as exc:
        statistici["motiv"] = str(exc)
        if strict:
            raise
        logging.error("!! indexul de cautare NU s-a construit (%s) — /cauta/ ramane pe "
                      "cautarea simplificata, doar in titluri.", exc)
    statistici["secunde"] = round(time.monotonic() - inceput, 2)
    if statistici["ok"]:
        print(f">> cautare: index Pagefind pentru {statistici['pagini']} pagini in "
              f"{statistici['fisiere']} fisiere ({statistici['secunde']} s); "
              f"{statistici['sterse']} fisiere de fragment sterse din bugetul gazdei")
    return statistici


def verifica(out_dir: str) -> int:
    """Poarta de build: 0 daca indexul e intreg, 1 altfel. Folosita de `tests.yml`."""
    radacina = os.path.join(out_dir, SUBDIR)
    probleme = []
    if not os.path.isdir(radacina):
        probleme.append(f"{SUBDIR}/ lipseste")
    else:
        for cerut in ("pagefind.js", "pagefind-entry.json", "pagefind-worker.js"):
            if not os.path.isfile(os.path.join(radacina, cerut)):
                probleme.append(f"{SUBDIR}/{cerut} lipseste")
        if not os.path.isdir(os.path.join(radacina, "index")):
            probleme.append(f"{SUBDIR}/index/ lipseste")
        if os.path.isdir(os.path.join(radacina, "fragment")):
            probleme.append(f"{SUBDIR}/fragment/ exista — ar sparge plafonul de fisiere")
        pagini = _pagini_indexate(out_dir)
        if pagini < 1:
            probleme.append("indexul nu contine nicio pagina")
    if probleme:
        for p in probleme:
            print(f"!! {p}")
        return 1
    print(f">> verificat: {_pagini_indexate(out_dir)} pagini in index, "
          f"{numara_fisiere(out_dir)} fisiere, fara fragmente")
    return 0


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", metavar="OUTPUT",
                        help="verifica un index deja construit (0 = ok)")
    parser.add_argument("--build", metavar="OUTPUT",
                        help="construieste indexul si esueaza la orice problema")
    args = parser.parse_args()
    if args.build:
        rezultat = ruleaza(args.build, strict=True)
        sys.exit(0 if rezultat["ok"] else 1)
    sys.exit(verifica(args.verify or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")))
