"""Randare SSG cu Jinja2 (autoescape ON) -> output/. Permalink-uri, sitemap, robots, feed, JSON-LD."""
import logging
import math
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape as xml_escape

from jinja2 import Environment, FileSystemLoader, select_autoescape
from slugify import slugify

from . import config, covers, geo, htmlart
from .select import (_BODY_PLACEHOLDERS, _dedup, _dedup_sources, _diversify,
                     _entity_index, _pick_hero, _quality_gate, _slug_stems,
                     sources_coherent)
from .util import title_tokens, domain_of

ROOT = config.ROOT
TPL_DIR = os.path.join(ROOT, "templates")
STATIC_DIR = os.path.join(ROOT, "static")
OUT_DIR = os.path.join(ROOT, "output")
MEDIA_DIR = os.path.join(ROOT, "media")   # imagini HTML/Chromium comise (tools/gen_images.py)
PORTRAITS_JSON = os.path.join(ROOT, "data", "portraits.json")
LEADPHOTOS_JSON = os.path.join(ROOT, "data", "leadphotos.json")


def _load_leadphotos() -> dict:
    """Fotografii reale de tip LEAD per articol (tools/fetch_leadphotos.py), cheie=art_id.
    INVARIANT: doar imagini landscape ATRIBUIRE-LIBERA (Public domain / CC0), fiindca
    lead-ul apare si pe carduri/og unde regula sect. 7 interzice orice eticheta de credit.
    Copiaza renditiile comise (media/leads/) in output/. Lipsa fisierului -> {} (fallback)."""
    try:
        import json as _json
        cache = _json.load(open(LEADPHOTOS_JSON, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    src = os.path.join(MEDIA_DIR, "leads")
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(OUT_DIR, "leads"), dirs_exist_ok=True)
    return {k: v for k, v in cache.items() if v and not v.get("miss")}


def _load_portraits() -> dict:
    """Portretele Wikimedia comise de tools/fetch_portraits.py; copiaza thumbs in output."""
    try:
        import json as _json
        cache = _json.load(open(PORTRAITS_JSON, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    src = os.path.join(MEDIA_DIR, "portraits")
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(OUT_DIR, "portraits"), dirs_exist_ok=True)
    return {k: v for k, v in cache.items() if not v.get("miss")}


def _norm_name(s: str) -> str:
    from .util import strip_diacritics
    return re.sub(r"\s+", " ", strip_diacritics((s or "").strip().lower()))


def _use_media(src: str, dst: str) -> bool:
    """Copiaza imaginea comisa (HTML/Chromium) daca exista si e valida. False -> fallback Pillow."""
    try:
        if os.path.exists(src) and os.path.getsize(src) > 3000:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            return True
    except OSError:
        pass
    return False


def _content_ver(path: str) -> str:
    """Amprenta scurta a CONTINUTULUI imaginii, pentru ?v= in URL (cache-busting).
    Hash de continut, nu mtime: mtime se schimba la fiecare copyfile/render, ceea
    ce ar invalida cache-ul la fiecare deploy desi imaginea e identica."""
    import hashlib
    try:
        with open(path, "rb") as fh:
            return hashlib.md5(fh.read()).hexdigest()[:8]
    except OSError:
        return "0"


_ASSET_VER = None


def _asset_ver() -> dict:
    """?v=<hash-continut> pentru activele /static/ versionabile (CSS/JS). Ele stau pe
    URL-uri stabile servite cu `max-age=2592000, immutable` -- deci o schimbare de cod
    (ex. o culoare in styles.css) NU ajunge la vizitatorii cu cache pana la 30 de zile.
    Hash de continut in query: URL-ul se schimba exact cand fisierul se schimba, deci
    fix-ul ajunge la primul page-load de dupa deploy, fara hard-refresh."""
    global _ASSET_VER
    if _ASSET_VER is None:
        _ASSET_VER = {name: _content_ver(os.path.join(STATIC_DIR, name))
                      for name in ("styles.css", "personalize.js", "search.js", "theme.js", "fonts.css",
                                   "calc-salariu.js", "site.webmanifest")}
    return _ASSET_VER


_RO_MONTHS = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
              "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"]


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TPL_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True, lstrip_blocks=True,
    )
    # eticheta afisata a unei categorii (slug URL neschimbat); fallback = capitalizat
    env.filters["cat_label"] = lambda slug: config.CATEGORY_LABELS.get(slug, (slug or "").capitalize())
    return env


try:
    from zoneinfo import ZoneInfo
    _TZ_RO = ZoneInfo("Europe/Bucharest")
except Exception:  # fara tzdata (ex. Windows fara pachet) -> aproximare EEST
    from datetime import timedelta
    _TZ_RO = timezone(timedelta(hours=3))


def _human_date(iso: str) -> str:
    """Ora afisata cititorului = ora Romaniei (published e stocat in UTC).
    Fara conversie, o stire de la 01:30 noaptea aparea '22:30, ieri'."""
    try:
        dt = datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(_TZ_RO)
    return f"{dt.day} {_RO_MONTHS[dt.month]} {dt.year}, {dt:%H:%M}"


def _assign_slugs(articles: list) -> None:
    """Slug unic per categorie din titlu (permalink stabil, indexabil)."""
    seen: dict = {}
    for a in articles:
        base = (slugify(a.get("title") or a.get("original_title") or "stire") or "stire")[:80]
        key = (a.get("category", "general"), base)
        n = seen.get(key, 0) + 1
        seen[key] = n
        a["slug"] = base if n == 1 else f"{base}-{n}"
        a["published_human"] = _human_date(a.get("published", ""))


_PAGES_WRITTEN: set = set()


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    # Evidenta paginilor chiar emise in rularea ASTA, pentru sitemap (_editorial_paths).
    # `output/` nu se curata intre randari, deci ce e pe disc nu e acelasi lucru cu ce a
    # publicat rularea curenta -- un director ramas de la o alta ramura ar intra in sitemap
    # ca pagina vie. Aici nu poate: daca nu s-a scris acum, nu exista.
    if os.path.basename(path) == "index.html":
        rel = os.path.relpath(path, OUT_DIR).replace(os.sep, "/")
        _PAGES_WRITTEN.add("/" + rel[:-len("index.html")].lstrip("/"))


