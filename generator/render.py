"""Randare SSG cu Jinja2 (autoescape ON) -> output/. Permalink-uri, sitemap, robots, feed, JSON-LD."""
import os
import shutil
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape

from jinja2 import Environment, FileSystemLoader, select_autoescape
from slugify import slugify

from . import config

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
        "url": f"{config.SITE['url']}/{a['category']}/{a['slug']}.html",
        "inLanguage": config.SITE["lang"],
        "publisher": {"@type": "Organization", "name": config.SITE["name"]},
        "isBasedOn": [s["url"] for s in a.get("sources", [])] or a.get("original_link", ""),
    }


def _base_ctx(canonical_path: str, **extra) -> dict:
    ctx = {
        "site": config.SITE,
        "categories": config.CATEGORIES,
        "year": datetime.now().year,
        "canonical": config.SITE["url"] + canonical_path,
        "org_jsonld": _org_jsonld(),
        "analytics_token": os.getenv("CF_ANALYTICS_TOKEN", "").strip() or None,
        "active_cat": None,
    }
    ctx.update(extra)
    return ctx


def _pick_hero(articles: list) -> list:
    featured = [a for a in articles if a.get("featured")]
    rest = [a for a in articles if not a.get("featured")]
    rest_sorted = sorted(rest, key=lambda a: (a.get("model") != "C", a.get("published") or ""),
                         reverse=False)
    # C-urile si cele mai recente in fata
    rest_sorted = sorted(rest, key=lambda a: a.get("published") or "", reverse=True)
    rest_sorted = sorted(rest_sorted, key=lambda a: a.get("model") != "C")
    return (featured + rest_sorted)[:3]


def build(articles: list, mod: dict | None = None) -> None:
    env = _env()
    _assign_slugs(articles)

    # reset output, copiaza static
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)
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
             "url": f"{config.SITE['url']}/{a['category']}/{a['slug']}.html"}
            for i, a in enumerate(by_date[:20])
        ],
    }
    _write(os.path.join(OUT_DIR, "index.html"),
           env.get_template("index.html").render(**_base_ctx(
               "/", articles=by_date, hero=hero, by_category=by_category,
               page_jsonld=item_list)))

    # pagini de categorie + permalink articole
    article_tpl = env.get_template("article.html")
    cat_tpl = env.get_template("category.html")
    for cat in config.CATEGORIES:
        items = [a for a in by_date if a.get("category") == cat]
        _write(os.path.join(OUT_DIR, cat, "index.html"),
               cat_tpl.render(**_base_ctx(f"/{cat}/", category=cat, articles=items, active_cat=cat)))
        for a in items:
            _write(os.path.join(OUT_DIR, cat, f"{a['slug']}.html"),
                   article_tpl.render(**_base_ctx(
                       f"/{cat}/{a['slug']}.html", a=a, active_cat=cat,
                       article_jsonld=_article_jsonld(a))))

    _render_legal(env)
    _write(os.path.join(OUT_DIR, "404.html"),
           env.get_template("category.html").render(**_base_ctx(
               "/404.html", category="Pagina negăsită", articles=[])))
    _write_sitemap(by_date)
    _write_robots()
    _write_feed(by_date)


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
        _write(os.path.join(OUT_DIR, "legal", f"{name}.html"),
               tpl.render(**_base_ctx(f"/legal/{name}.html", page_title=title,
                                      body_html=html, page_heading=title)))


def _write_sitemap(articles: list) -> None:
    url = config.SITE["url"]
    locs = [f"{url}/", *[f"{url}/{c}/" for c in config.CATEGORIES]]
    locs += [f"{url}/{a['category']}/{a['slug']}.html" for a in articles]
    items = "\n".join(f"  <url><loc>{xml_escape(l)}</loc></url>" for l in locs)
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
        link = f"{url}/{a['category']}/{a['slug']}.html"
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
