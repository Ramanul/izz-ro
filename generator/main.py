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

from . import fetch, state, cluster, moderation, config, guard
from .process import get_provider, process_single, process_clusters_batch, process_batch, process_official, OFFICIAL_PREFIXES
from .util import domain_of, titlu_e_doar_o_data
from .claude_orchestrator import ClaudeCodeValidator


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


def itemele_fara_substanta(items: list) -> list:
    """Itemele care nu ajung niciodata la AI fiindca n-au ce sintetiza.

    Predicat UNIC, deliberat: il foloseste si `process_new` (care le scoate din drum) si
    raportul de la finalul rularii (care nu are voie sa le numere ca „amanate"). Doua copii
    ale conditiei ar fi doua adevaruri care se desincronizeaza la prima schimbare de prag.
    """
    return [i for i in items
            if i.get("src_extra") is not None
            and i["src_extra"] < config.MIN_SUBSTANTA_CUVINTE]


def cadere_ai(provider) -> bool:
    """Rularea a fost lipsita de AI in mod SISTEMIC? Predicat separat, ca sa poata fi testat.

    Doua forme, amandoua sistemice. Distinct de „n-a fost nimic nou" (`calls == 0`) si de un 429
    tranzitoriu partial (`failures < calls`). Vezi providers/base.py.

    (a) `provider is None` — providerul LIPSESTE cu totul. `get_provider()` intoarce None cand
        niciun provider nu e `available()`: cheie stearsa, expirata sau invalida (in CI Ollama
        nu ruleaza, deci cascada se reduce la cloud). **Pana la 2026-08-20 conditia incepea cu
        `bool(provider)`, deci forma asta nu aprindea nimic** — rularea reusea, comitea si
        publica, fara niciun semnal rosu. Esecul mai grav era singurul nedetectat.
        Consecinta nu era doar „titluri de sursa in loc de sinteze": pe reprezentantii DEJA
        PUBLICATI, `process.py` pastreaza titlul si sinteza scrise de model (textul original e
        sters de `state._scrub_processed`), deci se republica text de AI. Vezi
        `specs/audit-izz-20260820/11-conformitate-editoriala.md`, [C1] si [C3].
    (b) providerul exista, s-au incercat apeluri si TOATE au esuat (model retras -> 404,
        cheie/quota moarta).
    """
    if provider is None:
        return True
    return provider.calls > 0 and provider.failures >= provider.calls


def cauza_amanarii(ai_calls: int, ai_budget: int, upgrade_reserve: int) -> str:
    """Eticheta cauzei, DEDUSA din cifre — raportul nu mai are voie s-o afirme.

    Plafonul comparat e `ai_budget - upgrade_reserve`, NU `ai_budget`: `process_new` primeste
    doar diferenta (`budget - reserve` la apel), deci cand rezerva e > 0 apelurile nu pot
    atinge niciodata totalul. O comparatie cu totalul ar raporta „buget NEepuizat" exact cand
    bugetul pentru iteme noi chiar s-a terminat — aceeasi eticheta falsa, in cealalta directie.

    Prins la reverificare, nu la scriere: pe cele 6 build-uri citite pe 2026-08-16 rezerva era
    0, deci greseala nu se vedea in date. Functie separata, nu conditie inline intr-un `print`,
    tocmai ca sa poata fi testata — lectia contorului de alaturi, invatata a doua oara.
    """
    plafon = ai_budget - upgrade_reserve
    if ai_calls >= plafon:
        return "buget AI epuizat"
    return f"buget NEepuizat ({ai_calls}/{plafon}) — alta cauza"


def numara_amanate(new_items: list, handled: set) -> int:
    """Cate iteme noi chiar se INTORC la rularea urmatoare.

    Functie separata ca sa poata fi testata direct: cat timp contorul statea inline in `run()`,
    orice test al lui trebuia sa-i reimplementeze formula, deci verifica o copie contra unei
    copii si trecea si cu contorul stricat (masurat prin mutatie, 2026-08-16).

    Itemele fara substanta NU intra la socoteala: sunt respinse inainte de clustering si de
    buget, deci nu se amana — revin la fiecare rulare si sunt respinse din nou.
    """
    respinse = {i["url"] for i in itemele_fara_substanta(new_items)}
    return sum(1 for i in new_items if i["url"] not in handled and i["url"] not in respinse)


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
    fara_substanta = itemele_fara_substanta(new_items)
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

    # clusterele C intai, in LOTURI (1 apel per CLUSTER_BATCH_SIZE clustere, nu per cluster).
    # MASURAT 2026-08-16: cate un apel per cluster epuiza bugetul la 17-18 clustere/rulare,
    # lasand 0 apeluri pentru model B -- amanate a crescut monoton 0->84->152->220 in 8 ore.
    # Vezi config.CLUSTER_BATCH_SIZE si process.py:process_clusters_batch.
    cbs = config.CLUSTER_BATCH_SIZE if provider else (len(syn) or 1)
    for i in range(0, len(syn), cbs):
        if used >= budget:
            break  # restul clusterelor -> reluate la rularea urmatoare
        chunk = syn[i:i + cbs]
        reps = process_clusters_batch(chunk, provider)
        used += 1
        for g, rep in zip(chunk, reps):
            if rep is None:
                continue  # esec/nemapat -> cluster amanat; membrii raman nefolded si se reiau data viitoare
            processed.append(rep)
            if not rep.get("skip"):
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