def _logo_jsonld() -> dict:
    return {"@type": "ImageObject", "url": config.SITE["url"] + "/static/logo.png",
            "width": 512, "height": 512}


def _org_jsonld() -> dict:
    return {
        "@context": "https://schema.org", "@type": "Organization",
        "name": config.SITE["name"], "url": config.SITE["url"],
        "logo": _logo_jsonld(),
        "email": config.SITE["contact"],
        "description": config.SITE["tagline"],
    }


def _article_jsonld(a: dict) -> dict:
    body = a.get("synthesis") if a.get("model") == "C" else a.get("teaser")
    return {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "headline": a.get("title", ""),
        "description": body or "",
        "image": [config.SITE["url"] + "/static/og-image.png"],
        "datePublished": a.get("published", ""),
        "dateModified": a.get("published", ""),
        "url": f"{config.SITE['url']}/{a['category']}/{a['slug']}/",
        "mainEntityOfPage": f"{config.SITE['url']}/{a['category']}/{a['slug']}/",
        "inLanguage": config.SITE["lang"],
        "author": {"@type": "Organization", "name": config.SITE["name"]},
        "publisher": {"@type": "Organization", "name": config.SITE["name"], "logo": _logo_jsonld()},
        "isBasedOn": [s["url"] for s in a.get("sources", [])] or a.get("original_link", ""),
    }


_FONTS_CSS = None


def _fonts_css() -> str:
    """Continutul fonts.css, inline-uit in <head>: taie un hop blocant din lantul
    document -> css -> font (FCP mai bun pe retea reala). Fisierul e minuscul."""
    global _FONTS_CSS
    if _FONTS_CSS is None:
        p = os.path.join(STATIC_DIR, "fonts.css")
        try:
            _FONTS_CSS = re.sub(r"\s+", " ", open(p, encoding="utf-8").read()).strip()
        except OSError:
            _FONTS_CSS = ""
    return _FONTS_CSS


def _base_ctx(canonical_path: str, **extra) -> dict:
    ctx = {
        "site": config.SITE,
        "base": os.getenv("SITE_BASE", "").rstrip("/"),
        "categories": config.CATEGORIES,
        "year": datetime.now().year,
        "canonical": config.SITE["url"] + canonical_path,
        "org_jsonld": _org_jsonld(),
        "analytics_token": os.getenv("CF_ANALYTICS_TOKEN", "").strip() or None,
        "fonts_css": _fonts_css(),
        "asset_ver": _asset_ver(),
        "active_cat": None,
    }
    ctx.update(extra)
    return ctx


def _source_catalog(by_date: list) -> tuple[list, int, int]:
    """Catalogul /surse/: TOATE sursele din config.SOURCES, nu doar cele cu statistici de
    originalitate. O sursa (ex. o primarie) care publica un anunt unic nu intra niciodata
    intr-un cluster multi-sursa, deci n-ar aparea NICIODATA daca am lista doar din sintezele
    C -- exact bug-ul raportat (29 din 189 pe /surse/, lipseau toate primariile). Grupare pe
    categoria deja existenta in config (axa unica, "one axis one home"); in fiecare grup,
    sursele cu statistici raman intr-un tabel (nemodificat), restul intr-o lista simpla de
    linkuri fara coloane goale/zerouri care ar sugera fals performanta slaba.
    Returneaza (catalog, total_surse, surse_cu_statistici)."""
    # scor de originalitate: cine initiaza vs. cine preia (din sintezele C cu first_source)
    counts: dict = {}
    for a in by_date:
        if a.get("model") != "C" or not a.get("first_source"):
            continue
        for s in a.get("sources") or []:
            d = counts.setdefault(s["name"], {"first": 0, "total": 0})
            d["total"] += 1
            if s["name"] == a["first_source"]:
                d["first"] += 1
    src_stats = {n: {"first": d["first"], "total": d["total"], "rate": round(d["first"] / d["total"] * 100)}
                 for n, d in counts.items() if d["total"] >= 2}

    catalog = []
    for cat in config.CATEGORIES:
        entries = sorted(((k, v) for k, v in config.SOURCES.items() if v["category"] == cat),
                         key=lambda kv: _norm_name(kv[1]["name"]))
        if not entries:
            continue
        with_stats, without_stats = [], []
        pe_judet: dict = {}
        for key, v in entries:
            site_url = f"https://{domain_of(v['url'])}/"
            if v["name"] in src_stats:
                rec, camp = {"name": v["name"], "url": site_url, **src_stats[v["name"]]}, "with_stats"
            else:
                rec, camp = {"name": v["name"], "url": site_url}, "without_stats"
            # Sursele institutionale isi codeaza judetul in cheie (`pl_<judet>_...`, `cj_<judet>`)
            # -> intra in arborele regiune/judet. Ziarele nu il codeaza si raman in lista plata.
            judet = geo.judet_din_cheie(key)
            if judet:
                pe_judet.setdefault(judet, {"with_stats": [], "without_stats": []})[camp].append(rec)
            else:
                (with_stats if camp == "with_stats" else without_stats).append(rec)
        catalog.append({
            "key": cat, "label": config.CATEGORY_LABELS.get(cat, cat.capitalize()),
            "count": len(entries), "with_stats": with_stats, "without_stats": without_stats,
            "regions": _grupeaza_pe_regiuni(pe_judet),
        })
    return catalog, len(config.SOURCES), len(src_stats)


