"""Randare SSG cu Jinja2 (autoescape ON) -> output/. Permalink-uri, sitemap, robots, feed, JSON-LD."""
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape

from jinja2 import Environment, FileSystemLoader, select_autoescape
from slugify import slugify

from . import config, covers, htmlart
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
                      for name in ("styles.css", "personalize.js", "search.js", "fonts.css")}
    return _ASSET_VER


_RO_MONTHS = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
              "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"]


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TPL_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True, lstrip_blocks=True,
    )


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


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


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


def _dedup(articles: list) -> list:
    """Elimina articolele despre acelasi eveniment (titluri foarte asemanatoare).

    Pastreaza varianta cea mai bogata: C inaintea B, mai multe surse, mai recent.
    """
    ordered = sorted(articles, key=lambda a: a.get("published") or "", reverse=True)
    ordered.sort(key=lambda a: (0 if a.get("model") == "C" else 1, -len(a.get("sources") or [])))
    kept, kept_tok = [], []
    for a in ordered:
        tok = title_tokens(a.get("title") or a.get("original_title") or "")
        is_dup = False
        for kt in kept_tok:
            if not tok or not kt:
                continue
            inter = len(tok & kt)
            if inter >= 4 or inter / len(tok | kt) >= 0.55:
                is_dup = True
                break
        if not is_dup:
            kept.append(a)
            kept_tok.append(tok)
    return kept


def _diversify(items: list, max_run: int = 2) -> list:
    """Reordonare blanda anti-monotonie (regula 'source diversity'): pastreaza
    ordinea cronologica, dar acelasi domeniu-sursa nu apare mai mult de `max_run`
    ori consecutiv -- urmatorul articol de la alta sursa e tras in fata.
    Nu elimina nimic; sursele vorbarete (ex. Digi24 Extern, 53% din extern) doar
    se intretes cu restul in loc sa monopolizeze vizual sectiunea.
    """
    def dom(a: dict) -> str:
        return domain_of(a.get("original_link") or "") or a.get("source_name", "")

    pool, out = list(items), []
    while pool:
        tail = [dom(x) for x in out[-max_run:]]
        idx = 0
        if len(tail) == max_run and len(set(tail)) == 1:
            idx = next((i for i, a in enumerate(pool) if dom(a) != tail[0]), 0)
        out.append(pool.pop(idx))
    return out


def _entity_index(articles: list) -> dict:
    """Slug -> {name, articles} pentru entitatile AI cu >=2 aparitii publicate.
    Grauntele grafului cunoasterii: pagini statice /subiect/<slug>/."""
    idx: dict = {}
    for a in articles:
        for e in a.get("entities") or []:
            s = slugify(e)[:60]
            if not s:
                continue
            d = idx.setdefault(s, {"name": e, "articles": []})
            d["articles"].append(a)
    return {s: d for s, d in idx.items() if len(d["articles"]) >= 2}


def _pick_hero(articles: list) -> list:
    featured = [a for a in articles if a.get("featured")]
    rest = [a for a in articles if not a.get("featured")]
    # prioritate: AI (gemini) inaintea fallback, apoi clustere C, apoi cele mai recente
    rest_sorted = sorted(rest, key=lambda a: a.get("published") or "", reverse=True)
    rest_sorted.sort(key=lambda a: (a.get("processed_by") != "gemini", a.get("model") != "C"))
    return (featured + rest_sorted)[:6]


def _dedup_sources(a: dict) -> None:
    """Surse unice dupa domeniu (evita 'Digi24' + 'Digi24 Extern' duplicate pe acelasi card,
    inclusiv pentru clustere C deja salvate in state inainte de acest fix)."""
    seen, out = set(), []
    for s in a.get("sources") or []:
        d = domain_of(s.get("url", ""))
        if d in seen:
            continue
        seen.add(d)
        out.append(s)
    if out:
        a["sources"] = out


_BODY_PLACEHOLDERS = {"Detalii pe sursa.", "Detalii pe surse.", ""}


