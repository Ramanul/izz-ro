"""Proba de structura: starea articles.json + distributia pe surse.

Read-only. Ruleaza cu:  py notes/story-intelligence/proba_structura.py
Data: 2026-10-01. Partea usoara a probei de clustering STORY:
ce contine real starea, cat de mare e, pe ce semnale se poate sprijini
un model de story (surse grupate, sinteze marcate).

Nu modifica nimic: doar citeste data/articles.json si printeaza masuratori.
"""

import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "articles.json"

NOW = datetime.now(timezone.utc)
DAY = timedelta(days=1)


def parse_published(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    print(f"NOW (run time, UTC): {NOW.isoformat()}")
    print(f"file: {DATA} ({DATA.stat().st_size:,} bytes)")

    # ---------- 1. Structura ----------
    print("\n=== 1. STRUCTURA ===")
    print(f"total articles: {len(data)}")

    field_presence = Counter()
    field_populated = Counter()
    field_types: dict[str, Counter] = defaultdict(Counter)
    for a in data:
        for k, v in a.items():
            field_presence[k] += 1
            if v is not None and v != "" and v != []:
                field_populated[k] += 1
            field_types[k][type(v).__name__] += 1

    print("field inventory (name | type(s) | present | populated non-empty):")
    for k in sorted(field_presence, key=lambda x: -field_presence[x]):
        types = ",".join(sorted(field_types[k]))
        print(f"  {k} | {types} | {field_presence[k]} | {field_populated[k]}")

    dates = [parse_published(a["published"]) for a in data]
    valid = [d for d in dates if d is not None]
    unparsable = len(dates) - len(valid)
    future = [d for d in valid if d > NOW]
    print(f"published parse errors: {unparsable}")
    print(f"published range: {min(valid).isoformat()} .. {max(valid).isoformat()}")
    print(f"future-dated articles (published > NOW): {len(future)}")

    # ---------- 2. Sinteza multi-sursa ----------
    print("\n=== 2. SINTEZA MULTI-SURSA ===")
    searched = [
        "synthesis", "is_synthesis", "article_type", "type",
        "cluster", "related", "sources", "first_source", "model",
    ]
    print("fields searched vs what exists:")
    for f in searched:
        n = field_presence.get(f, 0)
        print(f"  {f}: {'ABSENT' if n == 0 else f'{n} articles carry it'}")

    set_model_c = {a["url"] for a in data if a.get("model") == "C"}
    set_syn_text = {a["url"] for a in data if a.get("synthesis")}
    set_sources = {a["url"] for a in data if a.get("sources") is not None}
    set_first_src = {a["url"] for a in data if a.get("first_source") is not None}
    print(f"model == 'C': {len(set_model_c)}")
    print(f"synthesis non-empty: {len(set_syn_text)}")
    print(f"sources (list) present: {len(set_sources)}")
    print(f"first_source present: {len(set_first_src)}")
    print(f"all four markers identical sets: "
          f"{set_model_c == set_syn_text == set_sources == set_first_src}")

    syn = [a for a in data if a.get("model") == "C"]
    refs = sum(len(a.get("sources") or []) for a in syn)
    urls_in_state = {a["url"] for a in data}
    resolved = sum(1 for a in syn for s in a.get("sources") or [] if s.get("url") in urls_in_state)
    per_syn = Counter(len(a.get("sources") or []) for a in syn)
    print(f"source refs listed inside syntheses: {refs} "
          f"(median per synthesis: {statistics.median([len(a.get('sources') or []) for a in syn])})")
    print(f"source refs resolving to a separate article in state: {resolved} / {refs}")
    print(f"sources-per-synthesis histogram: {dict(sorted(per_syn.items()))}")

    print("syntheses per day (published date, UTC; only days with >=1):")
    syn_by_day = Counter()
    for a in syn:
        d = parse_published(a["published"])
        if d and d <= NOW:
            syn_by_day[d.date()] += 1
    for day in sorted(syn_by_day):
        print(f"  {day.isoformat()}: {syn_by_day[day]}")
    recent14 = sum(n for day, n in syn_by_day.items() if NOW.date() - day <= timedelta(days=14))
    print(f"syntheses in last 14 days: {recent14}")

    # ---------- 3. Surse ----------
    print("\n=== 3. SURSE (ultimele 30 de zile) ===")
    win30_start = NOW - 30 * DAY
    win48_start = NOW - timedelta(hours=48)
    by_source_30 = Counter()
    by_source_48 = set()
    per_source_per_day: dict[str, Counter] = defaultdict(Counter)
    for a, d in zip(data, dates):
        if d is None or d > NOW or d < win30_start:
            continue
        src = a["source"]
        by_source_30[src] += 1
        per_source_per_day[src][d.date()] += 1
        if d >= win48_start:
            by_source_48.add(src)
    print(f"distinct sources with >=1 article in last 30 days: {len(by_source_30)}")
    print(f"distinct sources with >=1 article in last 48 hours: {len(by_source_48)}")

    days_in_state = sorted({d.date() for d in valid if d <= NOW})
    n_days = len(days_in_state)
    print(f"distinct calendar days covered by state (<= NOW): {n_days} "
          f"({days_in_state[0].isoformat()} .. {days_in_state[-1].isoformat()})")
    print("top 15 sources by volume in last 30 days "
          "(count | median/day over those calendar days, zero-days included):")
    names = {}
    for a in data:
        names.setdefault(a["source"], a.get("source_name", ""))
    for src, cnt in by_source_30.most_common(15):
        series = [per_source_per_day[src].get(day, 0) for day in days_in_state]
        med = statistics.median(series)
        print(f"  {src} ({names.get(src, '')}) | {cnt} | median {med}/day | max {max(series)}/day")

    # ---------- 4. Fereastra ----------
    print("\n=== 4. FEREASTRA (ultimele 14 zile) ===")
    win14_start = NOW - 14 * DAY
    in14 = sum(1 for d in valid if win14_start <= d <= NOW)
    in30 = sum(1 for d in valid if win30_start <= d <= NOW)
    print(f"articles with NOW-14d <= published <= NOW: {in14}")
    print(f"articles with NOW-30d <= published <= NOW: {in30}")
    print(f"(outside windows: {unparsable} unparsable, {len(future)} future-dated)")

    # ---------- 5. Geo / local ----------
    print("\n=== 5. GEO / LOCAL ===")
    geo_fields = [k for k in field_presence if any(t in k.lower() for t in
                  ("geo", "local", "county", "judet", "city", "place"))]
    print(f"dedicated geo-like top-level fields: {geo_fields or 'NONE'}")
    ec_total = sum(1 for a in data if a.get("event_chart"))
    ec_loc = sum(1 for a in data if (a.get("event_chart") or {}).get("localitate"))
    ec_tips = Counter((a.get("event_chart") or {}).get("tip") for a in data if a.get("event_chart"))
    print(f"event_chart present: {ec_total} (tips: {dict(ec_tips)})")
    print(f"event_chart.localitate populated: {ec_loc}")
    cat_local = sum(1 for a in data if a.get("category") in ("local", "judetean"))
    print(f"category in (local, judetean) - proxy, not a geo field: {cat_local}")
    pl_sources = {src for src in names if src.startswith("pl_")}
    pl_articles = sum(c for src, c in by_source_30.items() if src in pl_sources)
    print(f"sources with 'pl_' prefix (town halls proxy, [INTERPRETARE]): "
          f"{len(pl_sources)} sources, {pl_articles} articles in last 30 days")


if __name__ == "__main__":
    main()
