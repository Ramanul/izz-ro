"""Repopuleaza `data/articles.json` cu articole pe care Google le are indexate dar site-ul
nu le mai serveste.

De ce exista: `state.expire()` sterge din stare articolele peste `ARTICLE_TTL_DAYS`, iar
site-ul fiind generat static asta face pagina sa dispara complet. Google pastreaza adresa in
index si o serveste cititorilor, care primesc 404. Masurat pe 20 aug 2026: 193 de pagini
raportate asa in Search Console, iar cautarea `maria baetica` statea pe pozitia 7,5 cu 18
afisari si ZERO clicuri fiindca pagina murise.

Unealta e TINTITA, deliberat: repopuleaza doar adresele pe care Google le cere efectiv (din
exportul Search Console), nu tot ce s-ar putea recupera din istoric. Motivul e raportul
risc/castig — alea sunt exact paginile care aveau deja pozitie in cautare, iar un import in
masa ar umfla starea cu articole pe care nimeni nu le cere.

Sursa de adevar e istoricul Git al lui `data/articles.json`: articolele n-au fost pierdute,
doar scoase din stare. Se cauta inapoi in timp si se ia PRIMA aparitie a fiecarui slug tinta.

Utilizare:
    python tools/recupereaza_404.py <export_gsc.csv>            # doar raporteaza
    python tools/recupereaza_404.py <export_gsc.csv> --scrie    # scrie in articles.json

NU rula inainte ca `ARTICLE_TTL_DAYS` sa fie destul de mare cat sa le tina: cu pragul vechi de
7 zile, articolele recuperate sunt sterse la loc de prima rulare a pipeline-ului.
"""
import csv
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARE = os.path.join(ROOT, "data", "articles.json")
ZILE_ISTORIC = 40          # cat de departe cautam in urma; peste TTL, ca sa prindem si marginea


def _incarca(ref: str):
    """Continutul lui articles.json la un commit dat, sau None daca nu se poate citi."""
    r = subprocess.run(["git", "show", f"{ref}:data/articles.json"],
                       capture_output=True, cwd=ROOT)
    if r.returncode:
        return None
    try:
        d = json.loads(r.stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return d if isinstance(d, list) else d.get("articles")


def _data(a: dict):
    v = a.get("published") or a.get("first_seen") or ""
    try:
        x = datetime.fromisoformat(v)
    except (ValueError, TypeError):
        return None
    return x if x.tzinfo else x.replace(tzinfo=timezone.utc)


def sluguri_tinta(cale_csv: str) -> dict:
    """Slug -> URL, din exportul Search Console. Paginile de subiect se sar: ele au
    `noindex` deliberat (templates/subject.html), deci un 404 acolo nu costa trafic."""
    tinta = {}
    with io.open(cale_csv, encoding="utf-8-sig") as fh:
        for rand in csv.DictReader(fh):
            u = (rand.get("URL") or "").rstrip("/")
            if not u or "/subiect/" in u:
                continue
            tinta[u.split("/")[-1]] = u
    return tinta


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cale_csv = sys.argv[1]
    scrie = "--scrie" in sys.argv

    tinta = sluguri_tinta(cale_csv)
    curent = _incarca("HEAD")
    if curent is None:
        print("!! nu pot citi data/articles.json la HEAD")
        return 1
    prezente = {a.get("slug") for a in curent}
    lipsa = {s: u for s, u in tinta.items() if s not in prezente}
    print(f"tinte din export : {len(tinta)}")
    print(f"deja in stare    : {len(tinta) - len(lipsa)}")
    print(f"de recuperat     : {len(lipsa)}")
    if not lipsa:
        return 0

    refs = subprocess.run(
        ["git", "log", "--format=%H", f"--since={ZILE_ISTORIC} days ago", "--", "data/articles.json"],
        capture_output=True, text=True, cwd=ROOT).stdout.split()
    print(f"commituri scanate: {len(refs)}")

    gasit = {}
    for ref in refs:
        if len(gasit) == len(lipsa):
            break
        arts = _incarca(ref)
        if not arts:
            continue
        for a in arts:
            s = a.get("slug")
            if s in lipsa and s not in gasit:
                gasit[s] = a

    # Un articol peste TTL ar fi sters de prima rulare, deci recuperarea lui ar fi zgomot.
    prag = datetime.now(timezone.utc) - timedelta(days=_ttl())
    utile, expirate = [], 0
    for a in gasit.values():
        t = _data(a)
        if t and t >= prag:
            utile.append(a)
        else:
            expirate += 1

    print(f"gasite in istoric: {len(gasit)}")
    print(f"  peste TTL (sar): {expirate}")
    print(f"  DE ADAUGAT     : {len(utile)}")
    negasite = len(lipsa) - len(gasit)
    if negasite:
        print(f"  negasite       : {negasite} (mai vechi de {ZILE_ISTORIC} zile in istoric)")

    if not utile:
        return 0
    if not scrie:
        print("\n(doar raport — adauga --scrie ca sa modifice data/articles.json)")
        return 0

    # Cheia de unicitate e URL-ul, ca in state.merge(); slug-ul e doar calea publica.
    dupa_url = {a.get("url"): a for a in curent if a.get("url")}
    adaugate = 0
    for a in utile:
        if a.get("url") and a["url"] not in dupa_url:
            dupa_url[a["url"]] = a
            adaugate += 1
    rezultat = list(dupa_url.values())
    with io.open(STARE, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rezultat, fh, ensure_ascii=False, indent=2)
    print(f"\nSCRIS: {len(curent)} -> {len(rezultat)} articole (+{adaugate})")
    return 0


def _ttl() -> int:
    sys.path.insert(0, ROOT)
    from generator import config
    return config.ARTICLE_TTL_DAYS


if __name__ == "__main__":
    raise SystemExit(main())
