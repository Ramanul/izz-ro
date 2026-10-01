#!/usr/bin/env python3
"""Monthly SEO-TTL report: expired izz.ro URL cohorts extracted from git history.

Compares data/articles.json at an old origin/main commit (default: 30 days ago)
against current origin/main. Site URLs present then and absent now are "expired";
they are grouped into age cohorts by publish date so the site owner can check
them in Search Console (impressions, clicks, avg. position).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTICLES_IN_REPO = "data/articles.json"
SITE_BASE_URL = "https://izz.ro/"
DEFAULT_DAYS = 30
MAX_EXAMPLE_URLS = 20

COHORT_21_60 = "21-60 zile"
COHORT_61_PLUS = "61+ zile"
COHORT_LE_20 = "sub 21 zile"
COHORT_UNKNOWN = "fara data parsabila"
ALL_COHORTS = (COHORT_21_60, COHORT_61_PLUS, COHORT_LE_20, COHORT_UNKNOWN)


def run_git(args: list[str]) -> subprocess.CompletedProcess:
    """Run a read-only git command inside the repository root."""
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def fail(message: str) -> NoReturn:
    """Print a clear error and exit with status 1 (no traceback)."""
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def resolve_old_commit(days: int) -> str:
    """Return the last origin/main commit before `days` days ago."""
    result = run_git(["rev-list", "-1", f"--before={days} days ago", "origin/main"])
    if result.returncode != 0:
        fail(f"git rev-list failed: {result.stderr.strip()}")
    sha = result.stdout.strip()
    if not sha:
        fail(
            f"no commit found on origin/main before '{days} days ago'; history is "
            "shorter than the requested window. Re-run with a smaller --days."
        )
    return sha


def resolve_main_commit() -> str:
    """Return the current origin/main commit SHA."""
    result = run_git(["rev-parse", "origin/main"])
    if result.returncode != 0:
        fail(
            "cannot resolve origin/main (run 'git fetch origin main' first): "
            f"{result.stderr.strip()}"
        )
    return result.stdout.strip()


def commit_date(commit: str) -> str:
    """Return the committer date (ISO 8601) of `commit`, or a placeholder."""
    result = run_git(["show", "-s", "--format=%cI", commit])
    if result.returncode != 0:
        return "unknown commit date"
    return result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "unknown commit date"


def load_articles_json(commit: str) -> tuple[list | None, str | None]:
    """Load data/articles.json at `commit`; returns (list, None) or (None, reason)."""
    result = run_git(["show", f"{commit}:{ARTICLES_IN_REPO}"])
    if result.returncode != 0:
        return None, f"cannot read {ARTICLES_IN_REPO} at {commit}: {result.stderr.strip()}"
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return None, f"{ARTICLES_IN_REPO} at {commit} is not valid JSON: {exc}"
    if not isinstance(data, list):
        return None, (
            f"{ARTICLES_IN_REPO} at {commit} has an unexpected format: top-level "
            f"{type(data).__name__}, expected a list of articles"
        )
    return data, None


def parse_published(value: object) -> dt.date | None:
    """Tolerantly parse a published timestamp into a date; None if unparseable."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    candidates = [text]
    if text.endswith(("Z", "z")):
        candidates.append(text[:-1] + "+00:00")
    for candidate in candidates:
        try:
            return dt.datetime.fromisoformat(candidate).date()
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%d %b %Y"):
        try:
            # fara %z in formate: publicarile site-ului sunt UTC, deci naive = UTC
            return dt.datetime.strptime(text, fmt).replace(tzinfo=dt.timezone.utc).date()
        except ValueError:
            continue
    return None


def extract_site_articles(raw_articles: list) -> tuple[dict[str, dict], int]:
    """Map site URL -> {published: date|None}; skip malformed items, count them."""
    records: dict[str, dict] = {}
    malformed = 0
    for item in raw_articles:
        if not isinstance(item, dict):
            malformed += 1
            continue
        category = item.get("category")
        slug = item.get("slug")
        if not (isinstance(category, str) and category.strip()) or not (
            isinstance(slug, str) and slug.strip()
        ):
            malformed += 1
            continue
        url = f"{SITE_BASE_URL}{category.strip().strip('/')}/{slug.strip().strip('/')}/"
        records[url] = {"published": parse_published(item.get("published"))}
    return records, malformed


def cohort_for(published: dt.date | None, today: dt.date) -> str:
    """Assign an expired URL to its publish-age cohort."""
    if published is None:
        return COHORT_UNKNOWN
    age_days = (today - published).days
    if age_days <= 20:
        # Logically impossible for a real removal in a >=21-day window:
        # almost certainly a re-published article or a data quirk. Reported explicitly.
        return COHORT_LE_20
    if age_days <= 60:
        return COHORT_21_60
    return COHORT_61_PLUS