def _grupeaza_pe_regiuni(pe_judet: dict) -> list:
    """{judet: {with_stats, without_stats}} -> arbore regiune istorica > judet, pentru /surse/.

    Sapte regiuni (decizia ownerului 2026-08-02), in ordinea din `geo`; judetele alfabetic
    dupa eticheta afisata. Judetele fara regiune cunoscuta ar disparea tacut, asa ca merg
    intr-o grupa proprie la final -- o sursa nu se pierde niciodata din catalog.
    """
    pe_regiune: dict = {}
    for judet, buckets in pe_judet.items():
        regiune = geo.regiune_afisare(judet) or "ALTELE"
        pe_regiune.setdefault(regiune, []).append({
            "label": geo.eticheta_judet(judet),
            "count": len(buckets["with_stats"]) + len(buckets["without_stats"]),
            **buckets,
        })

    ordine = list(geo.ORDINE_REGIUNI_AFISARE) + ["ALTELE"]
    out = []
    for regiune in ordine:
        judete = pe_regiune.get(regiune)
        if not judete:
            continue
        judete.sort(key=lambda j: _norm_name(j["label"]))
        out.append({
            "label": geo.ETICHETE_REGIUNI.get(regiune, "Alte județe"),
            "count": sum(j["count"] for j in judete),
            "counties": judete,
        })
    return out


