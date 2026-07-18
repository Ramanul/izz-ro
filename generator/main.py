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


def process_new(new_items: list, provider, budget: int, existing: list | None = None) -> tuple[list, set, int]:
    """Returneaza (articole_procesate, url_uri_inglobate_in_cluster_C, apeluri_AI_folosite).

    `budget` = numarul de APELURI AI (free-tier are limita). Model B se proceseaza in
    LOTURI de config.BATCH_SIZE (1 apel/lot) -> de ~BATCH_SIZE ori mai putine requesturi.
    Clusterele C (1 apel fiecare) au prioritate. Ce nu intra in buget e reluat la rularea urmatoare.

    Clustering CROSS-RUN: itemele noi se grupeaza IMPREUNA cu stirile B recente din
    state (`existing`) -- doua surse care relateaza acelasi eveniment la ~20-30 min
    distanta cad in rulari diferite si altfel ar aparea ca stiri duplicate separate.
    Doar clusterele atinse de items NOI consuma AI; stirea B absorbita e inlocuita de
    sinteza C (prin `folded` + inlocuirea pe URL in run()).
    """
    used = 0
    new_urls = {i["url"] for i in new_items}
    recent_b = [a for a in (existing or [])
                if a.get("model") == "B" and a.get("url") not in new_urls]

    groups = cluster.cluster(new_items)
    groups = cluster.attach_recent(groups, recent_b)
    clustered = {a["url"] for g in groups for a in g}
    processed, folded = [], set()

    syn = [g for g in groups if len(g) > 1 and cluster.is_synthesis_candidate(g)
           and any(a["url"] in new_urls for a in g)]
    singles = [it for g in groups if g not in syn for it in g if it["url"] in new_urls]
    singles += [it for it in new_items if it["url"] not in clustered]

    # clusterele C intai (1 apel fiecare)
    for g in syn:
        if used >= budget:
            break
        rep = process_cluster(g, provider)
        used += 1
        if rep is None:
            continue  # esec AI -> cluster amanat; membrii raman nefolded si se reiau data viitoare
        processed.append(rep)
        folded.update(a["url"] for a in g if a["url"] != rep["url"])

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
    Le modifica pe loc. Returneaza upgrade-urile reusite. (C nu se reproceseaza — nu avem grupul.)
    Pe primul esec AI (quota/eroare) se opreste runda, ca sa nu lovim un API indisponibil.
    """
    if not provider or remaining <= 0:
        return 0
    used = 0
    for a in articles:
        if used >= remaining:
            break
        if a.get("model") == "B" and a.get("original_title") and (
            a.get("processed_by") == "fallback"
            or a.get("prompt_version") != config.PROMPT_VERSION
        ):
            if process_single(a, provider) is None:
                break  # AI indisponibil -> oprim upgrade-ul; fallback-urile raman pentru data viitoare
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
    processed_new, folded, used = process_new(new_items, provider, budget - reserve, existing=existing)
    processed_new = [a for a in processed_new if not a.get("skip")]
    # inlocuire pe URL: un rep C poate purta URL-ul unei stiri B existente pe care a absorbit-o
    rep_urls = {a.get("url") for a in processed_new}
    combined = [a for a in existing
                if a.get("url") not in folded and a.get("url") not in rep_urls] + processed_new
    upgraded = upgrade_fallbacks(combined, provider, budget - used)
    combined = state.expire(combined)

    mod = moderation.load()
    visible = moderation.apply(combined, mod)

    # Cadere AI SISTEMICA: providerul exista, s-au incercat apeluri si TOATE au esuat
    # (model retras -> 404, cheie/quota moarta). Distinct de "n-a fost nimic nou"
    # (calls == 0) si de un 429 tranzitoriu partial (failures < calls). Vezi providers/base.py.
    ai_down = bool(provider) and provider.calls > 0 and provider.failures >= provider.calls

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
        "ai_down": ai_down,
        "ai_calls": provider.calls if provider else 0,
        "ai_last_error": provider.last_error if provider else None,
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
    if stats.get("ai_down"):
        print("\n" + "=" * 64)
        print(f"!! AI DOWN — toate cele {stats.get('ai_calls', 0)} apeluri AI au esuat. "
              "NIMIC nou publicat.")
        print(f"   Ultima eroare: {stats.get('ai_last_error')}")
        print("   Cauze probabile: model retras (404), cheie invalida sau quota epuizata.")
        print("   Verifica GEMINI_MODEL / GEMINI_API_KEY. Site-ul ramane pe ultima stare buna.")
        print("=" * 64)
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
        stats = run(dry_run=args.dry_run)
        # Cadere AI sistemica -> exit non-zero: in CI (build.yml) pasul pipeline nu e
        # continue-on-error, deci jobul devine ROSU (owner notificat) si pasul de commit
        # e sarit -> Cloudflare NU redeployeaza, site-ul ramane pe ultima stare buna.
        if stats and stats.get("ai_down"):
            sys.exit(1)


if __name__ == "__main__":
    main()