def cohort_section(title: str, subtitle: str, items: list[tuple[dt.date | None, str]]) -> list[str]:
    """Render one markdown section for a cohort, with capped example URLs."""
    lines = [f"## {title} — {len(items)} URL-uri", ""]
    if subtitle:
        lines += [subtitle, ""]
    if not items:
        lines += ["Niciun URL în această cohortă.", ""]
        return lines
    shown = items[:MAX_EXAMPLE_URLS]
    lines += [f"Exemple (primele {len(shown)} din {len(items)}):", ""]
    for published, url in shown:
        when = published.isoformat() if published else "dată lipsă"
        lines.append(f"- {url} (publicat {when})")
    lines.append("")
    return lines


def build_report(
    *,
    days: int,
    old_commit: str,
    old_commit_date: str,
    main_commit: str,
    main_commit_date: str,
    today: dt.date,
    old_entry_count: int,
    old_malformed: int,
    old_url_count: int,
    main_entry_count: int,
    main_malformed: int,
    main_url_count: int,
    cohorts: dict[str, list[tuple[dt.date | None, str]]],
) -> str:
    """Render the full markdown report (Romanian, for the site owner)."""
    expired_total = sum(len(items) for items in cohorts.values())
    cohort_start = today - dt.timedelta(days=60)
    cohort_end = today - dt.timedelta(days=21)
    lines: list[str] = []
    add = lines.append

    add("# Raport SEO-TTL — cohortă URL expirate (izz.ro)")
    add("")
    add(
        "URL-uri de site prezente în snapshot-ul vechi și absente din `origin/main` acum — "
        "de verificate lunar în Search Console (impressions / clicks / avg. position)."
    )
    add("")
    add(f"- Generat: {today.isoformat()}")
    add(f"- Fereastră: {days} zile")
    add(f"- Comit vechi: `{old_commit[:12]}` ({old_commit_date})")
    add(f"- Comit curent (origin/main): `{main_commit[:12]}` ({main_commit_date})")
    add(f"- URL construit ca `{SITE_BASE_URL}{{category}}/{{slug}}/`")
    add(f"- Comandă: `python tools/seottl_raport.py --days {days}`")
    add("")
    add("## Contoare")
    add("")
    add("| Metrică | Valoare |")
    add("|---|---|")
    add(f"| Intrări în `articles.json` la comitul vechi | {old_entry_count} |")
    add(f"| Din ele cu format invalid (fără category/slug valide) | {old_malformed} |")
    add(f"| URL-uri unice de site în vechi | {old_url_count} |")
    add(f"| Intrări în `articles.json` în main acum | {main_entry_count} |")
    add(f"| Din ele cu format invalid | {main_malformed} |")
    add(f"| URL-uri unice de site în main acum | {main_url_count} |")
    add(f"| **URL-uri expirate (în vechi, absente acum)** | **{expired_total}** |")
    add("")
    add("## Cohorte, pe vârsta publicării (azi − published)")
    add("")
    for name in ALL_COHORTS:
        add(f"- {name}: **{len(cohorts[name])}** URL-uri")
    add("")

    lines += cohort_section(
        "Cohorta 21–60 zile",
        f"Publicate între {cohort_start.isoformat()} și {cohort_end.isoformat()} inclusiv. "
        "Acestea sunt cele mai proaspete scoateri — traficul rezidual e așteptat să scadă treptat.",
        sorted(cohorts[COHORT_21_60], key=lambda pair: (pair[0] or dt.date.min, pair[1])),
    )
    lines += cohort_section(
        "Cohorta 61+ zile",
        f"Publicate înainte de {cohort_start.isoformat()}. Vechi de peste două luni — dacă mai "
        "aduc impressions, e semnal că merită redirect, nu lăsare în 404.",
        sorted(cohorts[COHORT_61_PLUS], key=lambda pair: (pair[0] or dt.date.min, pair[1])),
    )
    lines += cohort_section(
        "Expirate sub 21 zile (neasteptat)",
        "Logic imposibil pentru o scoatere într-o fereastră de ≥21 zile: cel mai probabil "
        "articol re-publicat sau anomalie de date. De verificat manual dacă apar.",
        sorted(cohorts[COHORT_LE_20], key=lambda pair: (pair[0] or dt.date.min, pair[1])),
    )
    lines += cohort_section(
        "Expirate fără dată de publicare parsabilă",
        "Câmpul `published` lipsea sau n-a putut fi parsat — nu se pot cohorta pe vârstă.",
        sorted(cohorts[COHORT_UNKNOWN], key=lambda pair: pair[1]),
    )

    add("## Metodă și limite")
    add("")
    add("- Comparația e pe URL derivat din starea pipeline-ului (`data/articles.json`), nu din "
        "pagini publicate efectiv: dacă starea include articole intrate în pipeline dar "
        "nemoderate/nepublicate, ele apar și ele în listă — de filtrat la verificare.")
    add("- Un articol mutat în altă categorie apare ca „expirat” pe URL-ul vechi (și ca nou pe "
        "cel actual) — de verificat dacă URL-ul vechi face redirect.")
    add("- Vârsta se calculează la data generării raportului, nu la data scoaterii URL-ului.")
    add("")
    add("## Checklist Search Console — ce măsor lunar, per cohortă")
    add("")
    add("Pentru fiecare din cele două cohorte (21–60 zile, 61+ zile):")
    add("")
    add("1. Search Console → Performanță → Rezultate de căutare; interval: ultimele 28 de zile.")
    add("2. Filtru: **Pagină** → URI-uri de pagină; lipește URL-urile cohortei (în seri dacă "
        "lista e mare, sau folosește Export și procesează în spreadsheet).")
    add("3. Măsoară per cohortă: **Impressions** (de câte ori URL-ul a apărut în rezultate), "
        "**Clicks**, **Avg. position** (poziția medie; ≤10 = prima pagină).")
    add("4. Semnale de urmărit:")
    add("   - Impressions > 0 pe URL expirat: mai primește afișări — candidat la redirect 301.")
    add("   - Avg. position bună (prima pagină) pe URL expirat: pierdere reală de SEO — "
        "prioritate la redirect.")
    add("   - Clicks pe URL expirat: utilizatori ajung pe 404 — de corectat repede.")
    add("5. Compară cu raportul lunii trecute: scădere lentă de impressions = normal după "
        "scoatere (TTL); cădere bruscă = ceva s-a schimbat la indexare.")
    add("")
    add("Raportul se regenerează cu `python tools/seottl_raport.py` "
        "(`--days N` pentru altă fereastră, `--out DIR` pentru alt folder).")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Monthly SEO-TTL report: expired izz.ro URL cohorts from git history."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        metavar="DAYS",
        help="how many days back to take the old snapshot (default: %(default)s)",
    )
    parser.add_argument(
        "--out",
        default="notes",
        metavar="DIR",
        help="output directory for the report, relative to the repo root (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    if args.days < 1:
        fail("--days must be a positive integer")

    old_commit = resolve_old_commit(args.days)
    main_commit = resolve_main_commit()
    old_commit_date = commit_date(old_commit)
    main_commit_date = commit_date(main_commit)

    old_raw, old_error = load_articles_json(old_commit)
    if old_raw is None:
        fail(f"cannot build report: {old_error}")
    main_raw, main_error = load_articles_json(main_commit)
    if main_raw is None:
        fail(f"cannot build report: {main_error}")

    today = dt.datetime.now(tz=dt.timezone.utc).date()
    old_articles, old_malformed = extract_site_articles(old_raw)
    main_articles, main_malformed = extract_site_articles(main_raw)

    cohorts: dict[str, list[tuple[dt.date | None, str]]] = {name: [] for name in ALL_COHORTS}
    for url in sorted(set(old_articles) - set(main_articles)):
        cohorts[cohort_for(old_articles[url]["published"], today)].append(
            (old_articles[url]["published"], url)
        )

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"seottl-cohorte-{today.isoformat()}.md"
    if out_path.exists():
        fail(f"refusing to overwrite an existing report: {out_path}")

    report = build_report(
        days=args.days,
        old_commit=old_commit,
        old_commit_date=old_commit_date,
        main_commit=main_commit,
        main_commit_date=main_commit_date,
        today=today,
        old_entry_count=len(old_raw),
        old_malformed=old_malformed,
        old_url_count=len(old_articles),
        main_entry_count=len(main_raw),
        main_malformed=main_malformed,
        main_url_count=len(main_articles),
        cohorts=cohorts,
    )
    out_path.write_text(report, encoding="utf-8")

    print(f"Report written: {out_path}")
    print(
        f"Expired URLs: {sum(len(c) for c in cohorts.values())} "
        f"({len(cohorts[COHORT_21_60])} in 21-60 d, {len(cohorts[COHORT_61_PLUS])} in 61+ d, "
        f"{len(cohorts[COHORT_LE_20])} unexpected <=20 d, "
        f"{len(cohorts[COHORT_UNKNOWN])} without parseable date)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