def build(articles: list, mod: dict | None = None) -> None:
    env = _env()
    articles = _dedup(articles)
    before = len(articles)
    articles = [a for a in articles if _quality_gate(a)]
    skipped = before - len(articles)
    if skipped:
        logging.info("quality_gate: excluded %d/%d articles (no usable body or missing source)", skipped, before)
    for a in articles:
        _dedup_sources(a)
    _assign_slugs(articles)

    # reset output (golim CONTINUTUL, nu radacina — ca un server local care tine
    # folderul deschis sa nu blocheze build-ul pe Windows), apoi copiem static
    os.makedirs(OUT_DIR, exist_ok=True)
    for entry in os.listdir(OUT_DIR):
        p = os.path.join(OUT_DIR, entry)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    shutil.copytree(STATIC_DIR, os.path.join(OUT_DIR, "static"))

    # Run build_entities in-process (validate YAML -> entities.json)
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        from build_entities import load_all, write_json
        ents = load_all()
        if ents:
            write_json(ents)
    except Exception as e:
        logging.warning("build_entities a esuat (non-fatal): %s", e)

    # Sortare pe sir; vezi nota din state.save si tests/test_published_is_utc.py.
    by_date = sorted(articles, key=lambda a: a.get("published") or "", reverse=True)

    # coperti: share (og, cu titlu) + arta fara text pentru site -- generate O DATA,
    # INAINTE de orice randare, ca hero-ul si paginile de articol sa le poata folosi.
    # URL-urile poarta ?v=<hash-continut>: imaginile stau pe cai stabile cu TTL 24h,
    # iar cand o coperta se schimba (fallback Pillow -> desen Chromium la urmatorul
    # build) browserele ar servi pictograma veche din cache pana la o zi; versiunea
    # in query schimba URL-ul doar cand se schimba imaginea, deci cache-ul ramane
    # eficient dar nu mai poate fi vreodata stale.
    leadphotos = _load_leadphotos()
    for a in by_date:
        cdir = os.path.join(OUT_DIR, a["category"], a["slug"])
        aid = htmlart.art_id(a)
        cover_dst, art_dst = os.path.join(cdir, "cover.jpg"), os.path.join(cdir, "art.jpg")
        webp_dst = os.path.join(cdir, "art.webp")
        # prioritate: (1) fotografie reala LEAD (landscape, atribuire-libera) daca articolul
        # are una -> imagine principala "foto"; (2) coperta HTML/Chromium comisa;
        # (3) fallback Pillow. Fotografia reala inlocuieste pictograma pe carduri/hero/og.
        lp = leadphotos.get(aid)
        cover_ok = art_ok = False
        if lp:
            cover_ok = _use_media(os.path.join(MEDIA_DIR, lp["cover"]), cover_dst)
            art_ok = _use_media(os.path.join(MEDIA_DIR, lp["art"]), art_dst)
            if art_ok and lp.get("webp") and _use_media(os.path.join(MEDIA_DIR, lp["webp"]), webp_dst):
                a["art_webp"] = f"/{a['category']}/{a['slug']}/art.webp?v={_content_ver(webp_dst)}"
            if cover_ok or art_ok:
                a["lead_credit"] = lp   # afisat DOAR pe pagina de articol (curtoazie); PD/CC0 -> nu e obligatoriu
        if cover_ok or _use_media(os.path.join(MEDIA_DIR, f"{aid}.c.jpg"), cover_dst) or covers.generate(a, cover_dst):
            a["cover_url"] = (f"{config.SITE['url']}/{a['category']}/{a['slug']}/cover.jpg"
                              f"?v={_content_ver(cover_dst)}")
        if art_ok or _use_media(os.path.join(MEDIA_DIR, f"{aid}.jpg"), art_dst) or covers.generate_art(a, art_dst):
            a["art_path"] = f"/{a['category']}/{a['slug']}/art.jpg?v={_content_ver(art_dst)}"
            # varianta WebP (~70% mai mica) daca e comisa; <picture> cade pe JPEG altfel
            if not a.get("art_webp") and _use_media(os.path.join(MEDIA_DIR, f"{aid}.webp"), webp_dst):
                a["art_webp"] = f"/{a['category']}/{a['slug']}/art.webp?v={_content_ver(webp_dst)}"

    hero = _pick_hero(by_date)
    hero_urls = {a["url"] for a in hero}

    by_category = {}
    for cat in config.CATEGORIES:
        # plafon pe homepage (legea lui Hick): max 9/sectiune; restul pe pagina categoriei
        items = [a for a in by_date if a.get("category") == cat and a["url"] not in hero_urls]
        by_category[cat] = _diversify(items)[:9]

    # homepage
    item_list = {
        "@context": "https://schema.org", "@type": "ItemList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "url": f"{config.SITE['url']}/{a['category']}/{a['slug']}/"}
            for i, a in enumerate(by_date[:20])
        ],
    }
    _write(os.path.join(OUT_DIR, "index.html"),
           env.get_template("index.html").render(**_base_ctx(
               "/", nav_section="stiri", articles=by_date, hero=hero, by_category=by_category,
               page_jsonld=item_list, newsletter_html=_newsletter_html())))

    src_catalog, total_sources, stats_sources = _source_catalog(by_date)
    _write(os.path.join(OUT_DIR, "surse", "index.html"),
           env.get_template("surse.html").render(**_base_ctx(
               "/surse/", catalog=src_catalog, total_sources=total_sources,
               stats_sources=stats_sources, ttl_days=config.ARTICLE_TTL_DAYS)))

    # graful cunoasterii v1: pagini de subiect per entitate (+ feed de urmarire >=3)
    ents = _entity_index(by_date)
    portraits = _load_portraits()   # fotografii reale P18 (auto-gazduite) cheie=nume normalizat
    # graf-lite: entitatile care apar IMPREUNA (co-ocurenta pe articole) -> "Conexiuni"
    art_slugs: dict = {}
    for s, d in ents.items():
        for a in d["articles"]:
            art_slugs.setdefault(a["url"], set()).add(s)
    # pondere IDF/entitate pentru relevanta: o entitate rara conteaza mai mult decat una
    # frecventa. Departajeaza candidatii "articole conectate" dupa raritatea entitatilor comune.
    _n_docs = max(len(by_date), 1)
    idf = {s: math.log(_n_docs / len(d["articles"])) for s, d in ents.items()}
    subject_tpl = env.get_template("subject.html")
    for s, d in ents.items():
        has_feed = len(d["articles"]) >= 3
        co: dict = {}
        for a in d["articles"]:
            for other in art_slugs.get(a["url"], ()):  
                if other != s:
                    co[other] = co.get(other, 0) + 1
        connections = [(o, ents[o]["name"], n) for o, n in
                       sorted(co.items(), key=lambda kv: -kv[1])[:6]]
        _write(os.path.join(OUT_DIR, "subiect", s, "index.html"),
               subject_tpl.render(**_base_ctx(f"/subiect/{s}/", name=d["name"], slug=s,
                                              articles=sorted(d["articles"],
                                                              key=lambda a: a.get("published") or "",
                                                              reverse=True),
                                              connections=connections,
                                              portrait=portraits.get(_norm_name(d["name"])),
                                              has_feed=has_feed)))
        if has_feed:
            _write(os.path.join(OUT_DIR, "subiect", s, "feed.xml"),
                   _feed_xml(d["articles"], f"{d['name']} — {config.SITE['name']}",
                             f"{config.SITE['url']}/subiect/{s}/",
                             f"Știri despre {d['name']} pe {config.SITE['name']}"))

    # pagini de categorie + permalink articole
    article_tpl = env.get_template("article.html")
    cat_tpl = env.get_template("category.html")
    for cat in config.CATEGORIES:
        items = [a for a in by_date if a.get("category") == cat]
        # si categoriile inca goale (in insamantare) primesc pagina 1 — altfel nav-ul ar duce la 404
        for page in range(0, max(len(items), 1), 20):
            page_items = _diversify(items[page:page+20])
            page_num = page // 20 + 1
            page_dir = os.path.join(OUT_DIR, cat) if page_num == 1 else os.path.join(OUT_DIR, cat, str(page_num))
            show_pagination = (len(items) > 20 and page_num == 1)
            _write(os.path.join(page_dir, "index.html"),
                   cat_tpl.render(**_base_ctx(
                       f"/{cat}/" if page_num == 1 else f"/{cat}/{page_num}/",
                       category=cat, articles=page_items, active_cat=cat,
                       show_pagination=show_pagination)))
        for a in items:
            topics = [(slugify(e)[:60], e) for e in (a.get("entities") or [])
                      if slugify(e)[:60] in ents]
            people = []
            for e in (a.get("entities") or []):
                p = portraits.get(_norm_name(e))
                if p:
                    s = slugify(e)[:60]
                    people.append({**p, "slug": s if s in ents else None})
                if len(people) >= 2:
                    break
            # articole conectate: minim RELATED_MIN_SHARED entitati comune (o singura
            # entitate comuna — de regula o tara larga ca "Franța" — nu e relevanta reala,
            # doar zgomot). Rang dupa numar de entitati comune, apoi raritatea lor (IDF),
            # apoi recenta. Sub prag => lista goala, sablonul ascunde sectiunea.
            mine = art_slugs.get(a["url"], set())
            related = []
            if mine:
                seen_urls = {a["url"]}
                scored = []
                for s2 in mine:
                    for other in ents[s2]["articles"]:
                        if other["url"] in seen_urls:
                            continue
                        seen_urls.add(other["url"])
                        common = mine & art_slugs.get(other["url"], set())
                        if len(common) < config.RELATED_MIN_SHARED:
                            continue
                        weight = sum(idf.get(s, 0.0) for s in common)
                        scored.append((len(common), weight,
                                       other.get("published") or "", other))
                scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
                related = [t[3] for t in scored[:3]]
            og_image = a.get("cover_url")
            jsonld = _article_jsonld(a)
            if og_image:
                jsonld["image"] = [og_image]
            breadcrumb_jsonld = {
                "@context": "https://schema.org", "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": config.SITE["name"],
                     "item": config.SITE["url"] + "/"},
                    {"@type": "ListItem", "position": 2, "name": cat,
                     "item": f"{config.SITE['url']}/{cat}/"},
                    {"@type": "ListItem", "position": 3, "name": a.get("title", "")},
                ]
            }
            _write(os.path.join(OUT_DIR, cat, a['slug'], "index.html"),
                   article_tpl.render(**_base_ctx(
                       f"/{cat}/{a['slug']}/", a=a, active_cat=cat, topics=topics,
                       people=people, related=related, og_image=og_image,
                       article_jsonld=jsonld, breadcrumb_jsonld=breadcrumb_jsonld)))

    _render_legal(env)
    _render_ghiduri(env, by_date)
    _write(os.path.join(OUT_DIR, "404.html"),
           env.get_template("category.html").render(**_base_ctx(
               "/404.html", category="Pagina negăsită", articles=[])))
    _write_sitemap(by_date)
    _write_robots()
    # dovada de domeniu pentru IndexNow: motorul citeste cheia de la radacina
    _write(os.path.join(OUT_DIR, f"{config.INDEXNOW_KEY}.txt"), config.INDEXNOW_KEY + "\n")
    _write_headers()
    _write_feed(by_date)
    _write_search(env, by_date)


