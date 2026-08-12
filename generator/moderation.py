"""Om in bucla: aplica moderation.yaml peste lista de articole.

Fisierul lipsa = configurare goala (nicio filtrare). Toleranta deliberat.
"""
import os

import yaml

from . import config, guard
from .util import normalize_url

MOD_PATH = os.path.join(config.ROOT, "moderation.yaml")

DEFAULTS = {
    "blocklist_urls": [],
    "blocklist_keywords": [],
    "suppress_sources": [],
    "corrections": {},
    "featured": [],
    "hold_important": False,
}


def load() -> dict:
    mod = dict(DEFAULTS)
    if os.path.exists(MOD_PATH):
        try:
            with open(MOD_PATH, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            for key in DEFAULTS:
                if key in data and data[key] is not None:
                    mod[key] = data[key]
        except (yaml.YAMLError, OSError):
            pass
    return mod


def apply(articles: list, mod: dict) -> list:
    block_urls = {normalize_url(u) for u in mod["blocklist_urls"]}
    keywords = [k.lower() for k in mod["blocklist_keywords"]]
    suppress = set(mod["suppress_sources"])
    corrections = {normalize_url(u): c for u, c in mod["corrections"].items()}
    featured = {normalize_url(u) for u in mod["featured"]}

    out = []
    for a in articles:
        url = a.get("url", "")
        if url in block_urls or a.get("source") in suppress:
            continue
        # Garda de continut, a doua oara. Nu e redundanta cu cea din `fetch.py`: aici trec si
        # articolele DEJA din `articles.json`, ingerate inainte ca garda sa existe sau printr-o
        # versiune mai slaba a ei. `render_only()` chema `apply()` la FIECARE build, deci asta
        # e singurul punct prin care curatarea ajunge pe site fara sa astepte un fetch nou.
        motiv = (guard.verdict(a.get("title") or "",
                               a.get("teaser") or a.get("synthesis") or a.get("description") or "")
                 or guard.url_ostil(a.get("original_link") or "")
                 or next((m for s in (a.get("sources") or [])
                          if (m := guard.url_ostil(s.get("url") or ""))), None)
                 # Anomalia de limba se judeca pe titlul ORIGINAL, nu pe cel de pe site: la
                 # articolele trecute prin AI titlul e deja rescris in romana, deci ar scapa
                 # mereu. Pentru alea `original_title` lipseste (`_scrub_processed` il sterge),
                 # deci cade pe `title` si stratul tace — conservator, si exact ce trebuie:
                 # anunturile de primarie, singurele care conteaza aici, NU trec prin AI si isi
                 # pastreaza titlul brut. Masurat pe corpus: 3 din 3130, toate trei ostile.
                 or guard.anomalie(a.get("original_title") or a.get("title") or "",
                                   a.get("source_lang") or "ro"))
        if motiv:
            print(f"   !! garda moderare: ascund {(a.get('title') or '')[:60]!r} — {motiv}")
            continue
        title_l = (a.get("title", "") + " " + a.get("original_title", "")).lower()
        if any(kw in title_l for kw in keywords):
            continue
        if url in corrections:
            for field in ("title", "teaser", "synthesis"):
                if field in corrections[url]:
                    a[field] = corrections[url][field]
        a["featured"] = url in featured
        out.append(a)
    return out