def _claude_validate(stats: dict, processed_new: list) -> dict | None:
    """Optionally validate a batch with the locally authenticated Claude Code CLI.

    Default is ``off`` so existing CI and legacy runs remain unchanged.  ``report`` records
    the verdict without blocking publication; ``required`` blocks save/render unless Claude
    Code returns an explicit approval.  The manifest contains only workflow metadata and a
    bounded article sample, never environment variables or provider secrets.
    """
    mode = os.getenv("CLAUDE_CODE_VALIDATE", "off").strip().lower()
    if mode in {"", "0", "false", "off", "no"}:
        return None
    if mode not in {"report", "required"}:
        raise ValueError("CLAUDE_CODE_VALIDATE trebuie să fie off, report sau required")
    manifest = {
        "stats": stats,
        "processed_sample": [
            {
                "url": a.get("url"),
                "source": a.get("source"),
                "source_name": a.get("source_name"),
                "original_title": a.get("original_title"),
                "title": a.get("title"),
                "teaser": (a.get("teaser") or "")[:600],
                "synthesis": (a.get("synthesis") or "")[:800],
                "category": a.get("category"),
                "model": a.get("model"),
            }
            for a in processed_new[:12]
        ],
        "policy": {"read_only": True, "no_secrets": True, "publication_guard": True},
    }
    result = ClaudeCodeValidator().validate_batch(manifest)
    verdict = {
        "status": result.status,
        "verdict": result.verdict,
        "issues": list(result.issues),
        "next_action": result.next_action,
        "evidence": list(result.evidence),
    }
    stats["claude_validation"] = verdict
    print(f">> Claude Code validator: {result.status}/{result.verdict}")
    if result.issues:
        print(f"   Probleme raportate: {len(result.issues)}")
        for issue in result.issues:
            print(f"      - {issue}")
    if result.evidence:
        print("   Dovezi:")
        for evidence in result.evidence:
            print(f"      - {evidence}")
    if mode == "required" and not result.accepted:
        raise RuntimeError(
            "Claude Code nu a aprobat batchul; publicarea a fost blocată: "
            + (result.next_action or result.status)
        )
    return verdict


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
    # Dedup si INTRE itemele proaspete, nu doar fata de stare. Doua feeduri ale aceluiasi site
    # se suprapun — `digi24` (RSS general) le contine si pe cele din `extern`
    # (`digi24.ro/rss/stiri/externe`) — iar o comparatie facuta doar cu `known` lasa ambele
    # exemplare sa treaca: fiecare primeste un apel AI, un titlu propriu si un slug propriu,
    # deci aceeasi stire ajunge de doua ori pe site. Masurat pe starea din 2026-08-07
    # (2766 articole): 57 de perechi, 56 cu slug-uri diferite, adica doua pagini.
    #
    # `state.merge()` promite dedup pe URL si e pe dict, deci imuna prin constructie — dar nu e
    # chemata nicaieri in productie (singurul apelant e tests/test_state.py). De aceea testul
    # ei trecea in timp ce calea reala nu deduplica; a se citi ca avertisment, nu ca alternativa.
    #
    # Castiga PRIMUL, deci ordinea din `config.SOURCES` decide care exemplar supravietuieste:
    # `fetch_all` pastreaza ordinea aia dinadins (vezi invariantul 1 din docstring-ul ei).
    # Regula e controlabila de proprietar mutand sursa in config, nu un accident de dictionar.
    new_items, vazute, exemplare_duplicate = [], set(), 0
    for i in raw:
        url = i["url"]
        if url in known:
            continue                      # deja in stare — garda veche, neatinsa
        if url in vazute:
            exemplare_duplicate += 1      # al doilea feed care aduce aceeasi stire
            continue
        vazute.add(url)
        new_items.append(i)
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
    # `deferred` numara doar ce se poate INTOARCE. Itemele fara substanta sunt respinse
    # DEFINITIV, inainte de clustering si inainte de buget, deci nu se „amana": revin la
    # fiecare rulare si sunt respinse din nou, la nesfarsit.
    #
    # Masurat pe 6 build-uri reale (2026-08-16, `gh run view --log`): in cele doua rulari in
    # care bugetul NU s-a epuizat (11/18 si 15/18 apeluri folosite), `deferred` era EXACT
    # numarul de iteme fara substanta — 27 din 27, 28 din 28. Zero presiune reala pe buget,
    # raportata ca „buget AI epuizat". Pe rularile in care bugetul chiar s-a terminat,
    # presiunea reala era 107-29=78 si 254-30=224. Cifra veche amesteca doua marimi opuse,
    # iar decizia „merita batching pentru Model C?" se ia tocmai pe ea.
    respinse_substanta = {i["url"] for i in itemele_fara_substanta(new_items)}
    deferred = numara_amanate(new_items, handled)
    processed_new = [a for a in processed_new if not a.get("skip")]
    # §7, „fara output stricat": un titlu care e DOAR o data calendaristica nu spune nimic
    # despre stire. Masurat 2026-08-30: `27.08.2026` si `17.08.2026` de la CJ Giurgiu
    # ajunsesera publicate asa. Sursele oficiale locale ocolesc AI-ul, deci titlul din feed
    # nu trecea prin nicio bara. Se SARE itemul, nu se publica stricat.
    titluri_data = [a for a in processed_new if titlu_e_doar_o_data(a.get("title", ""))]
    if titluri_data:
        processed_new = [a for a in processed_new if a not in titluri_data]
    # inlocuire pe URL: un rep C poate purta URL-ul unei stiri B existente pe care a absorbit-o
    rep_urls = {a.get("url") for a in processed_new}
    combined = [a for a in existing
                if a.get("url") not in folded and a.get("url") not in rep_urls] + processed_new
    upgraded = upgrade_fallbacks(combined, provider, budget - used)
    combined = state.expire(combined)

    mod = moderation.load()
    visible = moderation.apply(combined, mod)

    ai_down = cadere_ai(provider)

    stats = {
        "fetched": len(raw),
        "dead_sources": dead,
        "new": len(new_items),
        "stale_skipped": stale_skipped,
        # Cate exemplare in plus ale unei stiri deja vazute IN ACEEASI rulare au fost sarite.
        # Numarat separat de `stale_skipped` fiindca spune altceva: nu „feedul e vechi", ci
        # „doua surse din config aduc acelasi lucru" — semnal pentru portofoliul de surse.
        "exemplare_duplicate": exemplare_duplicate,
        "deferred": deferred,
        "respinse_substanta": len(respinse_substanta),
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

    # Poarta opțională Claude Code rulează înainte de save/render; în modul required,
    # orice verdict diferit de approve oprește publicarea și păstrează ultima stare bună.
    _claude_validate(stats, processed_new)
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
    if stats.get("exemplare_duplicate"):
        print(f"Exemplare duplicate sarite: {stats['exemplare_duplicate']} "
              "(aceeasi stire adusa de doua surse in aceeasi rulare)")
    if stats.get("ai_budget"):
        print(f"Buget AI: {stats['ai_budget']} apeluri | pentru iteme noi: "
              f"{stats['ai_budget'] - stats['upgrade_reserve']} | rezervat upgrade: "
              f"{stats['upgrade_reserve']} din {stats['upgradable']} eligibile | "
              f"folosite: {stats['ai_calls']}")
    if stats.get("deferred"):
        cauza = cauza_amanarii(stats["ai_calls"], stats.get("ai_budget", 0),
                               stats.get("upgrade_reserve", 0))
        print(f"Amanate ({cauza}): {stats['deferred']} din {stats['new']} "
              f"— revin la rularea urmatoare, apeluri folosite: {stats['ai_calls']}")
    if stats.get("respinse_substanta"):
        print(f"Respinse DEFINITIV (fara substanta): {stats['respinse_substanta']} "
              "— nu revin, sunt respinse din nou la fiecare rulare; nu se numara ca amanate")
    print(f"Total cunoscute (dupa expirare): {stats['total_known']} | "
          f"vizibile dupa moderare: {stats['visible_after_moderation']}")
    if stats["hold_important"]:
        print("hold_important=true -> sintezele C sunt RETINUTE de moderation.apply pana le "
              "aprobi in lista `approved` din moderation.yaml (lista celor retinute, mai sus).")
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

    # Dead man's switch pentru garda de continut (LECTII L5). O garda stricata nu se plange
    # singura: ar lasa pur si simplu warez-ul sa treaca, exact ca pe 8-9 aug 2026. Autotestul
    # ruleaza corpusul REAL de atac la fiecare pornire si arunca daca garda nu mai prinde,
    # inainte de orice fetch sau randare. Exceptia iese cu cod non-zero -> pasul de CI devine
    # rosu, commit-ul e sarit, Cloudflare NU redeployeaza (aceeasi proprietate ca mai jos).
    print(f">> garda de continut: autotest OK ({guard.autotest()} cazuri)")

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