def _newsletter_html() -> str:
    """Embed-ul Brevo din content/newsletter.html. Daca fisierul lipseste, sectiunea
    NU se randeaza deloc ("" e falsy in template) -- instructiunile de configurare
    sunt pentru owner (vezi README), nu pentru cititorii site-ului public."""
    path = os.path.join(ROOT, "content", "newsletter.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return ""


def _md_to_html(text: str) -> str:
    """Markdown -> HTML pentru text din date (sectiunile ghidurilor). Fara `markdown`
    instalat, cade pe o impartire in paragrafe: mai bine text citibil decat o exceptie
    la build pentru o dependenta optionala.

    INVARIANT: intrarea e scrisa de OM, in `data/entities/*.yaml`, si iesirea se randeaza
    cu `| safe`. `python-markdown` NU e un sanitizer — lasa HTML-ul brut din sursa sa treaca
    intact. Cat timp textul vine dintr-un fisier comis in repo, asta e acelasi model ca
    `/legal/*`. Daca vreodata `sectiuni` ajunge sa fie populat de un pas automat sau de AI
    (restul pipeline-ului e plin de asa ceva), invariantul cade si aici trebuie sanitizare
    inainte de `| safe` — nu exista alta poarta intre datele alea si cititor."""
    try:
        import markdown as md
    except ImportError:
        return "<p>" + (text or "").replace("\n\n", "</p><p>") + "</p>"
    return md.markdown(text or "", extensions=["extra"])


def _render_md_dir(env: Environment, src_dir: str, url_prefix: str) -> None:
    """Randeaza toate .md dintr-un folder la <url_prefix>/<nume>/ cu template-ul legal."""
    if not os.path.isdir(src_dir):
        return
    try:
        import markdown as md
    except ImportError:
        md = None
    tpl = env.get_template("legal.html") if os.path.exists(os.path.join(TPL_DIR, "legal.html")) else None
    if not tpl:
        return
    for fn in os.listdir(src_dir):
        if not fn.endswith(".md"):
            continue
        name = fn[:-3]
        with open(os.path.join(src_dir, fn), "r", encoding="utf-8") as fh:
            raw = fh.read()
        title = raw.lstrip("# ").splitlines()[0].strip() if raw.startswith("#") else name
        html = md.markdown(raw, extensions=["extra"]) if md else "<pre>" + raw + "</pre>"
        out = os.path.join(OUT_DIR, *url_prefix.strip("/").split("/"), name, "index.html") \
            if url_prefix.strip("/") else os.path.join(OUT_DIR, name, "index.html")
        _write(out, tpl.render(**_base_ctx(f"{url_prefix}/{name}/".replace("//", "/"),
                                           page_title=title, body_html=html, page_heading=title)))


def _render_ghiduri(env: Environment, articles: list) -> None:
    """Fazele 1-2: Ghiduri din entități YAML + instrumente + calendar.
    Datele stau în data/entities/*.yaml — o singură sursă de adevăr.
    build_entities.py: validează YAML → emite output/data/entities.json."""
    import json as _json
    from datetime import datetime as _dt

    entities_json = os.path.join(OUT_DIR, "data", "entities.json")
    if not os.path.exists(entities_json):
        return
    with open(entities_json, "r", encoding="utf-8") as fh:
        edata = _json.load(fh)
    entities = edata.get("entity_kwargs", {})
    categorii = edata.get("categorii_ghid", {})
    if not entities:
        return

    def _fmt_int(v):
        if isinstance(v, (int, float)):
            return f"{v:,}".replace(",", ".")
        return v
    def _domain(url):
        return re.sub(r"^https?://(?:www\.)?", "", (url or "")).rstrip("/")
    env.filters["format_int"] = _fmt_int
    env.filters["domain_from_url"] = _domain

    ghid_tpl = env.get_template("ghid.html")
    ghiduri_tpl = env.get_template("ghiduri.html")

    categorii_icon = {
        "bani": "💰", "acte": "📄", "auto": "🚗",
        "locuinte": "🏠", "educatie": "🎓", "sanatate": "🩺",
    }

    entities_by_cat = {}
    for eid, ent in entities.items():
        cat = ent.get("categorie_ghid", "")
        entities_by_cat.setdefault(cat, []).append({"id": eid, **ent})

    for eid, ent in entities.items():
        cat_stiri = ent.get("categorie_stiri", "")
        related = [a for a in articles if a.get("category") == cat_stiri][:5]
        faq_jsonld = {
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": item["q"],
                 "acceptedAnswer": {"@type": "Answer", "text": item["a"]}}
                for item in (ent.get("faq") or [])
            ]
        }
        breadcrumb_jsonld = {
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": config.SITE["name"], "item": config.SITE["url"] + "/"},
                {"@type": "ListItem", "position": 2, "name": "Ghiduri", "item": config.SITE["url"] + "/ghiduri/"},
                {"@type": "ListItem", "position": 3, "name": ent.get("nume", eid)},
            ]
        }
        calculator_html = ""
        if ent.get("relatii", {}).get("calculator"):
            calculator_html = _render_calc_salariu(env, ent)
        # Ghidurile procedurale (acte, permis, programe) n-au o cifra-titlu, ci proza pe
        # sectiuni. Markdown-ul se randeaza aici, nu in template: Jinja n-are filtru de
        # markdown, iar `| safe` pe text neconvertit ar afisa `**bold**` literal.
        sectiuni = [{"titlu": s.get("titlu", ""), "continut_html": _md_to_html(s.get("continut", ""))}
                    for s in (ent.get("sectiuni") or [])]
        _write(os.path.join(OUT_DIR, "ghiduri", eid, "index.html"),
               ghid_tpl.render(**_base_ctx(
                   f"/ghiduri/{eid}/", ent=ent, categorii=categorii,
                   categorii_icon=categorii_icon, related_news=related,
                   faq_jsonld=faq_jsonld, breadcrumb_jsonld=breadcrumb_jsonld,
                   calculator_html=calculator_html, sectiuni=sectiuni, active_cat=None)))

    # Cate ghiduri au inca valori neconfirmate: pagina isi ajusteaza promisiunea dupa asta,
    # ca sa nu scrie „verificate" cand nu sunt.
    n_neverificate = sum(1 for ent in entities.values() if not ent.get("verificat"))
    _write(os.path.join(OUT_DIR, "ghiduri", "index.html"),
           ghiduri_tpl.render(**_base_ctx(
               "/ghiduri/", nav_section="ghiduri", categorii=categorii, categorii_icon=categorii_icon,
               entities_by_cat=entities_by_cat, n_neverificate=n_neverificate,
               n_ghiduri=len(entities))))

    # Instrumente
    tools = [
        {"url": "/instrumente/calculator-salariu/", "icon": "🧮",
         "title": "Calculator salariu net", "desc": "Calculează salariul net în funcție de brut. Datele se actualizează automat."},
    ]
    instr_tpl = env.get_template("instrumente.html")
    _write(os.path.join(OUT_DIR, "instrumente", "index.html"),
           instr_tpl.render(**_base_ctx("/instrumente/", nav_section="instrumente", tools=tools)))
    calc_tpl = env.get_template("calculator.html")
    # Salariul minim ajunge in pagina la randare, nu printr-un fetch() la runtime: situl se
    # regenereaza la 2h, deci valoarea e la fel de proaspata, iar pagina nu mai depinde de
    # cod inline (blocat de CSP) ca sa afiseze ceva.
    _write(os.path.join(OUT_DIR, "instrumente", "calculator-salariu", "index.html"),
           calc_tpl.render(**_base_ctx("/instrumente/calculator-salariu/",
                                       salariu_minim=_salariu_minim(entities.get("salariul-minim")))))

    # Calendar din termenele entităților
    termene = []
    for eid, ent in entities.items():
        for t in (ent.get("termene") or []):
            try:
                ts = _dt.fromisoformat(t["data"]).timestamp()
            except (ValueError, TypeError):
                ts = 0
            termene.append({
                "data": t.get("data", ""), "eveniment": t.get("eveniment", ""),
                "timestamp": ts, "ent_id": eid, "ent_nume": ent.get("nume", ""),
            })
    _RO_MONTHS_LONG = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
                       "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"]
    def _human_month(ym: str) -> str:
        try:
            y, m = ym.split("-")
            return f"{_RO_MONTHS_LONG[int(m)]} {y}"
        except (ValueError, IndexError):
            return ym
    env.filters["human_month"] = _human_month
    cal_tpl = env.get_template("calendar.html")
    _write(os.path.join(OUT_DIR, "calendar", "index.html"),
           cal_tpl.render(**_base_ctx(
               "/calendar/", nav_section="calendar", termene=termene,
               now_timestamp=_dt.now().timestamp())))


