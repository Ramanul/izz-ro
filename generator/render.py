"""Randare SSG cu Jinja2 (autoescape ON) -> output/. Permalink-uri, sitemap, robots, feed, JSON-LD."""
import os
import shutil
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape

from jinja2 import Environment, FileSystemLoader, select_autoescape
from slugify import slugify

from . import config
from .util import title_tokens

ROOT = config.ROOT
TPL_DIR = os.path.join(ROOT, "templates")
STATIC_DIR = os.path.join(ROOT, "static")
OUT_DIR = os.path.join(ROOT, "output")

_RO_MONTHS = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
              "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"]


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TPL_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True, lstrip_blocks=True,
    )


def _human_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return ""
    return f"{dt.day} {_RO_MONTHS[dt.month]} {dt.year}, {dt:%H:%M}"


def _assign_slugs(articles: list) -> None:
    """Slug unic per categorie din titlu (permalink stabil, indexabil)."""
    seen: dict = {}
    for a in articles:
        base = slugify(a.get("title") or a.get("original_title") or "stire") or "stire"
        key = (a.get("category", "general"), base)
        n = seen.get(key, 0) + 1
        seen[key] = n
        a["slug"] = base if n == 1 else f"{base}-{n}"
        a["published_human"] = _human_date(a.get("published", ""))


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _org_jsonld() -> dict:
    return {
        "@context": "https://schema.org", "@type": "Organization",
        "name": config.SITE["name"], "url": config.SITE["url"],
        "logo": config.SITE["url"] + "/static/logo.svg",
        "email": config.SITE["contact"],
        "description": config.SITE["tagline"],
    }


def _article_jsonld(a: dict) -> dict:
    body = a.get("synthesis") if a.get("model") == "C" else a.get("teaser")
    return {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "headline": a.get("title", ""),
        "description": body or "",
        "datePublished": a.get("published", ""),
        "dateModified": a.get("published", ""),
        "url": f"{config.SITE['url']}/{a['category']}/{a['slug']}/",
        "mainEntityOfPage": f"{config.SITE['url']}/{a['category']}/{a['slug']}/",
        "inLanguage": config.SITE["lang"],
        "author": {"@type": "Organization", "name": config.SITE["name"]},
        "publisher": {"@type": "Organization", "name": config.SITE["name"]},
        "isBasedOn": [s["url"] for s in a.get("sources", [])] or a.get("original_link", ""),
    }


