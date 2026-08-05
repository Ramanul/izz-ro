"""Orchestrare pipeline: fetch -> state -> cluster -> AI (B/C) -> moderation -> [render].

  python -m generator.main            # rulare completa (salveaza starea, randeaza)
  python -m generator.main --dry-run  # afiseaza rezultatul, NU salveaza, NU randeaza
"""
import argparse
import hashlib
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from . import fetch, state, cluster, moderation, config
from .process import get_provider, process_single, process_cluster, process_batch, process_official, OFFICIAL_PREFIXES
from .util import domain_of


def _utf8_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def _tie(url: str) -> str:
    """Departajare la scor egal. Fara ea, `sort` fiind stabil, egalitatile ar cadea inapoi
    pe ordinea de intrare — adica exact ordinea din config.SOURCES pe care o inlocuim aici.
    Nu e o ipoteza teoretica: sursele cu data fara ora (`_parse_w3c_date` pe sitemap news,
    `_parse_ro_date`) primesc toate miezul noptii UTC, deci egalitatile sunt sistematice
    exact acolo. Amprenta URL-ului e stabila intre rulari si necorelata cu sursa."""
    return hashlib.md5((url or "").encode("utf-8")).hexdigest()


def _cluster_rank(group: list) -> tuple:
    """Cheia de prioritate a unui cluster fata de bugetul AI: (domenii distincte, cel mai
    proaspat membru, departajare). Doua surse independente care relateaza acelasi lucru
    sunt un semnal de eveniment real, nu de sablon — de aia coroborarea vine inaintea
    prospetimii. `published` e ISO 8601 UTC pentru toate caile de ingestie (fetch.py),
    deci se compara ca sir fara conversie."""
    domains = {domain_of(a.get("original_link", "")) for a in group}
    newest = max((a.get("published") or "") for a in group)
    return (len(domains), newest, _tie(min(a.get("url", "") for a in group)))


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

    Sursele oficiale (pl_/cj_/pr_) sunt procesate determinist, fara AI budget.
    """
    used = 0
    official = [i for i in new_items if str(i.get("source", "")).startswith(OFFICIAL_PREFIXES)]
    new_items = [i for i in new_items if i not in official]

    # Itemele fara substanta nu ajung la AI. Se opresc AICI, inainte de clustering si inainte de
    # buget, din doua motive: (1) nu exista nimic de sintetizat, deci apelul ar produce o
    # parafraza a titlului — vezi `specs/sinteza-fara-substanta.md`; (2) bugetul e ~10 apeluri pe
    # rulare si era ars pe ele. Sursele oficiale sunt deja scoase mai sus si nu sunt atinse.
    # `src_extra` lipseste doar pe iteme construite in teste vechi; acolo nu presupunem nimic.
    fara_substanta = [i for i in new_items
                      if i.get("src_extra") is not None
                      and i["src_extra"] < config.MIN_SUBSTANTA_CUVINTE]
    if fara_substanta:
        surse = sorted({str(i.get("source")) for i in fara_substanta})
        print(f">> Fara substanta (sub {config.MIN_SUBSTANTA_CUVINTE} cuvinte peste titlu), "
              f"NEtrimise la AI: {len(fara_substanta)} iteme din {len(surse)} surse: "
              f"{', '.join(surse)}")
        new_items = [i for i in new_items if i not in fara_substanta]
    new_urls = {i["url"] for i in new_items}
    # Candidatii cross-run sunt TOATE stirile recente din stare, nu doar cele model B.
    # Filtrul `model == "B"` de aici insemna ca o sinteza deja publicata nu putea absorbi o
    # stire noua despre acelasi eveniment: se forma un cluster nou si se publica A DOUA sinteza
    # langa prima. Masurat pe arhiva de 7443 articole (2026-08-05): din 623 de perechi duplicate
    # (aceeasi rubrica, <=6h, Jaccard>=0.5), 328 — 53% — contin o sinteza C, si TOATE trec
    # pragul `_strict_match`, deci s-ar fi unit daca ar fi fost eligibile. Decizia IZZ-0151:
    # sinteza se ACTUALIZEAZA, la acelasi slug. Pragul de potrivire NU se atinge; se schimba
    # doar cine e eligibil, deci profilul de over-merge ramane cel deja calibrat.
    recent_publicate = [a for a in (existing or []) if a.get("url") not in new_urls]

    groups = cluster.cluster(new_items)
    groups = cluster.attach_recent(groups, recent_publicate)
    clustered = {a["url"] for g in groups for a in g}
    processed, folded = [], set()

    syn = [g for g in groups if len(g) > 1 and cluster.is_synthesis_candidate(g)
           and any(a["url"] in new_urls for a in g)]
    singles = [it for g in groups if g not in syn for it in g if it["url"] in new_urls]
    singles += [it for it in new_items if it["url"] not in clustered]

    # ORDINEA in care se consuma bugetul. Implicit era ordinea din config.SOURCES
    # (fetch.py o pastreaza deliberat), dar bugetul se satureaza la fiecare rulare —
    # ~250 de iteme noi pentru ~10 apeluri — deci pozitia in config decidea ce se
    # publica: sursele din capul listei mereu, cele de la coada niciodata. Doua
    # criterii neutre, calculabile fara AI: coroborarea (domenii distincte) si
    # prospetimea. Vezi specs/ai-budget-ordering.md.
    syn.sort(key=_cluster_rank, reverse=True)
    singles.sort(key=lambda a: (a.get("published") or "", _tie(a.get("url", ""))), reverse=True)

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

    if official:
        processed.extend(process_official(official))

    return processed, folded, used


def upgradable(articles: list) -> list:
    """Articolele pe care `upgrade_fallbacks` chiar le-ar reprocesa, in ordinea lor.

    Predicat SINGUR, folosit si de `upgrade_fallbacks` si de `ai_reserve`. Scris o data
    dinadins: rezerva de buget e utila doar daca numara exact ce va consuma upgrade-ul.
    Doua copii ale conditiei ar putea sa se departeze fara ca nimic sa para stricat —
    rezerva ar tine deoparte apeluri pentru o coada care nu exista, exact defectul reparat
    aici, doar ca mai greu de vazut."""
    return [a for a in articles
            if a.get("model") == "B" and a.get("original_title") and (
                a.get("processed_by") == "fallback"
                or a.get("prompt_version") != config.PROMPT_VERSION)]


def ai_reserve(existing: list, budget: int) -> int:
    """Cate apeluri se tin deoparte din buget pentru `upgrade_fallbacks`.

    MASURAT 2026-08-03, pe trei rulari `build.yml` consecutive: `MAX_AI_CALLS_PER_RUN=18`
    si `UPGRADE_RESERVE=8` dadeau lui `process_new` doar 10 apeluri, iar rezerva de 8 nu se
    cheltuia NICIODATA (`ai_calls 10` in toate trei) — pentru ca starea nu contine niciun
    articol eligibil: 0 fallback-uri, 0 pe versiune veche de prompt, iar cele 233 de articole
    oficiale n-au `original_title`, deci nu califica prin constructie. In acelasi timp
    rularile amanau 20 / 27 / 127 de iteme noi din lipsa de buget. 44% din buget tinut pentru
    o coada goala.

    Rezerva NU e gresita prin design: un bump de `PROMPT_VERSION` face ~1100 de articole
    eligibile deodata, si atunci exact ea impiedica infometarea upgrade-urilor de catre
    fluxul continuu de stiri noi. Era gresita neconditionat. Acum e plafonata de cati sunt.

    Se numara pe `existing`, adica starea DINAINTE de procesare. Un articol care cade pe
    fallback chiar in rularea asta nu e numarat — dar daca a cazut, providerul tocmai a
    esuat, deci upgrade-ul lui ar esua si el; se ridica la rularea urmatoare, cand e in stare."""
    want = int(os.getenv("UPGRADE_RESERVE", "3"))
    return max(0, min(want, budget, len(upgradable(existing))))


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
    for a in upgradable(articles):
        if used >= remaining:
            break
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
    # Official feeds carry months-old entries, so most "new" items are already past the TTL
    # when read. Without this they burn AI budget and are deleted by the trailing expire()
    # in the SAME run — and worse, process_cluster picks the OLDEST member as representative,
    # so a stale item can absorb a FRESH article and take it down with it when it expires.
    # Same expire() as below, so the two cutoffs cannot drift. Undated items stay: _parse_iso
    # falls back to now(). Measurements are in the PR #108 description, not here — they age.
    fresh_items = state.expire(new_items)
    stale_skipped = len(new_items) - len(fresh_items)
    new_items = fresh_items

    provider = get_provider()
    provider_name = provider.name if provider else "fallback (fara cheie/SDK AI)"

    budget = int(os.getenv("MAX_AI_CALLS_PER_RUN", "12")) if provider else 10 ** 9
    # rezerva apeluri garantate pentru upgrade-ul fallback-urilor vechi, ca sa nu fie
    # infometate cand exista mereu articole noi (umplerea initiala) -- dar DOAR cat exista
    # de upgradat. Vezi `ai_reserve`: neplafonata, tinea 8 din 18 apeluri pentru o coada goala.
    pending_upgrades = len(upgradable(existing)) if provider else 0
    reserve = ai_reserve(existing, budget) if provider else 0
    processed_new, folded, used = process_new(new_items, provider, budget - reserve, existing=existing)
    # Cate iteme noi n-au primit AI in rularea asta. Nu se salveaza in state, deci revin
    # „noi” la rularea urmatoare — masura reala a presiunii pe buget, invizibila pana acum:
    # raportul spunea cate articole au IESIT, niciodata cate au fost lasate afara.
    handled = {a.get("url") for a in processed_new} | folded
    deferred = sum(1 for i in new_items if i["url"] not in handled)
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
        "stale_skipped": stale_skipped,
        "deferred": deferred,
        "model_B": sum(1 for a in processed_new if a.get("model") == "B"),
        "model_C": sum(1 for a in processed_new if a.get("model") == "C"),
        # Cate sinteze deja publicate s-au ACTUALIZAT in loc sa apara a doua oara (IZZ-0151).
        # `updated` e pus de `process_cluster` doar cand rep-ul e un membru deja publicat, iar
        # in `processed_new` nu intra decat ce s-a procesat ACUM — deci nu numara actualizari vechi.
        "sinteze_actualizate": sum(1 for a in processed_new if a.get("updated")),
        "total_known": len(combined),
        "visible_after_moderation": len(visible),
        "provider": provider_name,
        "upgraded_fallbacks": upgraded,
        "hold_important": mod.get("hold_important", False),
        "ai_down": ai_down,
        "ai_calls": provider.calls if provider else 0,
        "ai_budget": budget if provider else 0,
        # Cat s-a tinut deoparte pentru upgrade-uri si cati candidati existau. Fara ele,
        # „ai_calls 10" dintr-un log nu se poate citi fara sa incrucisezi doua variabile de
        # mediu cu starea — a costat o sesiune intreaga sa se observe ca rezerva era moarta.
        "upgrade_reserve": reserve,
        "upgradable": pending_upgrades,
        "ai_last_error": provider.last_error if provider else None,
    }
    if upgraded:
        print(f">> Upgrade fallback -> AI: {upgraded} articole vechi reprocesate")

    _print_report(stats, processed_new, dry_run)

    if not dry_run:
        try:
            from . import render
        except ImportError:
            render = None
        if render is not None:
            # INAINTE de save, dinadins: slug-ul e permalink-ul public si trebuie sa intre in
            # stare, ca sa nu se recalculeze din titlu la fiecare randare. Titlul se schimba
            # dupa publicare (upgrade de PROMPT_VERSION, sinteza care absoarbe o stire noua —
            # IZZ-0151); slug-ul nu are voie. Vezi render.assign_slugs.
            render.assign_slugs(visible)
        state.save(combined)
        if render is not None:
            render.build(visible, mod)
            print(">> Randare completa in output/")
        else:
            print(">> render.py inca neimplementat (Faza 3) — sar peste randare.")
    return stats


def _print_report(stats: dict, processed_new: list, dry_run: bool):
    mode = "DRY-RUN (nu salvez)" if dry_run else "RULARE COMPLETA"
    print(f"\n=== IZZ.ro pipeline — {mode} ===")
    print(f"Provider AI: {stats['provider']}")
    print(f"Articole citite: {stats['fetched']} | noi: {stats['new']} | "
          f"B: {stats['model_B']} | C: {stats['model_C']}")
    if stats.get("sinteze_actualizate"):
        print(f"Sinteze actualizate la acelasi permalink (in loc de duplicat): "
              f"{stats['sinteze_actualizate']}")
    if stats.get("stale_skipped"):
        print(f"Sarite ca deja expirate la citire: {stats['stale_skipped']} "
              f"(peste TTL de {config.ARTICLE_TTL_DAYS} zile — ar fi fost sterse in aceeasi rulare)")
    if stats.get("ai_budget"):
        print(f"Buget AI: {stats['ai_budget']} apeluri | pentru iteme noi: "
              f"{stats['ai_budget'] - stats['upgrade_reserve']} | rezervat upgrade: "
              f"{stats['upgrade_reserve']} din {stats['upgradable']} eligibile | "
              f"folosite: {stats['ai_calls']}")
    if stats.get("deferred"):
        print(f"Amanate (buget AI epuizat): {stats['deferred']} din {stats['new']} "
              f"— revin la rularea urmatoare, apeluri folosite: {stats['ai_calls']}")
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