# Rezerva pentru cazul in care entitatea lipseste sau n-are `brut`. HG 146/2026, in vigoare de la
# 1 iul 2026. Se schimba odata cu data/entities/salariul-minim.yaml — un test leaga cele doua
# valori, pentru ca o divergenta aici nu strica nimic vizibil: calculatorul continua sa afiseze
# un net, doar ca gresit.
_SALARIU_MINIM_FALLBACK = 4325


def _salariu_minim(ent: dict | None) -> int:
    """Brutul minim al unei entitati, cu o singura valoare de rezerva in tot codul.
    Tolereaza `valoare_curenta: null` in date -- acolo `.get("valoare_curenta", {})` intoarce
    None, iar un `.get` inlantuit ar pica build-ul cu AttributeError."""
    val = (ent or {}).get("valoare_curenta") or {}
    brut = val.get("brut")
    return brut if isinstance(brut, (int, float)) else _SALARIU_MINIM_FALLBACK


def _render_calc_salariu(env: Environment, ent: dict) -> str:
    """Markup-ul calculatorului, dintr-un template -- NU dintr-un f-string cu JS in el.
    Varianta veche emitea <script> inline si oninput=/onclick=, pe care CSP-ul
    (`script-src 'self'`, _write_headers) le blocheaza tacut: pe live calculatorul afisa
    campul si butoanele si nu calcula nimic. Codul e acum in static/calc-salariu.js."""
    return env.get_template("_calc_salariu.html").render(
        salariu_minim=_salariu_minim(ent), calc_heading="🧮 Calculator salariu net")


def _render_legal(env: Environment) -> None:
    _render_md_dir(env, os.path.join(ROOT, "content", "legal"), "/legal")
    # pagini generale (ex. content/pages/despre.md -> /despre/)
    _render_md_dir(env, os.path.join(ROOT, "content", "pages"), "")


# Sectiunile editoriale care intra in sitemap. NU tot ce se randeaza: `subiect/` are ~300 de
# pagini de agregare subtiri (decizie de proprietar daca merita indexate), `cauta/` e o unealta,
# iar `static/`, `data/`, `leads/`, `portraits/` nu sunt pagini.
_SITEMAP_SECTIONS = ("ghiduri", "instrumente", "calendar", "surse", "legal")


def _content_page_slugs() -> set:
    """Paginile de sine statatoare (ex. /despre/), citite din SURSA lor: content/pages/*.md."""
    src = os.path.join(ROOT, "content", "pages")
    if not os.path.isdir(src):
        return set()
    return {fn[:-3] for fn in os.listdir(src) if fn.endswith(".md")}


