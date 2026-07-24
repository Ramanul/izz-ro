import csv
import os
import re


# Potrivire pe CUVANT INTREG, nu substring: "ORASTIOARA DE SUS" e o COMUNA, dar contine
# "ORAS" -- cu `in` era clasificata gresit ca oras (bug real, prins la review 2026-07-24).
# `MUNICIPIUL?` accepta si forma fara -L, ca o scriere diferita in CSV sa nu cada tacut la comuna.
_MUNICIPIU_RE = re.compile(r"\bMUNICIPIUL?\b")
_ORAS_RE = re.compile(r"\bORA[SȘ](UL)?\b")


def _impact_tier(localitate: str) -> int:
    """Prioritate de IMPACT, dedusa STATIC din numele localitatii (nu re-analiza la runtime):
    municipiu (oras mare) inaintea orasului, orasul inaintea comunei. Reper cheie: un primar
    de municipiu are zeci de mii de cititori vs. o comuna de cateva sute -> incarcam intai
    localitatile mari, apoi comunele pentru acoperire. Marile resedinte de judet (Cluj, Iasi...)
    lipsesc din lista GOLD -- site-urile lor n-au RSS -- deci municipiile sunt varful disponibil."""
    loc = localitate.upper()
    if _MUNICIPIU_RE.search(loc):
        return 0
    if _ORAS_RE.search(loc):
        return 1
    return 2  # comuna


def _make_slug(judet: str, localitate: str) -> str:
    raw = f"{judet}_{localitate}".lower()
    slug = re.sub(r"[^a-z0-9]", "_", raw)
    slug = re.sub(r"_+", "_", slug)
    slug = slug.strip("_")
    return slug


def load_gold_sources(csv_path: str, limit: int, min_date: str = "2026-01-01") -> dict:
    if limit <= 0:
        return {}
    if not os.path.isfile(csv_path):
        return {}

    rows = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rss_url = (row.get("rss_url") or "").strip()
            if row.get("rss_ok") == "yes" and rss_url:
                last_date = (row.get("last_signal_date") or "").strip()
                if last_date and last_date >= min_date:
                    rows.append(row)

    # sortare STATICA in 2 pasi (sort stabil): intai prospetime desc, apoi nivel de impact asc.
    # Rezultat: municipiile cele mai active primele, apoi orasele, apoi comunele -> primele
    # `limit` sloturi merg la localitatile cu cel mai mare impact, nu la comune la intamplare.
    rows.sort(key=lambda r: (r["judet"], r["localitate"]))
    rows.sort(key=lambda r: r.get("last_signal_date") or "", reverse=True)
    rows.sort(key=lambda r: _impact_tier(r["localitate"]))

    result = {}
    for row in rows[:limit]:
        slug = _make_slug(row["judet"], row["localitate"])
        key = "pl_" + slug
        if key not in result:
            result[key] = {
                "name": "Primăria " + row["localitate"].title(),
                "url": row["rss_url"].strip(),
                "category": "local",
            }

    return result