def _slug_stems(url: str) -> set:
    """Cuvinte-cheie (stem 6 litere) din ultima bucata a URL-ului = subiectul articolului-sursa."""
    slug = re.sub(r"[?#].*$", "", url or "").rstrip("/").split("/")[-1]
    return {t[:6] for t in title_tokens(slug.replace("-", " ").replace("_", " "))}


def sources_coherent(a: dict) -> bool:
    """False daca o sursa a unui cluster C nu imparte NICIUN cuvant cu restul (mis-clustering)."""
    srcs = a.get("sources") or []
    if len(srcs) < 2:
        return True
    toks = [_slug_stems(s.get("url", "")) for s in srcs]
    for i, t in enumerate(toks):
        if not t:
            continue
        others = set().union(*[toks[j] for j in range(len(toks)) if j != i]) if len(toks) > 1 else set()
        if others and not (t & others):
            return False
    return True


def _quality_gate(a: dict) -> bool:
    """Contract de date: un articol trece gate-ul daca satisface toate conditiile.

    Returneaza True = publicabil. False = exclus din feed (zero output degradat).
    """
    title = (a.get("title") or "").strip()
    if not title:
        return False

    if a.get("model") == "C":
        body = (a.get("synthesis") or "").strip()
    else:
        body = (a.get("teaser") or "").strip()

    if not body or body in _BODY_PLACEHOLDERS:
        return False
    if body == title:
        return False

    # sursa minima
    has_source = bool(a.get("sources")) or bool(a.get("original_link"))
    if not has_source:
        return False

    # fallback = titlu/body brut din RSS, fara sinteza AI -> zgomot, NU se publica
    # (indiferent de limba). Item-ul ramane in state si se reia/upgrade-eaza la AI.
    if a.get("processed_by") == "fallback":
        return False

    # cluster C cu surse incoerente (linkuri spre articole fara legatura) -> nu se publica
    if a.get("model") == "C" and not sources_coherent(a):
        return False

    # titlu brut trunchiat ("...") = output degradat
    if title.endswith("...") or title.endswith("…"):
        return False

    return True


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
               "/", articles=by_date, hero=hero, by_category=by_category,
               page_jsonld=item_list, newsletter_html=_newsletter_html())))

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
    src_stats = sorted(
        [{"name": n, "first": d["first"], "total": d["total"],
          "rate": round(d["first"] / d["total"] * 100)} for n, d in counts.items() if d["total"] >= 2],
        key=lambda x: (-x["first"], -x["rate"]))
    _write(os.path.join(OUT_DIR, "surse", "index.html"),
           env.get_template("surse.html").render(**_base_ctx(
               "/surse/", stats=src_stats, ttl_days=config.ARTICLE_TTL_DAYS)))

    # graful cunoasterii v1: pagini de subiect per entitate (+ feed de urmarire >=3)
    ents = _entity_index(by_date)
    portraits = _load_portraits()   # fotografii reale P18 (auto-gazduite) cheie=nume normalizat
    # graf-lite: entitatile care apar IMPREUNA (co-ocurenta pe articole) -> "Conexiuni"
    art_slugs: dict = {}
    for s, d in ents.items():
        for a in d["articles"]:
            art_slugs.setdefault(a["url"], set()).add(s)
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
        for page in range(0, len(items), 20):
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
            # articole conectate: cele mai multe entitati comune, apoi recenta
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
                        shared = len(mine & art_slugs.get(other["url"], set()))
                        scored.append((shared, other.get("published") or "", other))
                scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
                related = [t[2] for t in scored[:3]]
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
            calculator_html = _render_calc_salariu(ent)
        _write(os.path.join(OUT_DIR, "ghiduri", eid, "index.html"),
               ghid_tpl.render(**_base_ctx(
                   f"/ghiduri/{eid}/", ent=ent, categorii=categorii,
                   categorii_icon=categorii_icon, related_news=related,
                   faq_jsonld=faq_jsonld, breadcrumb_jsonld=breadcrumb_jsonld,
                   calculator_html=calculator_html, active_cat=None)))

    _write(os.path.join(OUT_DIR, "ghiduri", "index.html"),
           ghiduri_tpl.render(**_base_ctx(
               "/ghiduri/", categorii=categorii, categorii_icon=categorii_icon,
               entities_by_cat=entities_by_cat)))

    # Instrumente
    tools = [
        {"url": "/instrumente/calculator-salariu/", "icon": "🧮",
         "title": "Calculator salariu net", "desc": "Calculează salariul net în funcție de brut. Datele se actualizează automat."},
    ]
    instr_tpl = env.get_template("instrumente.html")
    _write(os.path.join(OUT_DIR, "instrumente", "index.html"),
           instr_tpl.render(**_base_ctx("/instrumente/", tools=tools)))
    calc_tpl = env.get_template("calculator.html")
    _write(os.path.join(OUT_DIR, "instrumente", "calculator-salariu", "index.html"),
           calc_tpl.render(**_base_ctx("/instrumente/calculator-salariu/")))

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
               "/calendar/", termene=termene,
               now_timestamp=_dt.now().timestamp())))


