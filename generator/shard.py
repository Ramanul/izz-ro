"""Imparte `output/` in cioburi, cate unul pe Worker (specs/multi-worker-free-2026-11.md).

DE CE. Planul Free permite 20.000 de fisiere pe versiune de Worker, dar 100 de Workere pe cont.
Rutarea Cloudflare trimite `izz.ro/sport/*` la Workerul de sport fiindca ruta mai specifica
castiga; un fisier lipsa din ciob NU cade inapoi pe Workerul principal (felia 0, IZZ-0455).
Deci regula de aici trebuie sa fie EXACT regula de rutare: un fisier ajunge intr-un ciob daca
si numai daca adresa la care e servit se potriveste cu una din rutele ciobului. Altfel fie
pagina sta pe un Worker la care cererea nu ajunge niciodata, fie cererea ajunge la un Worker
care n-o are.

CE NU FACE. Nu atinge `output/` (copiaza in `dist/`), nu publica nimic si nu schimba bugetul
de randare: pana la felia 2 productia ramane un singur Worker, iar pasul asta se poate rula
oricand, pe orice randare, fara efect pe site.

    python -m generator.shard --src output --dest dist
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys

from generator import config

MAIN = "main"
ZONE = "izz.ro"
WORKER_PREFIX = "izz-ro-"
# Aceeasi ca `compatibility_date` a Workerului principal; `tests/test_shard.py` le compara.
COMPAT_DATE = "2026-06-18"
# Fisierele de la radacina pe care fiecare ciob le are in copie proprie: 404.html (ratarile nu
# cad pe principal), `_headers` (CSP si cache pe activele ciobului; o regula pentru o cale care
# nu ajunge la ciob nu se aplica niciodata) si `build.json` (sonda de release citeste commitul
# de pe originea workers.dev a ciobului). `_redirects` se FILTREAZA pe ciob, mai jos.
REPLICATE = ("404.html", "_headers", "build.json")


def plan() -> list[dict]:
    """Cioburile, in ordinea de publicare. Fiecare: nume + prefixe de adresa (fara `/` initial).

    Ruta Cloudflare a unui prefix P este `izz.ro/P*`.
    """
    shards = []
    for cat in config.CATEGORIES:
        if cat == "local":
            continue
        shards.append({"name": f"cat-{cat}", "prefixes": [f"{cat}/"]})
    shards.append({"name": "subiect", "prefixes": [config.SHARD_SUBJECT_PREFIX]})
    for grup in config.LOCAL_SHARD_GROUPS:
        nume = "local-cifre" if grup.isdigit() else f"local-{grup}"
        shards.append({"name": nume, "prefixes": [f"local/{c}" for c in grup]})
    return shards


def live_plan() -> list[dict]:
    """Cioburile din `plan()` activate in `config.SHARDS_LIVE`.

    Orice ciob neactivat (ex. `subiect`, sau o categorie retrasa la rollback) ramane in `main`,
    fiindca pe `izz.ro` cererile lui cad tot pe Workerul principal.
    """
    live = set(config.SHARDS_LIVE)
    return [s for s in plan() if s["name"] in live]


def workers_origin_for(base_url: str, path: str,
                       shards: list[dict] | None = None) -> str:
    """Pe `https://izz-ro.<cont>.workers.dev`, intoarce originea ciobului care serveste `path`.

    Pe domeniul public (`https://izz.ro`) sau pe orice alt host, intoarce `base_url` neschimbat:
    acolo rutarea de zona Cloudflare trimite singura cererea la Workerul potrivit.
    """
    base = base_url.rstrip("/")
    if not (base.startswith(("https://izz-ro.", "http://izz-ro.")) and base.endswith(".workers.dev")):
        return base
    shards = live_plan() if shards is None else shards
    rel = path.split("?", 1)[0].split("#", 1)[0].lstrip("/")
    if not rel or rel.endswith("/"):
        rel = (rel + "index.html") if rel else "index.html"
    tinta = assign(rel, shards)
    if tinta == MAIN:
        return base
    scheme, rest = base.split("://izz-ro.", 1)
    return f"{scheme}://{WORKER_PREFIX}{tinta}.{rest}"


def served_path(relpath: str) -> str:
    """Adresa la care Workers Static Assets serveste fisierul (fara `/` initial).

    `x/index.html` se serveste la `x/` (html_handling implicit), deci acolo se potriveste ruta:
    `local/index.html` raspunde la `/local/`, care NU intra pe `izz.ro/local/i*`.
    """
    relpath = relpath.replace(os.sep, "/")
    if relpath == "index.html":
        return ""
    if relpath.endswith("/index.html"):
        return relpath[: -len("index.html")]
    return relpath


def assign(relpath: str, shards: list[dict]) -> str:
    """Numele ciobului care primeste fisierul; `main` daca nicio ruta nu se potriveste.

    Cea mai lunga potrivire castiga, ca la Cloudflare (ruta mai specifica).
    """
    return _route(served_path(relpath), shards)


def _route(url: str, shards: list[dict]) -> str:
    best, best_len = MAIN, -1
    for shard in shards:
        for prefix in shard["prefixes"]:
            # `auto/` are si ruta exacta `izz.ro/auto` (vezi manifestul), deci adresa `auto`
            # (o sursa `/auto` din `_redirects`) ajunge tot la ciob.
            potrivit = url.startswith(prefix) or (prefix.endswith("/") and url == prefix[:-1])
            if potrivit and len(prefix) > best_len:
                best, best_len = shard["name"], len(prefix)
    return best


def _files(src: str):
    for root, _, files in os.walk(src):
        for name in files:
            full = os.path.join(root, name)
            yield os.path.relpath(full, src).replace(os.sep, "/"), full


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloc in iter(lambda: fh.read(1 << 16), b""):
            h.update(bloc)
    return h.hexdigest()


def partition(src: str, dest: str, shards: list[dict] | None = None,
              ceiling: int | None = None) -> dict:
    """Copiaza `src` in `dest/<ciob>/...` si scrie `dest/shards.json`. Intoarce manifestul.

    Fiecare ciob primeste si `404.html` de la radacina sursei: ratarile nu cad pe Workerul
    principal, deci fiecare Worker trebuie sa-si aiba pagina lui de 404.
    """
    shards = plan() if shards is None else shards
    ceiling = config.OUTPUT_FILE_CEILING if ceiling is None else ceiling
    names = [MAIN] + [s["name"] for s in shards]
    if len(names) != len(set(names)):
        raise ValueError(f"nume de ciob duplicate: {names}")
    src_abs, dest_abs = os.path.abspath(src), os.path.abspath(dest)
    if os.path.commonpath([src_abs, dest_abs]) in (src_abs, dest_abs):
        # rmtree pe un dest care e (sau contine) sursa ar sterge randarea.
        raise ValueError(f"--dest {dest} nu poate fi {src} sau un parinte/copil al lui")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    tree = {n: [] for n in names}

    def _pune(tinta, rel, full, sha):
        out = os.path.join(dest, tinta, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copy2(full, out)
        tree[tinta].append((rel, sha))

    for rel, full in sorted(_files(src)):
        if rel == "_redirects":
            continue
        sha = _sha(full)
        tinta = assign(rel, shards)
        _pune(tinta, rel, full, sha)
        # `x/index.html` raspunde si la adresa lui bruta, care poate cadea pe ALT Worker:
        # `/local/index.html` merge pe ruta `local/i*`. Fara copia de acolo -> 404.
        bruta = _route(rel, shards)
        if bruta != tinta:
            _pune(bruta, rel, full, sha)

    # Fiecare ciob primeste pagina 404, chiar si unul gol: ratarile nu cad pe principal, iar
    # un ciob mereu prezent tine setul de rute stabil intre publicari (categoriile in
    # insamantare pot fi goale azi si pline maine). La fel `_headers` si `build.json`.
    for nume_fisier in REPLICATE:
        full = os.path.join(src, nume_fisier)
        if not os.path.isfile(full):
            continue
        sha_f = _sha(full)
        for s in shards:
            if not any(p == nume_fisier for p, _ in tree[s["name"]]):
                _pune(s["name"], nume_fisier, full, sha_f)

    # `_redirects`: fiecare Worker (inclusiv principalul) primeste DOAR regulile a caror sursa
    # ajunge la el prin rutare. O regula `/auto/x /auto/y` lasata pe principal nu se mai
    # declanseaza (cererea merge la ciob), iar plafonul de reguli e per Worker.
    redir = os.path.join(src, "_redirects")
    if os.path.isfile(redir):
        with open(redir, encoding="utf-8") as fh:
            linii = fh.read().splitlines()
        for nume_ciob in [MAIN] + [s["name"] for s in shards]:
            ale_lui = [ln for ln in linii if ln.strip() and not ln.lstrip().startswith("#")
                       and _route(ln.split()[0].lstrip("/"), shards) == nume_ciob]
            if not ale_lui:
                continue
            out = os.path.join(dest, nume_ciob, "_redirects")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            text = "\n".join(ale_lui) + "\n"
            with open(out, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            tree[nume_ciob].append(("_redirects", hashlib.sha256(text.encode()).hexdigest()))

    manifest = {"zone": ZONE, "ceiling": ceiling, "shards": []}
    for s in [{"name": MAIN, "prefixes": []}] + shards:
        fisiere = sorted(tree[s["name"]])
        amprenta = hashlib.sha256(
            "".join(f"{p}\0{h}\n" for p, h in fisiere).encode()).hexdigest()
        rute = []
        for p in s["prefixes"]:
            if p.endswith("/"):
                # `izz.ro/sport` (fara bara) nu intra pe `izz.ro/sport/*`; pe principal nu exista
                # `sport/index.html`, deci redirectul spre `/sport/` nu s-ar mai face -> 404.
                rute.append(f"{ZONE}/{p[:-1]}")
            rute.append(f"{ZONE}/{p}*")
        manifest["shards"].append({
            "name": s["name"],
            "routes": rute or [f"{ZONE}/*"],
            "file_count": len(fisiere),
            "tree_sha256": amprenta,
        })

    # Plafonul se verifica INAINTE de a scrie manifestul: un shards.json pe disc trebuie sa
    # insemne o impartire publicabila, nu una care a picat.
    peste = [s for s in manifest["shards"] if s["file_count"] > ceiling]
    if peste:
        raise RuntimeError("cioburi peste plafonul de %d fisiere: %s" % (
            ceiling, ", ".join(f"{s['name']}={s['file_count']}" for s in peste)))
    os.makedirs(dest, exist_ok=True)
    for s in manifest["shards"]:
        if s["name"] == MAIN:
            continue
        s["worker"] = WORKER_PREFIX + s["name"]
        with open(os.path.join(dest, s["worker"] + ".config.json"), "w", encoding="utf-8") as fh:
            json.dump(worker_config(s), fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    with open(os.path.join(dest, "shards.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return manifest


def worker_config(entry: dict) -> dict:
    """Configuratia wrangler a unui ciob, scrisa ca `dist/<worker>.config.json`.

    Caile sunt relative la `dist/` (wrangler le rezolva fata de fisierul de config). Scriptul e
    DOAR fallback-ul spre oglinda: un articol iesit din fereastra ciobului nu mai ajunge la
    scriptul principal (ruta ciobului castiga), deci ciobul il aduce singur de pe oglinda.
    Fara `not_found_handling`, ca la principal: ratarea invoca scriptul, care serveste 404.html.
    `workers_dev` da originea fara bot challenge pe care o citeste sonda de release.
    """
    return {
        "name": entry["worker"],
        "main": "../infra/worker-404-mirror.js",
        "compatibility_date": COMPAT_DATE,
        "assets": {"directory": "./" + entry["name"], "binding": "ASSETS"},
        "workers_dev": True,
        "preview_urls": False,
        "routes": [{"pattern": r, "zone_name": ZONE} for r in entry["routes"]],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default="output")
    ap.add_argument("--dest", default="dist")
    ap.add_argument("--live-only", action="store_true",
                    help="imparte doar cioburile din config.SHARDS_LIVE; restul raman in main")
    args = ap.parse_args(argv)
    if not os.path.isfile(os.path.join(args.src, "index.html")):
        print(f"!! {args.src}/index.html lipseste -- randeaza intai", file=sys.stderr)
        return 1
    manifest = partition(args.src, args.dest, shards=live_plan() if args.live_only else None)
    for s in manifest["shards"]:
        if s["file_count"]:
            print(f"{s['name']:<16} {s['file_count']:>6}  {', '.join(s['routes'])}")
    print(f">> {sum(s['file_count'] for s in manifest['shards'])} fisiere in "
          f"{sum(1 for s in manifest['shards'] if s['file_count'])} cioburi -> {args.dest}/shards.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
