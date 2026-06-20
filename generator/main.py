"""Orchestrare pipeline: fetch -> state -> cluster -> AI (B/C) -> moderation -> [render].

  python -m generator.main            # rulare completa (salveaza starea, randeaza)
  python -m generator.main --dry-run  # afiseaza rezultatul, NU salveaza, NU randeaza
"""
import argparse
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from . import fetch, state, cluster, moderation
from .process import get_provider, process_single, process_cluster


def _utf8_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def process_new(new_items: list, provider) -> tuple[list, set]:
    """Returneaza (articole_procesate, url_uri_inglobate_in_cluster_C)."""
    groups = cluster.cluster(new_items)
    clustered = {a["url"] for g in groups for a in g}
    processed, folded = [], set()

    for g in groups:
        if len(g) > 1 and cluster.is_synthesis_candidate(g):
            rep = process_cluster(g, provider)
            processed.append(rep)
            folded.update(a["url"] for a in g if a["url"] != rep["url"])
        else:
            for it in g:
                processed.append(process_single(it, provider))

    # articole noi care nu au intrat in clustering (ex. mai vechi de 24h) -> model B
    for it in new_items:
        if it["url"] not in clustered:
            processed.append(process_single(it, provider))
    return processed, folded


def run(dry_run: bool = False) -> dict:
    _utf8_stdout()
    raw, dead = fetch.fetch_all()
    existing = state.load()
    known = {a.get("url") for a in existing}
    new_items = [i for i in raw if i["url"] not in known]

    provider = get_provider()
    provider_name = provider.name if provider else "fallback (fara cheie/SDK AI)"

    processed_new, folded = process_new(new_items, provider)
    combined = [a for a in (existing + processed_new) if a.get("url") not in folded]
    combined = state.expire(combined)

    mod = moderation.load()
    visible = moderation.apply(combined, mod)

    stats = {
        "fetched": len(raw),
        "dead_sources": dead,
        "new": len(new_items),
        "model_B": sum(1 for a in processed_new if a.get("model") == "B"),
        "model_C": sum(1 for a in processed_new if a.get("model") == "C"),
        "total_known": len(combined),
        "visible_after_moderation": len(visible),
        "provider": provider_name,
        "hold_important": mod.get("hold_important", False),
    }

    _print_report(stats, processed_new, dry_run)

    if not dry_run:
        state.save(combined)
        try:
            from . import render
            render.build(visible, mod)
            print(">> Randare completa in output/")
        except ImportError:
            print(">> render.py inca neimplementat (Faza 3) — sar peste randare.")
    return stats


def _print_report(stats: dict, processed_new: list, dry_run: bool):
    mode = "DRY-RUN (nu salvez)" if dry_run else "RULARE COMPLETA"
    print(f"\n=== IZZ.ro pipeline — {mode} ===")
    print(f"Provider AI: {stats['provider']}")
    print(f"Articole citite: {stats['fetched']} | noi: {stats['new']} | "
          f"B: {stats['model_B']} | C: {stats['model_C']}")
    print(f"Total cunoscute (dupa expirare): {stats['total_known']} | "
          f"vizibile dupa moderare: {stats['visible_after_moderation']}")
    if stats["hold_important"]:
        print("hold_important=true -> clusterele C asteapta aprobare (de tratat la randare).")
    if stats["dead_sources"]:
        print("\n!! Surse RSS care NU au raspuns (de verificat URL-ul in config.py):")
        for d in stats["dead_sources"]:
            print(f"   - {d}")
    print("\n--- Mostra articole noi procesate ---")
    for a in processed_new[:12]:
        body = a.get("teaser") if a.get("model") == "B" else a.get("synthesis")
        wc = len((body or "").split())
        print(f"[{a.get('model')}] ({a.get('source_name')}) {a.get('title')}")
        print(f"      {body}  [{wc} cuvinte]")
        if a.get("model") == "C":
            print(f"      surse: {', '.join(s['name'] for s in a.get('sources', []))}")


def main():
    parser = argparse.ArgumentParser(description="IZZ.ro static site generator")
    parser.add_argument("--dry-run", action="store_true",
                        help="ruleaza pipeline-ul fara a salva starea sau a randa")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