def _render_calc_salariu(ent: dict) -> str:
    brut = ent.get("valoare_curenta", {}).get("brut", 4050)
    return f"""\n    <h2>🧮 Calculator salariu net</h2>\n    <div class="calculator">\n      <div class="calc-row">\n        <label for="calc-brut">Salariu brut (lei)</label>\n        <div style="display:flex;gap:8px;align-items:center">\n          <input type="number" id="calc-brut" value="{brut}" min="0" step="100" oninput="calcSalariu()">\n          <button type="button" class="btn-preset" onclick="setBrut({brut})">Salariu minim</button>\n          <button type="button" class="btn-preset" onclick="setBrut(5000)">5.000</button>\n          <button type="button" class="btn-preset" onclick="setBrut(10000)">10.000</button>\n        </div>\n      </div>\n      <div class="calc-results" id="calc-results"></div>\n    </div>\n    <p class="calc-note">*Calcul estimativ pentru un angajat fără persoane în întreținere. Include deducerea personală de bază (20% × salariul minim brut). Nu include contribuția la Pilonul II de pensii (3,75% din CAS, opțional).</p>\n    <script>\n    var SM={brut};\n    function setBrut(v){{document.getElementById('calc-brut').value=v;calcSalariu()}}\n    function calcSalariu(){{\n      var b=parseFloat(document.getElementById('calc-brut').value)||0;\n      var cas=Math.round(b*.25),cass=Math.round(b*.1),ded=Math.round(SM*.2);\n      var baza=Math.max(0,b-cas-cass-ded),imp=Math.round(baza*.1),net=b-cas-cass-imp;\n      document.getElementById('calc-results').innerHTML=\n        '<div class="calc-item"><span class="calc-label">CAS (25%)</span><span class="calc-val">-'+cas+' lei</span></div>'\n        +'<div class="calc-item"><span class="calc-label">CASS (10%)</span><span class="calc-val">-'+cass+' lei</span></div>'\n        +'<div class="calc-item"><span class="calc-label">Deducere personală</span><span class="calc-val">'+ded+' lei</span></div>'\n        +'<div class="calc-item"><span class="calc-label">Bază impozabilă</span><span class="calc-val">'+baza+' lei</span></div>'\n        +'<div class="calc-item"><span class="calc-label">Impozit (10%)</span><span class="calc-val">-'+imp+' lei</span></div>'\n        +'<div class="calc-item calc-total"><span class="calc-label">SALARIU NET</span><span class="calc-val">'+net+' lei</span></div>'}}\n    calcSalariu();\n    </script>"""


