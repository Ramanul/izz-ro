"""Orchestrare pipeline: fetch -> state -> cluster -> AI (B/C) -> moderation -> [render].

  python -m generator.main            # rulare completa (salveaza starea, randeaza)
  python -m generator.main --dry-run  # afiseaza rezultatul, NU salveaza, NU randeaza
"""
import argparse
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from . import fetch, state, cluster, moderation, config
from .process import get_provider, process_single, process_cluster, process_batch


def _utf8_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def process_new(new_items: list, provider, budget: int) -> tuple[list, set, int]:
    """Returneaza (articole_procesate, url_uri_inglobate_in_cluster_C, apeluri_AI_folosite).

    `budget` = numarul de APELURI AI (free-tier are limita). Model B se proceseaza in
    LOTURI de config.BATCH_SIZE (1 apel/lot) -> de ~BATCH_SIZE ori mai putine requesturi.
    Clusterele C (1 apel fiecare) au prioritate. Ce nu intra in buget e reluat la rularea urmatoare.
    """
    used = 0

    groups = cluster.cluster(new_items)
    clustered = {a["url"] for g in groups for a in g}
    processed, folded = [], set()

    syn = [g for g in groups if len(g) > 1 and cluster.is_synthesis_candidate(g)]
    singles = [it for g in groups if g not in syn for it in g]
    singles += [it for it in new_items if it["url"] not in clustered]

    # clusterele C intai (1 apel fiecare)
    for g in syn:
        if used >= budget:
            break
        rep = process_cluster(g, provider)
        processed.append(rep)
        folded.update(a["url"] for a in g if a["url"] != rep["url"])
        used += 1

    # model B in LOTURI (1 apel per BATCH_SIZE articole)
    bs = config.BATCH_SIZE if provider else (len(singles) or 1)
    for i in range(0, len(singles), bs):
        if used >= budget:
            break  # restul loturilor -> reluate la rularea urmatoare
        processed.extend(process_batch(singles[i:i + bs], provider))
        used += 1

    return processed, folded, used


def upgrade_fallbacks(articles: list, provider, remaining: int) -> int:
    """Reprocesează cu AI articolele B invechite, in limita bugetului ramas:
    - cele ramase pe fallback (quota), SI
    - cele procesate cu o versiune veche a regulilor (prompt_version != curent).
    Le modifica pe loc. Returneaza apelurile folosite. (C nu se reproceseaza — nu avem grupul.)
    """
    if not provider or remaining <= 0:
        return 0
    used = 0
    for a in articles:
        if used >= remaining:
            break
        if a.get("model") == "B" and (
            a.get("processed_by") == "fallback"
            or a.get("prompt_version") != config.PROMPT_VERSION
        ):
            process_single(a, provider)  # rescrie titlu/teaser/processed_by/prompt_version pe loc
            used += 1
    return used


def render_only() -> dict:
    """Doar randeaza starea deja salvata (data/articles.json) -> output/.

    Folosit de Cloudflare Pages: build rapid, fara fetch/AI/quota. Munca grea
    (fetch + AI + commit state) o face GitHub Actions; commit-ul declanseaza acest render.
    """
    _utf8_stdout()
    from . import render
    articles = state.load()
    mod = moderation.load()
    visible = moderation.apply(articles, mod)
    render.build(visible, mod)
    print(f">> Render-only: {len(visible)} articole din state -> output/")
    return {"rendered": len(visible)}


def run(dry_run: bool = False) -> dict:
    _utf8_stdout()
    raw, dead = fetch.fetch_all()
    existing = state.load()
    known = {a.get("url") for a in existing}
    new_items = [i for i in raw if i["url"] not in known]

    provider = get_provider()
    provider_name = provider.name if provider else "fallback (fara cheie/SDK AI)"

    budget = int(os.getenv("MAX_AI_CALLS_PER_RUN", "12")) if provider else 10 ** 9
    # rezerva cateva apeluri garantate pentru upgrade-ul fallback-urilor vechi,
    # ca sa nu fie infometate cand exista mereu articole noi (umplerea initiala)
    reserve = min(int(os.getenv("UPGRADE_RESERVE", "3")), budget) if provider else 0
    processed_new, folded, used = process_new(new_items, provider, budget - reserve)
    processed_new = [a for a in processed_new if not a.get("skip")]
    combined = [a for a in (existing + processed_new) if a.get("url") not in folded]
    upgraded = upgrade_fallbacks(combined, provider, budget - used)
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
        "upgraded_fallbacks": upgraded,
        "hold_important": mod.get("hold_important", False),
    }
    if upgraded:
        print(f">> Upgrade fallback -> AI: {upgraded} articole vechi reprocesate")

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
    parser.add_argument("--render-only", action="store_true",
                        help="doar randeaza starea salvata (pentru Cloudflare: fara fetch/AI)")
    args = parser.parse_args()
    if args.render_only:
        render_only()
    else:
        run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