def _editorial_paths() -> list:
    """Paginile editoriale publicate de rularea curenta, ca `/ghiduri/permis-auto/`.

    Pana la 2026-08-02 sitemap-ul continea DOAR `/`, categoriile si articolele: fiecare ghid,
    instrumentul, calendarul, catalogul de surse si paginile legale lipseau cu totul, desi sunt
    vii si linkate din navigatie.

    Sursa e `_PAGES_WRITTEN` — ce a scris rularea asta — NU un scan al lui `output/`. Prima
    varianta scana discul si avea o gaura demonstrata: `output/` nu se curata intre randari,
    deci un director ramas de la alta ramura (`/utile/`, calea moarta din 17 iulie) intra in
    sitemap ca pagina vie, desi nimic n-o mai randeaza. Ce nu s-a scris acum nu exista.
    Un ghid nou intra automat, fara sa fie nevoie de o editare aici — asta ramane.

    Fara `lastmod`: un „modificat azi" la fiecare rulare de doua ore ar fi neadevarat pentru
    o pagina legala neatinsa de luni de zile. Mai bine niciun semnal decat unul fals."""
    pages = _content_page_slugs()
    paths = set()
    for p in _PAGES_WRITTEN:
        segments = p.strip("/").split("/") if p.strip("/") else []
        if not segments:
            continue  # radacina, deja in sitemap cu lastmod
        if segments[0] in _SITEMAP_SECTIONS:
            paths.add(p)
        elif len(segments) == 1 and segments[0] in pages:
            paths.add(p)
    return sorted(paths)


# Sitemap Google News. Limita de doua zile NU e o alegere editoriala: protocolul cere ca
# fisierul sa contina doar articole din ultimele doua zile, iar Google ignora restul. Un
# sitemap plin de intrari ignorate nu e neutru, e un semnal prost. Plafonul de 1000 e tot
# al protocolului. Masurat 2026-08-03 pe `data/articles.json`: 517 articole in fereastra,
# din 1736 pastrate — deci plafonul nu musca azi, dar ramane ca sa nu emitem un fisier
# invalid intr-o zi cu volum dublu.
#
# 46, nu 48, si asta e masurat, nu prudenta: fisierul se scrie o data pe rulare, iar
# `build.yml` ruleaza la doua ore (`13 */2`, §17). O intrare la exact 48h in momentul
# generarii sta pe live inca un ciclu intreg, deci **imbatraneste** dincolo de limita si
# devine invalida fara ca nimic sa fie regenerat. Verificat pe preview-ul lui #122: la
# generare toate cele 430 erau in fereastra, la o recitire 20 de minute mai tarziu — nu.
# Marja = un interval de cron. Ridici fereastra doar daca ridici si cadenta.
_NEWS_CRON_MARGIN_H = 2
_NEWS_WINDOW_H = 48 - _NEWS_CRON_MARGIN_H
_NEWS_MAX_URLS = 1000
_NEWS_NS = "http://www.google.com/schemas/sitemap-news/0.9"

# Ce sitemap-uri a emis chiar rularea ASTA. `robots.txt` le anunta pe astea, nu o lista
# scrisa de mana: `sitemap-images.xml` se scrie doar daca exista imagini, iar robots il
# anunta neconditionat din iulie — adica trimite crawlerul intr-un 404 pe orice rulare
# fara coperti. Acelasi mecanism ca `_PAGES_WRITTEN`: ce nu s-a scris acum nu exista.
_SITEMAPS_WRITTEN: list = []


def _news_articles(articles: list, now: datetime) -> list:
    """Articolele din ultimele `_NEWS_WINDOW_H` ore, cele mai noi primele.

    `published` e ISO UTC pentru toata baza (invariant masurat si aparat de
    `tests/test_published_is_utc.py`), dar filtrarea se face pe `datetime`, nu pe sir:
    o intrare cu offset local ar fi doar clasificata gresit cu cateva ore aici, nu ar
    strica ordinea globala — deci parsarea e ieftina si nu ascunde nimic."""
    cutoff = now - timedelta(hours=_NEWS_WINDOW_H)
    recent = []
    for a in articles:
        raw = a.get("published") or ""
        try:
            ts = datetime.fromisoformat(raw)
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff:
            recent.append((ts, a))
    recent.sort(key=lambda pair: pair[0], reverse=True)
    return [a for _, a in recent[:_NEWS_MAX_URLS]]


def _write_news_sitemap(articles: list, now: datetime) -> None:
    """sitemap-news.xml — fisier separat, ca `sitemap-images.xml`.

    Nu se adauga namespace-ul `news:` in `sitemap.xml`: acela are ~1300 de URL-uri, din
    care ghiduri, pagini legale si articole de acum o saptamana. Protocolul cere exact
    inversul — doar stiri, doar din ultimele 48h."""
    url = config.SITE["url"]
    recent = _news_articles(articles, now)
    if not recent:
        return
    items = "\n".join(
        "  <url><loc>" + xml_escape(f"{url}/{a['category']}/{a['slug']}/") + "</loc>\n"
        "    <news:news>\n"
        "      <news:publication>\n"
        f"        <news:name>{xml_escape(config.SITE['name'])}</news:name>\n"
        f"        <news:language>{xml_escape(config.SITE['lang'])}</news:language>\n"
        "      </news:publication>\n"
        f"      <news:publication_date>{xml_escape(a.get('published', ''))}</news:publication_date>\n"
        f"      <news:title>{xml_escape(a.get('title') or a.get('original_title', ''))}</news:title>\n"
        "    </news:news>\n  </url>"
        for a in recent)
    _write(os.path.join(OUT_DIR, "sitemap-news.xml"),
           '<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           f'xmlns:news="{_NEWS_NS}">\n'
           f"{items}\n</urlset>\n")
    _SITEMAPS_WRITTEN.append("sitemap-news.xml")