def _render_utilities(env: Environment, articles: list) -> None:
    """Pagini-utilitate din data/utilities.json: ghiduri actualizate automat."""
    import json as _json
    utils_path = os.path.join(ROOT, "data", "utilities.json")
    if not os.path.exists(utils_path):
        return
    with open(utils_path, "r", encoding="utf-8") as fh:
        all_utils = _json.load(fh)
    utility_tpl = env.get_template("utility.html")
    utilities_tpl = env.get_template("utilities.html")
    # Markdown -> HTML inainte de randare (Jinja2 nu are filtru custom simplu)
    try:
        import markdown as _md_lib
    except ImportError:
        _md_lib = None
    def _render_md(s: str) -> str:
        if _md_lib:
            return _md_lib.markdown(s, extensions=["extra"])
        return "<p>" + s.replace("\n\n", "</p><p>") + "</p>"
    utils_list = []
    for uid, util in all_utils.items():
        util["slug"] = uid
        # Pre-render markdown sections
        for s in (util.get("sections") or []):
            s["content_html"] = _render_md(s.get("content", ""))
        utils_list.append(util)
        # related news by tag match on title
        tags = set((util.get("news_tags") or []))
        related = []
        for a in articles:
            title = (a.get("title") or "").lower()
            if any(t.lower() in title for t in tags):
                related.append(a)
            if len(related) >= 5:
                break
        # FAQPage JSON-LD
        faq_jsonld = {
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": item["question"],
                 "acceptedAnswer": {"@type": "Answer", "text": item["answer"]}}
                for item in util.get("faq", [])
            ]
        }
        breadcrumb_jsonld = {
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": config.SITE["name"], "item": config.SITE["url"] + "/"},
                {"@type": "ListItem", "position": 2, "name": "Utile", "item": config.SITE["url"] + "/utile/"},
                {"@type": "ListItem", "position": 3, "name": util.get("title", uid)},
            ]
        }
        _write(os.path.join(OUT_DIR, "utile", uid, "index.html"),
               utility_tpl.render(**_base_ctx(
                   f"/utile/{uid}/", util=util, util_id=uid, active_cat=None,
                   related_news=related, faq_jsonld=faq_jsonld,
                   breadcrumb_jsonld=breadcrumb_jsonld)))
    # index page
    _write(os.path.join(OUT_DIR, "utile", "index.html"),
           utilities_tpl.render(**_base_ctx("/utile/", utilities=utils_list)))


def _render_legal(env: Environment) -> None:
    _render_md_dir(env, os.path.join(ROOT, "content", "legal"), "/legal")
    # pagini generale (ex. content/pages/despre.md -> /despre/)
    _render_md_dir(env, os.path.join(ROOT, "content", "pages"), "")


def _write_sitemap(articles: list) -> None:
    url = config.SITE["url"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cat_lastmod = {}
    for a in articles:
        c = a.get("category", "")
        d = (a.get("published") or "")[:10]
        if c and d and d > cat_lastmod.get(c, ""):
            cat_lastmod[c] = d
    locs = [(f"{url}/", today)]
    locs += [(f"{url}/{c}/", cat_lastmod.get(c, today)) for c in config.CATEGORIES]
    locs += [(f"{url}/{a['category']}/{a['slug']}/", (a.get("published") or "")[:10]) for a in articles]
    items = "\n".join(
        f"  <url><loc>{xml_escape(l)}</loc>" + (f"<lastmod>{lm}</lastmod>" if lm else "") + "</url>"
        for l, lm in locs)
    _write(os.path.join(OUT_DIR, "sitemap.xml"),
           '<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{items}\n</urlset>\n")
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


def _write_search(env: Environment, articles: list) -> None:
    """Pagina /cauta/ + index JSON mic (titluri) pentru cautarea client-side."""
    import json as _json
    idx = [{"t": a.get("title", ""), "u": f"/{a['category']}/{a['slug']}/",
            "c": a.get("category", ""), "d": a.get("published_human", "")} for a in articles]
    _write(os.path.join(OUT_DIR, "search-index.json"), _json.dumps(idx, ensure_ascii=False))
    _write(os.path.join(OUT_DIR, "cauta", "index.html"),
           env.get_template("search.html").render(**_base_ctx("/cauta/")))


def _write_robots() -> None:
    _write(os.path.join(OUT_DIR, "robots.txt"),
           f"User-agent: *\nAllow: /\nSitemap: {config.SITE['url']}/sitemap.xml\n"
           f"Sitemap: {config.SITE['url']}/sitemap-images.xml\n")


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
