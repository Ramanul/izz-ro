"""Om in bucla: aplica moderation.yaml peste lista de articole.

Fisierul lipsa = configurare goala (nicio filtrare). Toleranta deliberat.
"""
import os

import yaml

from . import config
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