def _write_sitemap(articles: list) -> None:
    url = config.SITE["url"]
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    _SITEMAPS_WRITTEN.clear()
    cat_lastmod = {}
    for a in articles:
        c = a.get("category", "")
        d = (a.get("published") or "")[:10]
        if c and d and d > cat_lastmod.get(c, ""):
            cat_lastmod[c] = d
    locs = [(f"{url}/", today)]
    locs += [(f"{url}/{c}/", cat_lastmod.get(c, today)) for c in config.CATEGORIES]
    locs += [(f"{url}/{a['category']}/{a['slug']}/", (a.get("published") or "")[:10]) for a in articles]
    locs += [(url + p, "") for p in _editorial_paths()]
    items = "\n".join(
        f"  <url><loc>{xml_escape(l)}</loc>" + (f"<lastmod>{lm}</lastmod>" if lm else "") + "</url>"
        for l, lm in locs)
    _write(os.path.join(OUT_DIR, "sitemap.xml"),
           '<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{items}\n</urlset>\n")
    _SITEMAPS_WRITTEN.append("sitemap.xml")
    _write_news_sitemap(articles, now)
    # Image sitemap
    img_locs = []
    for a in articles:
        if a.get("cover_url"):
            img_locs.append((f"{url}/{a['category']}/{a['slug']}/",
                              a.get("cover_url"),
                              a.get("title") or a.get("original_title", "")))
    if img_locs:
        img_items = "\n".join(
            "  <url><loc>" + xml_escape(l) + "</loc>\n"
            "    <image:image>\n      <image:loc>" + xml_escape(il) + "</image:loc>\n"
            "      <image:title>" + xml_escape(it) + "</image:title>\n"
            "    </image:image>\n  </url>"
            for l, il, it in img_locs[:1000])
        _write(os.path.join(OUT_DIR, "sitemap-images.xml"),
               '<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
               'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
               f"{img_items}\n</urlset>\n")
        _SITEMAPS_WRITTEN.append("sitemap-images.xml")


def _write_search(env: Environment, articles: list) -> None:
    """Pagina /cauta/ + index JSON mic (titluri) pentru cautarea client-side."""
    import json as _json
    idx = [{"t": a.get("title", ""), "u": f"/{a['category']}/{a['slug']}/",
            "c": a.get("category", ""), "d": a.get("published_human", "")} for a in articles]
    _write(os.path.join(OUT_DIR, "search-index.json"), _json.dumps(idx, ensure_ascii=False))
    _write(os.path.join(OUT_DIR, "cauta", "index.html"),
           env.get_template("search.html").render(**_base_ctx("/cauta/")))


def _write_robots() -> None:
    """Anunta DOAR sitemap-urile scrise de rularea curenta (`_SITEMAPS_WRITTEN`)."""
    lines = "".join(f"Sitemap: {config.SITE['url']}/{name}\n" for name in _SITEMAPS_WRITTEN)
    _write(os.path.join(OUT_DIR, "robots.txt"), f"User-agent: *\nAllow: /\n{lines}")


def _write_headers() -> None:
    """Cache-Control + headere de securitate pe Cloudflare Pages (fisierul _headers).
    Activele imutabile tin mult; imaginile o zi; HTML-ul NU se cache-uieste agresiv
    (stiri proaspete). Pattern-urile de cale TREBUIE sa inceapa cu '/' -- altfel
    Pages le ignora si imaginile cad pe TTL-ul implicit de 4h."""
    csp = ("default-src 'self'; "
           "script-src 'self' https://static.cloudflareinsights.com https://www.googletagmanager.com; "
           "style-src 'self' 'unsafe-inline'; "
           "img-src 'self' data: https://*.google-analytics.com https://*.googletagmanager.com; "
           "font-src 'self'; "
           "connect-src 'self' https://cloudflareinsights.com https://*.google-analytics.com "
           "https://*.analytics.google.com https://*.googletagmanager.com; "
           "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
           "upgrade-insecure-requests")
    _write(os.path.join(OUT_DIR, "_headers"),
           "/*\n"
           f"  Content-Security-Policy: {csp}\n"
           "  Strict-Transport-Security: max-age=31536000; includeSubDomains\n"
           "  X-Content-Type-Options: nosniff\n"
           "  X-Frame-Options: DENY\n"
           "  Referrer-Policy: strict-origin-when-cross-origin\n"
           "  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()\n"
           "/static/*\n  Cache-Control: public, max-age=2592000, immutable\n"
           "/favicon.svg\n  Cache-Control: public, max-age=2592000\n"
           "/*.jpg\n  Cache-Control: public, max-age=86400\n"
           "/*.png\n  Cache-Control: public, max-age=86400\n"
           "/*.webp\n  Cache-Control: public, max-age=86400\n"
           "/feed.xml\n  Cache-Control: public, max-age=1800\n")


def _feed_xml(articles: list, title: str, link: str, description: str) -> str:
    url = config.SITE["url"]
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    entries = []
    for a in articles[:50]:
        body = a.get("synthesis") if a.get("model") == "C" else a.get("teaser")
        alink = f"{url}/{a['category']}/{a['slug']}/"
        entries.append(
            "    <item>\n"
            f"      <title>{xml_escape(a.get('title',''))}</title>\n"
            f"      <link>{xml_escape(alink)}</link>\n"
            f"      <guid>{xml_escape(alink)}</guid>\n"
            f"      <description>{xml_escape(body or '')}</description>\n"
            "    </item>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0"><channel>\n'
            f"  <title>{xml_escape(title)}</title>\n"
            f"  <link>{xml_escape(link)}</link>\n"
            f"  <description>{xml_escape(description)}</description>\n"
            f"  <language>{config.SITE['lang']}</language>\n"
            f"  <lastBuildDate>{now}</lastBuildDate>\n"
            + "\n".join(entries) +
            "\n</channel></rss>\n")


def _write_feed(articles: list) -> None:
    _write(os.path.join(OUT_DIR, "feed.xml"),
           _feed_xml(articles, config.SITE["name"], config.SITE["url"], config.SITE["tagline"]))