def _base_ctx(canonical_path: str, **extra) -> dict:
    ctx = {
        "site": config.SITE,
        "base": os.getenv("SITE_BASE", "").rstrip("/"),
        "categories": config.CATEGORIES,
        "year": datetime.now().year,
        "canonical": config.SITE["url"] + canonical_path,
        "org_jsonld": _org_jsonld(),
        "analytics_token": os.getenv("CF_ANALYTICS_TOKEN", "").strip() or None,
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


def _pick_hero(articles: list) -> list:
    featured = [a for a in articles if a.get("featured")]
    rest = [a for a in articles if not a.get("featured")]
    # prioritate: AI (gemini) inaintea fallback, apoi clustere C, apoi cele mai recente
    rest_sorted = sorted(rest, key=lambda a: a.get("published") or "", reverse=True)
    rest_sorted.sort(key=lambda a: (a.get("processed_by") != "gemini", a.get("model") != "C"))
    return (featured + rest_sorted)[:6]


def _dedup_sources(a: dict) -> None:
    """Surse unice dupa nume (evita 'Digi Sport x3' pe acelasi card)."""
    seen, out = set(), []
    for s in a.get("sources") or []:
        if s.get("name") in seen:
            continue
        seen.add(s.get("name"))
        out.append(s)
    if out:
        a["sources"] = out


def build(articles: list, mod: dict | None = None) -> None:
    env = _env()
    articles = _dedup(articles)
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

    by_date = sorted(articles, key=lambda a: a.get("published") or "", reverse=True)
    hero = _pick_hero(by_date)
    hero_urls = {a["url"] for a in hero}

    by_category = {}
    for cat in config.CATEGORIES:
        by_category[cat] = [a for a in by_date if a.get("category") == cat and a["url"] not in hero_urls]

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

    # pagini de categorie + permalink articole
    article_tpl = env.get_template("article.html")
    cat_tpl = env.get_template("category.html")
    for cat in config.CATEGORIES:
        items = [a for a in by_date if a.get("category") == cat]
        _write(os.path.join(OUT_DIR, cat, "index.html"),
               cat_tpl.render(**_base_ctx(f"/{cat}/", category=cat, articles=items, active_cat=cat)))
        for a in items:
            _write(os.path.join(OUT_DIR, cat, a['slug'], "index.html"),
                   article_tpl.render(**_base_ctx(
                       f"/{cat}/{a['slug']}/", a=a, active_cat=cat,
                       article_jsonld=_article_jsonld(a))))

    _render_legal(env)
    _write(os.path.join(OUT_DIR, "404.html"),
           env.get_template("category.html").render(**_base_ctx(
               "/404.html", category="Pagina negăsită", articles=[])))
    _write_sitemap(by_date)
    _write_robots()
    _write_feed(by_date)


def _newsletter_html() -> str:
    """Embed-ul Brevo, daca utilizatorul l-a pus in content/newsletter.html; altfel placeholder."""
    path = os.path.join(ROOT, "content", "newsletter.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return ('<p class="summary">Primește rezumatul zilei pe e-mail. '
            'Formularul de înscriere (Brevo, cu confirmare dublă) va apărea aici.</p>'
            '<p class="meta">Configurare: lipește codul de embed din contul Brevo în '
            '<code>content/newsletter.html</code>.</p>')


def _render_legal(env: Environment) -> None:
    """Randeaza content/legal/*.md la /legal/*.html daca exista (Faza 4)."""
    legal_dir = os.path.join(ROOT, "content", "legal")
    if not os.path.isdir(legal_dir):
        return
    try:
        import markdown as md
    except ImportError:
        md = None
    tpl = env.get_template("legal.html") if os.path.exists(os.path.join(TPL_DIR, "legal.html")) else None
    if not tpl:
        return
    for fn in os.listdir(legal_dir):
        if not fn.endswith(".md"):
            continue
        name = fn[:-3]
        with open(os.path.join(legal_dir, fn), "r", encoding="utf-8") as fh:
            raw = fh.read()
        title = raw.lstrip("# ").splitlines()[0].strip() if raw.startswith("#") else name
        html = md.markdown(raw, extensions=["extra"]) if md else "<pre>" + raw + "</pre>"
        _write(os.path.join(OUT_DIR, "legal", name, "index.html"),
               tpl.render(**_base_ctx(f"/legal/{name}/", page_title=title,
                                      body_html=html, page_heading=title)))


def _write_sitemap(articles: list) -> None:
    url = config.SITE["url"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    locs = [(f"{url}/", today), *[(f"{url}/{c}/", today) for c in config.CATEGORIES]]
    locs += [(f"{url}/{a['category']}/{a['slug']}/", (a.get("published") or "")[:10]) for a in articles]
    items = "\n".join(
        f"  <url><loc>{xml_escape(l)}</loc>" + (f"<lastmod>{lm}</lastmod>" if lm else "") + "</url>"
        for l, lm in locs)
    _write(os.path.join(OUT_DIR, "sitemap.xml"),
           '<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{items}\n</urlset>\n")


def _write_robots() -> None:
    _write(os.path.join(OUT_DIR, "robots.txt"),
           f"User-agent: *\nAllow: /\nSitemap: {config.SITE['url']}/sitemap.xml\n")


def _write_feed(articles: list) -> None:
    url = config.SITE["url"]
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    entries = []
    for a in articles[:50]:
        body = a.get("synthesis") if a.get("model") == "C" else a.get("teaser")
        link = f"{url}/{a['category']}/{a['slug']}/"
        entries.append(
            "    <item>\n"
            f"      <title>{xml_escape(a.get('title',''))}</title>\n"
            f"      <link>{xml_escape(link)}</link>\n"
            f"      <guid>{xml_escape(link)}</guid>\n"
            f"      <description>{xml_escape(body or '')}</description>\n"
            "    </item>")
    _write(os.path.join(OUT_DIR, "feed.xml"),
           '<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0"><channel>\n'
           f"  <title>{config.SITE['name']}</title>\n"
           f"  <link>{url}</link>\n"
           f"  <description>{config.SITE['tagline']}</description>\n"
           f"  <language>{config.SITE['lang']}</language>\n"
           f"  <lastBuildDate>{now}</lastBuildDate>\n"
           + "\n".join(entries) +
           "\n</channel></rss>\n")
