"""Randare SSG cu Jinja2 (autoescape ON) -> output/. Permalink-uri, sitemap, robots, feed, JSON-LD."""
import logging
import math
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
# `saxutils.escape` NU parseaza nimic: primeste un str si intoarce un str cu &<> inlocuite.
# Regula semgrep marcheaza modulul `xml.sax`, nu apelul, iar `defusedxml` nici macar nu ofera
# un inlocuitor pentru functia asta. ID-ul e scris COMPLET intentionat: forma scurta
# (`use-defused-xml`) nu se potriveste si suprimarea trece tacut pe langa constatare —
# verificat prin rulare, dupa ce prima incercare a lasat-o in continuare rosie.
# nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
from xml.sax.saxutils import escape as xml_escape

from jinja2 import Environment, FileSystemLoader, select_autoescape
from slugify import slugify

from . import config, covers, geo, htmlart
from .select import (_dedup, _dedup_sources, _diversify, _entity_index,
                     _pick_hero, _quality_gate, anunt_oficial_fara_corp, filtru_cautare_rapida,
                     titlu_afisare)
# Re-export DELIBERAT, nu import mort: `tests/test_render_editorial.py` le cheama ca
# `render._slug_stems` / `render.sources_coherent` (9 apeluri), iar `tools/qa_check.py:18`
# importa `sources_coherent` din `generator.render`, nu din `generator.select` — si scriptul
# ala ruleaza in pipeline (`build.yml:106`). Un `ruff --fix` aici pica productia, nu doar
# suita. Instructiune separata pentru ca o exceptie de lint pusa pe prima linie a unui import
# in paranteze NU acopera numele de pe continuari — verificat, nu presupus.
from .select import _slug_stems, sources_coherent  # noqa: F401
from .util import domain_of

ROOT = config.ROOT
TPL_DIR = os.path.join(ROOT, "templates")
STATIC_DIR = os.path.join(ROOT, "static")
OUT_DIR = os.path.join(ROOT, "output")
MEDIA_DIR = os.path.join(ROOT, "media")   # imagini HTML/Chromium comise (tools/gen_images.py)
PAGE_SIZE = 20        # articole pe pagina de categorie
PAGE_WINDOW = 2       # cate numere se arata de o parte si de alta a paginii curente
PORTRAITS_JSON = os.path.join(ROOT, "data", "portraits.json")
LEADPHOTOS_JSON = os.path.join(ROOT, "data", "leadphotos.json")

# Coperțile apar pe carduri, în hero și în previzualizări sociale, unde creditul complet
# nu poate fi garantat. Prin urmare, acestea acceptă doar active fără obligație de atribuire.
# Regex-ul este intenționat strict: orice licență necunoscută ori CC BY/CC BY-SA cade pe
# coperta internă, nu pe fotografia terță.
_CREDIT_FREE_LICENSE = re.compile(r"^(cc0|cc[ -]?zero|public domain|pd([ -]|$))", re.I)


def _is_credit_free_license(license_name: str | None) -> bool:
    return bool(_CREDIT_FREE_LICENSE.match((license_name or "").strip()))


def _leadphoto_is_publication_safe(rec: dict) -> bool:
    """Validează o intrare din cache înainte ca fotografia să ajungă în orice zonă publică.

    `leadphotos.json` este un cache istoric; validarea aici protejează și intrările create
    înainte de regula actuală. O fotografie cu credit obligatoriu rămâne permisă doar în
    contexte cu legendă completă, nu ca imagine LEAD.
    """
    required = ("cover", "art", "webp", "license", "page", "name")
    return bool(rec) and not rec.get("miss") and all(rec.get(key) for key in required) and \
        _is_credit_free_license(rec.get("license"))


def _load_leadphotos() -> dict:
    """Fotografii LEAD per articol, admise numai dacă nu cer credit obligatoriu.

    Imaginile neeligibile sunt ignorate la randare, inclusiv cele din cache-ul vechi; articolul
    revine automat la coperta grafică internă. Lipsa fișierului ori a unei intrări conforme
    nu blochează build-ul.
    """
    try:
        import json as _json
        cache = _json.load(open(LEADPHOTOS_JSON, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    safe = {k: v for k, v in cache.items() if _leadphoto_is_publication_safe(v)}
    # Nu copiem întregul cache istoric în output: un fișier cu licență neeligibilă nu trebuie
    # să rămână public accesibil doar fiindcă nu mai este referit de HTML.
    for rec in safe.values():
        for field in ("cover", "art", "webp"):
            rel = rec[field]
            _use_media(os.path.join(MEDIA_DIR, rel), os.path.join(OUT_DIR, rel))
    return safe


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


def _responsive_webp(src: str, dst: str, max_width: int = 480) -> bool:
    """Scrie o varianta WebP mica numai cand aduce economie reala.

    Nu generam derivata pentru fiecare articol: Pages Free are plafon de fisiere, iar
    o copie pe toate permalinkurile ar apropia deploy-ul de limita. Este folosita doar
    pentru cardurile de pe homepage, exact zona unde Lighthouse a masurat imagini prea
    mari fata de suprafata afisata.
    """
    image = getattr(covers, "Image", None)
    if image is None:
        return False
    try:
        with image.open(src) as im:
            if im.width <= max_width:
                return False
            ratio = max_width / im.width
            size = (max_width, max(1, round(im.height * ratio)))
            resampling = getattr(image, "Resampling", image).LANCZOS
            out = im.convert("RGB").resize(size, resampling)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            out.save(dst, "WEBP", quality=72, method=4)
            return os.path.getsize(dst) > 1000
    except (OSError, ValueError):
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


def _taie_slug(s: str, limita: int = 80, minim: int = 40) -> str:
    """Taie la limita de cuvant, nu la mijloc: `...pentru-masuri-de-econom` citea ca output
    de masina. Masurat pe arhiva de 7001 articole: 1254 (17.9%) erau taiate la mijloc.

    `minim` e garda pentru cazul patologic — un titlu cu un cuvant foarte lung exact peste
    limita ar fi retezat la nimic daca am da mereu inapoi pana la ultima cratima. Sub prag,
    taietura brutala ramane preferabila unui slug de doua cuvinte.
    """
    if len(s) <= limita:
        return s
    taiat = s[:limita]
    i = taiat.rfind("-")
    return taiat[:i] if i >= minim else taiat


def assign_slugs(articles: list) -> None:
    """Slug unic per categorie din titlu — atribuit O SINGURA DATA, la prima publicare.

    Slug-ul e permalink-ul public, iar titlul se poate schimba DUPA publicare: un bump de
    `PROMPT_VERSION` reprocesează articolele B, iar o sinteză C care absoarbe o știre nouă
    își rescrie titlul (decizie IZZ-0151). Cat timp slug-ul se recalcula din titlu la fiecare
    randare, fiecare astfel de rescriere muta URL-ul unei pagini deja indexate. De aceea
    articolul care ARE deja `slug` il pastreaza neatins, iar `main.run` atribuie inainte de
    `state.save` ca slug-ul sa intre in stare si sa supravietuiasca intre rulari.

    Doua treceri: slug-urile deja publicate isi rezerva locul intai, ca un titlu nou identic
    sa primeasca sufixul numeric, nu invers.
    """
    luate: set = set()
    for a in articles:
        if a.get("slug"):
            luate.add((a.get("category", "general"), a["slug"]))
    for a in articles:
        if a.get("slug"):
            continue
        base = _taie_slug(slugify(a.get("title") or a.get("original_title") or "stire") or "stire")
        # Un slug pur numeric ar ocupa /<cat>/2/, adica exact calea unei pagini de paginare —
        # iar articolele se scriu DUPA paginile de listare, deci ar suprascrie-o tacut si
        # linkul „2" din navigatie ar deschide un articol. Azi 0 din 1733 de titluri produc
        # asa ceva, dar coliziunea e o proprietate a cailor, nu a corpusului de azi.
        if base.isdigit():
            base = f"stirea-{base}"
        cat = a.get("category", "general")
        slug, n = base, 1
        while (cat, slug) in luate:
            n += 1
            slug = f"{base}-{n}"
        luate.add((cat, slug))
        a["slug"] = slug


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


# --- JSON-LD: UN singur document per pagina, cu `@graph` --------------------------------
# Inainte, fiecare `<script type="application/ld+json">` era un document independent, cu
# `@context` propriu si fara niciun `@id`. Consecinta pe o pagina de articol: Organization
# aparea de trei ori (nodul din base.html, `author`, `publisher`) ca trei entitati fara
# legatura intre ele, iar nimic nu spunea ca articolul si pagina sunt acelasi lucru.
# Cu `@graph`, entitatea se declara O DATA si se refera prin `{"@id": ...}`.


def _abs_id(path: str, role: str) -> str:
    """`@id` absolut si STABIL: URL-ul canonic al paginii + un fragment care spune ce rol are
    nodul. Derivat din URL, NICIODATA dintr-un indice de pozitie — un `@id` care se schimba de
    la o randare la alta descrie o entitate noua de fiecare data, adica exact ce evitam aici."""
    return f"{config.SITE['url']}{path}#{role}"


def _logo_jsonld() -> dict:
    return {"@type": "ImageObject", "@id": _abs_id("/", "logo"),
            "url": config.SITE["url"] + "/static/logo.png",
            "width": 512, "height": 512}


def _org_jsonld() -> dict:
    return {
        "@type": "Organization", "@id": _abs_id("/", "organization"),
        "name": config.SITE["name"], "url": config.SITE["url"],
        "logo": _logo_jsonld(),
        "email": config.SITE["contact"],
        "description": config.SITE["tagline"],
    }


def _website_jsonld() -> dict:
    """Nodul WebSite — de acolo isi ia Google numele de site afisat in rezultate.
    FARA `potentialAction`/`SearchAction`: sitelinks search box a fost depreciat si scos din
    rezultate pe 21 noiembrie 2024, deci marcajul ala nu mai are consumator (WS-0019 respins,
    cu sursa). Nodul in sine a ramas suportat — a disparut doar actiunea."""
    return {
        "@type": "WebSite", "@id": _abs_id("/", "website"),
        "url": config.SITE["url"] + "/",
        "name": config.SITE["name"],
        "description": config.SITE["tagline"],
        "inLanguage": config.SITE["lang"],
        "publisher": {"@id": _abs_id("/", "organization")},
    }


def _graph_jsonld(canonical_path: str, nodes: list, page: dict | None = None) -> dict:
    """Documentul JSON-LD al unei pagini: un singur `@context`, un singur `@graph`.

    `nodes` = nodurile specifice paginii (NewsArticle, BreadcrumbList, ItemList).
    `page`  = proprietati in plus pe nodul WebPage (`name`, un `@type` mai specific).

    Legaturile WebPage -> `breadcrumb` / `mainEntity` se deduc AICI din tipul nodurilor, nu se
    scriu la fiecare apel: un apel care le-ar uita ar produce noduri orfane in graf, si nimic
    nu s-ar plange. `setdefault` ca sa nu calce peste ce a cerut explicit apelantul."""
    wp = {
        "@type": "WebPage", "@id": _abs_id(canonical_path, "webpage"),
        "url": config.SITE["url"] + canonical_path,
        "isPartOf": {"@id": _abs_id("/", "website")},
        "inLanguage": config.SITE["lang"],
    }
    wp.update(page or {})
    for n in nodes:
        if n.get("@type") == "BreadcrumbList":
            wp.setdefault("breadcrumb", {"@id": n["@id"]})
        elif n.get("@type") in ("NewsArticle", "ItemList"):
            wp.setdefault("mainEntity", {"@id": n["@id"]})
    return {"@context": "https://schema.org",
            "@graph": [_org_jsonld(), _website_jsonld(), wp, *nodes]}


def _article_jsonld(a: dict) -> dict:
    body = a.get("synthesis") if a.get("model") == "C" else a.get("teaser")
    path = f"/{a['category']}/{a['slug']}/"
    return {
        "@type": "NewsArticle", "@id": _abs_id(path, "article"),
        "headline": a.get("title", ""),
        "description": body or "",
        "image": [config.SITE["url"] + "/static/og-image.png"],
        "datePublished": a.get("published", ""),
        # o sinteza care a absorbit o stire noua isi pastreaza slug-ul si `published`, dar are
        # alt continut (IZZ-0151) -> `updated` e singurul semnal onest pentru motoarele de cautare
        "dateModified": a.get("updated") or a.get("published", ""),
        "url": config.SITE["url"] + path,
        "mainEntityOfPage": {"@id": _abs_id(path, "webpage")},
        "inLanguage": config.SITE["lang"],
        # referinte, nu copii: Organization e declarata o singura data, in acelasi graf
        "author": {"@id": _abs_id("/", "organization")},
        "publisher": {"@id": _abs_id("/", "organization")},
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


def _base_ctx(canonical_path: str, jsonld_nodes: list | None = None,
              jsonld_page: dict | None = None, **extra) -> dict:
    ctx = {
        "site": config.SITE,
        "base": os.getenv("SITE_BASE", "").rstrip("/"),
        "categories": config.CATEGORIES,
        # UTC explicit: pipeline-ul randeaza pe runnere GitHub, care sunt oricum pe UTC, deci
        # asta nu schimba anul din subsol in productie — face doar ca o randare locala
        # (UTC+3) sa dea acelasi octet ca CI-ul, in loc sa depinda de ceasul masinii.
        "year": datetime.now(timezone.utc).year,
        "canonical": config.SITE["url"] + canonical_path,
        # UN singur bloc `application/ld+json` per pagina, emis din base.html
        "jsonld": _graph_jsonld(canonical_path, jsonld_nodes or [], jsonld_page),
        "analytics_token": os.getenv("CF_ANALYTICS_TOKEN", "").strip() or None,
        "fonts_css": _fonts_css(),
        "asset_ver": _asset_ver(),
        "active_cat": None,
    }
    ctx.update(extra)
    return ctx


def _cat_page_path(cat: str, n: int) -> str:
    """Calea unei pagini de categorie; pagina 1 sta pe /cat/, nu pe /cat/1/."""
    return f"/{cat}/" if n <= 1 else f"/{cat}/{n}/"


def _pagination(cat: str, page_num: int, total_pages: int) -> dict | None:
    """Navigatia dintre paginile unei categorii. None cand nu e nimic de navigat.

    Sablonul afisa 1-2-3 fix, pe pagina 1 si numai acolo. Doua consecinte masurate pe
    randarea din 2026-08-03: la categoriile cu exact 2 pagini linkul spre /3/ era mort
    (general, politic, tech), iar din cele 79 de pagini randate 44 nu erau linkate de
    nicaieri — nici din sitemap, care nu contine paginare deloc. `zonal` randa 20 de
    pagini si oprea navigatia la 3.

    Fereastra de mai jos tine numarul de linkuri mic si garanteaza in acelasi timp ca
    fiecare pagina e la un pas de vecinele ei: prima, ultima, si +/-PAGE_WINDOW in jurul
    celei curente, deci orice pagina se atinge prin parcurgere.
    """
    if total_pages <= 1:
        return None
    shown = {1, total_pages, page_num}
    shown |= {n for n in range(page_num - PAGE_WINDOW, page_num + PAGE_WINDOW + 1)
              if 1 <= n <= total_pages}
    pages: list = []
    prev_n = 0
    for n in sorted(shown):
        if prev_n and n != prev_n + 1:
            pages.append(None)                    # salt in numerotare; sablonul pune „…"
        pages.append({"n": n, "path": None if n == page_num else _cat_page_path(cat, n)})
        prev_n = n
    return {
        "current": page_num,
        "total": total_pages,
        "pages": pages,   # NU „items": in Jinja, dict.items e metoda, nu cheia
        "prev": _cat_page_path(cat, page_num - 1) if page_num > 1 else None,
        "next": _cat_page_path(cat, page_num + 1) if page_num < total_pages else None,
    }


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


_HARTA_CACHE: dict | None = None


def _harta_judete(catalog: list) -> dict | None:
    """Conturul SVG al judetelor + ancora catre sectiunea fiecaruia de pe /surse/.

    Bara pusa de owner cand harta a fost amanata (`specs/istoric-executie.md`): SVG STATIC,
    linkuri TEXT inauntru, ZERO JS, fara layout shift, pa11y sa ramana 0. De-aia harta e
    inline (nicio cerere in plus), fiecare judet cu surse e un `<a>` cu `<title>` — deci are
    nume accesibil si functioneaza fara JavaScript — iar judetele FARA surse raman desenate,
    dar inerte: o tara intreaga, fara linkuri moarte.

    Returneaza None daca fisierul de contur lipseste; pagina se randeaza atunci fara harta,
    nu crapa. Datele vin din `tools/build_harta.py` (Natural Earth, domeniu public).
    """
    global _HARTA_CACHE
    if _HARTA_CACHE is None:
        try:
            with open(os.path.join(config.ROOT, "data", "harta_judete.json"),
                      encoding="utf-8") as fh:
                _HARTA_CACHE = json.load(fh)
        except (OSError, ValueError):
            _HARTA_CACHE = {}
    if not _HARTA_CACHE.get("judete"):
        return None

    # Ancorele exista doar pentru judetele care chiar au o sectiune in pagina.
    ancore: dict = {}
    for group in catalog:
        for region in group.get("regions", []):
            for county in region["counties"]:
                if county.get("judet"):
                    ancore[county["judet"]] = county

    forme = []
    for judet, d in _HARTA_CACHE["judete"].items():
        county = ancore.get(judet)
        forme.append({
            "judet": judet,
            "label": geo.eticheta_judet(judet),
            "d": d,
            "anchor": county["anchor"] if county else None,
            "count": county["count"] if county else 0,
        })
    return {"viewbox": _HARTA_CACHE.get("viewbox", "0 0 1000 704"),
            "forme": forme,
            "cu_surse": sum(1 for f in forme if f["anchor"])}


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
            "judet": judet,
            "anchor": "jud-" + slugify(judet),
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
        # Anunt oficial fara corp -> forma „titlu + link". Teaserul se goleste AICI, o data,
        # in loc sa stie fiecare sablon ce e un placeholder: cele 69 de anunturi deja in state
        # poarta literal "Detalii pe sursa.", deci un simplu `{% if a.teaser %}` in sablon
        # l-ar tipari. Marcajul `anunt_fara_corp` e ce citesc sabloanele.
        a["anunt_fara_corp"] = anunt_oficial_fara_corp(a)
        a["display_title"] = titlu_afisare(a)
        if a["anunt_fara_corp"]:
            a["teaser"] = ""
        # Marcaj AI Act art. 50(4), obligatoriu de la 2026-08-02: textul publicat pentru
        # informarea publicului si generat de AI trebuie dezvaluit. Exceptia (verificare
        # umana SI raspundere editoriala) cere ambele conditii; pipeline-ul publica fara ca
        # un om sa citeasca fiecare titlu, deci nu se aplica. Vezi REGULI-SINTEZA.md §4.
        #
        # Doua fluxuri NU ating modelul si deci NU se marcheaza — un marcaj fals ar sugera
        # ca stirea e fabricata, exact eroarea inversa:
        #   "official" -> titlul emis de institutie, publicat exact (process.py:301)
        #   "fallback" -> providerul lipseste, se copiaza original_title (process.py:378)
        # Articolele vechi fara `processed_by` se marcheaza: toate au trecut prin model B/C,
        # iar golul de conformitate e eroarea mai scumpa dintre cele doua.
        a["ai_generat"] = a.get("processed_by") not in ("official", "fallback")
    assign_slugs(articles)
    # data formatata e artefact de AFISARE, nu identitate: se recalculeaza la fiecare randare
    # si nu are ce cauta in stare (`assign_slugs` ruleaza acum si inainte de `state.save`).
    for a in articles:
        a["published_human"] = _human_date(a.get("published", ""))
        # `updated` exista numai cand un cluster deja publicat a absorbit informatie noua.
        # Pastram lipsa lui distincta de data publicarii: un cititor trebuie sa poata vedea
        # daca textul a fost revizuit, fara sa pretindem o verificare care nu a avut loc.
        a["updated_human"] = _human_date(a.get("updated", ""))

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
    except (Exception, SystemExit) as e:
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
        # Homepage-ul ramane un tablou de bord: limita configurabila pastreaza orientarea
        # rapida, iar arhiva completa ramane pe pagina categoriei.
        items = [a for a in by_date if a.get("category") == cat and a["url"] not in hero_urls]
        by_category[cat] = _diversify(items)[:config.HOME_CARDS_PER_CATEGORY]

    # Variantele mici se emit doar pentru cardurile homepage-ului (nu pentru toate
    # permalinkurile) — economie in primul viewport, sub plafonul gratuit de fisiere Pages.
    homepage_cards = {a["url"] for a in hero[1:]}
    homepage_cards.update(a["url"] for items in by_category.values() for a in items)
    for a in by_date:
        if a["url"] not in homepage_cards or not a.get("art_path"):
            continue
        card_dst = os.path.join(OUT_DIR, a["category"], a["slug"], "art-card.webp")
        source = os.path.join(OUT_DIR, a["category"], a["slug"], "art.webp")
        if not os.path.isfile(source):
            source = os.path.join(OUT_DIR, a["category"], a["slug"], "art.jpg")
        if _responsive_webp(source, card_dst):
            a["art_card_webp"] = f"/{a['category']}/{a['slug']}/art-card.webp?v={_content_ver(card_dst)}"

    # homepage
    item_list = {
        "@type": "ItemList", "@id": _abs_id("/", "itemlist"),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "url": f"{config.SITE['url']}/{a['category']}/{a['slug']}/"}
            for i, a in enumerate(by_date[:20])
        ],
    }
    _write(os.path.join(OUT_DIR, "index.html"),
           env.get_template("index.html").render(**_base_ctx(
               "/", nav_section="stiri", articles=by_date, hero=hero, by_category=by_category,
               jsonld_nodes=[item_list], newsletter_html=_newsletter_html())))

    src_catalog, total_sources, stats_sources = _source_catalog(by_date)
    _write(os.path.join(OUT_DIR, "surse", "index.html"),
           env.get_template("surse.html").render(**_base_ctx(
               "/surse/", catalog=src_catalog, total_sources=total_sources,
               stats_sources=stats_sources, ttl_days=config.ARTICLE_TTL_DAYS,
               harta=_harta_judete(src_catalog))))

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
                             f"Știri despre {d['name']} pe {config.SITE['name']}",
                             feed_url=f"{config.SITE['url']}/subiect/{s}/feed.xml"))

    # pagini de categorie + permalink articole
    article_tpl = env.get_template("article.html")
    cat_tpl = env.get_template("category.html")
    for cat in config.CATEGORIES:
        items = [a for a in by_date if a.get("category") == cat]
        total_pages = max(1, math.ceil(len(items) / PAGE_SIZE))
        # si categoriile inca goale (in insamantare) primesc pagina 1 — altfel nav-ul ar duce la 404
        for page in range(0, max(len(items), 1), PAGE_SIZE):
            page_items = _diversify(items[page:page + PAGE_SIZE])
            page_num = page // PAGE_SIZE + 1
            page_dir = os.path.join(OUT_DIR, cat) if page_num == 1 else os.path.join(OUT_DIR, cat, str(page_num))
            _write(os.path.join(page_dir, "index.html"),
                   cat_tpl.render(**_base_ctx(
                       _cat_page_path(cat, page_num),
                       category=cat, articles=page_items, active_cat=cat,
                       pagination=_pagination(cat, page_num, total_pages))))
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
                "@type": "BreadcrumbList",
                "@id": _abs_id(f"/{cat}/{a['slug']}/", "breadcrumb"),
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
                       jsonld_nodes=[jsonld, breadcrumb_jsonld],
                       jsonld_page={"name": a.get("title", "")})))

    _render_legal(env)
    _render_sections(env)
    _render_ghiduri(env, by_date)
    # Pagina 404 nu e o categorie goala, e capatul unui link mort — si cel mai frecvent motiv
    # NU e o adresa gresita, ci un articol EXPIRAT. `config.ARTICLE_TTL_DAYS = 7`, iar
    # `state.expire()` scoate articolul din stare, deci pagina lui nu se mai randeaza:
    # orice permalink partajat moare intr-o saptamana. Masurat pe live 8/8, cu control pozitiv
    # (articol viu -> 200) si negativ (articol expirat -> 404) — vezi
    # handoff/arhiva/2026-08-06-handoff-integral.md.
    #
    # Pana acum pagina asta afisa „Nicio stire in aceasta categorie deocamdata", fiindca
    # primea `articles=[]` si cadea pe starea goala a sablonului de categorie. Adica raspundea
    # la alta intrebare decat cea pusa de vizitator.
    #
    # Asta NU repara expirarea — aia cere o decizie de proprietar, fiindca e marginita tare:
    # planul gratuit Cloudflare Pages da 20.000 de fisiere pe site (documentatie, verificat
    # 2026-08-07), iar `output/` are azi 10.997 la ~3,5 fisiere/articol, deci TTL-ul nu poate
    # trece realist de ~14 zile. Aici se repara doar capatul: spune ce s-a intamplat si da
    # vizitatorului stirile de acum, in loc sa-l lase intr-o fundatura.
    _write(os.path.join(OUT_DIR, "404.html"),
           env.get_template("category.html").render(**_base_ctx(
               "/404.html", category="Pagina negăsită",
               intro="Adresa nu există sau articolul a expirat. Între timp, ce e nou:",
               articles=by_date[:12])))
    _write_sitemap(by_date)
    _write_build_metadata(len(by_date))
    _write_robots()
    _write_security_txt()
    # dovada de domeniu pentru IndexNow: motorul citeste cheia de la radacina
    _write(os.path.join(OUT_DIR, f"{config.INDEXNOW_KEY}.txt"), config.INDEXNOW_KEY + "\n")
    _write_headers()
    _write_redirects()
    _write_feed(by_date)
    _write_search(env, by_date)


def _write_build_metadata(article_count: int) -> None:
    """Emite amprenta necache-uită a release-ului pentru verificarea post-deploy.

    Cloudflare Pages expune SHA-ul și ramura buildului prin variabile de mediu; GitHub
    Actions expune `GITHUB_SHA` pentru randarea din pipeline. Local, manifestul rămâne
    explicit ca neidentificat, în loc să pretindă un commit care nu există.
    """
    commit = (os.getenv("CF_PAGES_COMMIT_SHA") or os.getenv("GITHUB_SHA")
              or os.getenv("BUILD_COMMIT_SHA") or "local")
    branch = (os.getenv("CF_PAGES_BRANCH") or os.getenv("GITHUB_REF_NAME")
              or os.getenv("BUILD_BRANCH") or "local")
    payload = {
        "commit": commit,
        "branch": branch,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "article_count": article_count,
    }
    # Cheile JSON raman stabile pentru ca probele externe sa nu depinda de ordinea dict-ului Python.
    _write(os.path.join(OUT_DIR, "build.json"), json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


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


def _render_sections(env: Environment) -> None:
    """Randează destinația explicită a linkului „Mai multe secțiuni”."""
    tpl = env.get_template("sectiuni.html")
    _write(os.path.join(OUT_DIR, "sectiuni", "index.html"),
           tpl.render(**_base_ctx("/sectiuni/", nav_section="stiri")))


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
    # Informatiile confirmate apar primele in fiecare categorie. Ghidurile neconfirmate
    # raman accesibile si marcate, dar nu concureaza vizual cu cele verificate.
    for ents in entities_by_cat.values():
        ents.sort(key=lambda ent: (not ent.get("verificat", False), ent.get("nume", "").casefold()))

    for eid, ent in entities.items():
        cat_stiri = ent.get("categorie_stiri", "")
        related = [a for a in articles if a.get("category") == cat_stiri][:5]
        # FAQPage e un SUBTIP de WebPage: pagina de ghid *este* FAQ-ul. Deci intrebarile stau
        # pe nodul paginii, nu pe un al doilea nod care ar pretinde acelasi URL cu alt `@id`.
        # Fara intrebari nu se declara FAQPage deloc — un FAQPage cu `mainEntity` gol e o
        # promisiune de rich result pe care pagina n-o poate onora.
        faq = [{"@type": "Question", "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]}}
               for item in (ent.get("faq") or [])]
        jsonld_page = {"name": ent.get("nume", eid)}
        if faq:
            jsonld_page["@type"] = ["WebPage", "FAQPage"]
            jsonld_page["mainEntity"] = faq
        breadcrumb_jsonld = {
            "@type": "BreadcrumbList",
            "@id": _abs_id(f"/ghiduri/{eid}/", "breadcrumb"),
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
                   jsonld_nodes=[breadcrumb_jsonld], jsonld_page=jsonld_page,
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
               # `.timestamp()` da acelasi numar in ambele forme — un naiv e citit ca ora
               # locala, si `_dt.now()` chiar e locala. Diferenta apare doar in ora ambigua
               # de la trecerea la ora de iarna, cand naivul poate iesi cu 3600 s alaturi si
               # ar muta un termen intre „urmatoarele" si „trecute". Ambele capete ale
               # comparatiei din `calendar.html` sunt secunde absolute, deci schimbarea aici
               # nu le desincronizeaza de `ts` de mai sus.
               now_timestamp=_dt.now(timezone.utc).timestamp())))


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
_SITEMAP_SECTIONS = ("ghiduri", "instrumente", "calendar", "surse", "legal", "sectiuni")


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


def _priority_articles(articles: list) -> list:
    """Returneaza doar articolele cu semnal editorial mai puternic pentru sitemapul prioritar.

    Sitemapul principal ramane inventarul complet de URL-uri canonice. Acest fisier separat nu
    blocheaza si nu elimina niciun articol; face explicita o selectie restransa, formata din
    sinteze multi-sursa cu corp propriu, astfel incat aceasta familie sa poata fi urmarita si
    trimisa separat in Search Console. O simpla aparitie in sitemap nu garanteaza indexarea.
    """
    selected = []
    for a in articles:
        sources = a.get("sources") or []
        if (a.get("model") == "C" and len(sources) >= 2
                and (a.get("synthesis") or "").strip()):
            selected.append(a)
    return selected


def _write_priority_sitemap(articles: list) -> None:
    """Scrie sitemap-priority.xml pentru continutul editorial multi-sursa si pagini stabile.

    Este un sitemap suplimentar, nu un inlocuitor al sitemapului principal: toate URL-urile
    din el raman si in inventarul general. Scopul este observabilitatea si semnalarea clara a
    paginilor pentru care IZZ.ro are cea mai mare contributie editoriala proprie.
    """
    url = config.SITE["url"]
    locs = [
        (f"{url}/{a['category']}/{a['slug']}/", (a.get("updated") or a.get("published") or "")[:10])
        for a in _priority_articles(articles)
    ]
    locs += [(url + p, "") for p in _editorial_paths()]
    if not locs:
        return
    items = "\n".join(
        f"  <url><loc>{xml_escape(l)}</loc>" + (f"<lastmod>{lm}</lastmod>" if lm else "") + "</url>"
        for l, lm in locs)
    _write(os.path.join(OUT_DIR, "sitemap-priority.xml"),
           '<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{items}\n</urlset>\n")
    _SITEMAPS_WRITTEN.append("sitemap-priority.xml")


def _write_sitemap(articles: list, now: datetime = None) -> None:
    # `now` injectabil: fereastra de stiri se masoara fata de el, iar un test cu date
    # fixe si ceas real ar trece azi si ar pica peste doua zile, fara nicio schimbare de cod.
    url = config.SITE["url"]
    now = now or datetime.now(timezone.utc)
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
    _write_priority_sitemap(articles)
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
    """Pagina /cauta/ + index JSON mic (titluri) pentru cautarea client-side.

    Limita indexului este aceeasi cu retentia editoriala, nu o promisiune vaga de
    "arhiva completa". Valorile sunt randate in HTML, astfel incat functioneaza fara JS
    si raman sincronizate cu datele pe care le poate interoga clientul.
    """
    import json as _json
    idx = [{"t": a.get("display_title") or a.get("title", ""), "u": f"/{a['category']}/{a['slug']}/",
            "c": a.get("category", ""), "d": a.get("published_human", ""),
            "f": filtru_cautare_rapida(a)} for a in articles]
    _write(os.path.join(OUT_DIR, "search-index.json"), _json.dumps(idx, ensure_ascii=False))
    _write(os.path.join(OUT_DIR, "cauta", "index.html"),
           env.get_template("search.html").render(**_base_ctx(
               "/cauta/", search_count=len(idx), search_days=config.ARTICLE_TTL_DAYS)))


def _write_robots() -> None:
    """Anunta DOAR sitemap-urile scrise de rularea curenta (`_SITEMAPS_WRITTEN`)."""
    lines = "".join(f"Sitemap: {config.SITE['url']}/{name}\n" for name in _SITEMAPS_WRITTEN)
    _write(os.path.join(OUT_DIR, "robots.txt"), f"User-agent: *\nAllow: /\n{lines}")


def _write_security_txt() -> None:
    """Publica un canal de raportare a vulnerabilitatilor la calea RFC 9116.

    Fisierul este deliberat separat de pagina HTML `/legal/security/`: cercetatorii si
    uneltele automate cauta formatul text la `/.well-known/security.txt`, iar cititorii
    pot intelege politica in pagina legala randata din Markdown.
    """
    expires = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT00:00:00Z")
    _write(os.path.join(OUT_DIR, ".well-known", "security.txt"),
           "Contact: mailto:contact@izz.ro?subject=Raport%20securitate%20IZZ.ro\n"
           f"Policy: {config.SITE['url']}/legal/security/\n"
           "Preferred-Languages: ro, en\n"
           f"Canonical: {config.SITE['url']}/.well-known/security.txt\n"
           f"Expires: {expires}\n")


def _write_headers() -> None:
    """Cache-Control + headere de securitate pe Cloudflare Pages (fisierul _headers).
    Activele imutabile tin mult; imaginile o zi; HTML-ul NU se cache-uieste agresiv
    (stiri proaspete). Pattern-urile de cale TREBUIE sa inceapa cu '/' -- altfel
    Pages le ignora si imaginile cad pe TTL-ul implicit de 4h."""
    # clarity.ms: wildcard, nu hosturi exacte -- hostul de colectare variaza
    # (configul tagului declara k.clarity.ms, rularea reala din 2026-08-13 a
    # urcat pe n.clarity.ms). Un CSP stramtat la hosturi exacte rupe Clarity in
    # tacere. DELIBERAT absent din img-src: singura imagine pe care o cere
    # Clarity e c.clarity.ms/c.gif, pixelul care sincronizeaza MUID (identificatorul
    # de publicitate Microsoft). personalize.js il refuza deja prin
    # ad_Storage:'denied'; lasandu-l in afara CSP, browserul il blocheaza si daca
    # flagul ala regreseaza. NU-l adauga la img-src "ca sa nu mai dea eroare".
    # Cloudflare Bot Fight Mode injecteaza pe live un bootstrap inline `__CF$cv$params`.
    # Nu folosim `unsafe-inline`: cele doua hash-uri sunt variantele observate ale acelui
    # bootstrap, permise explicit si nimic altceva. Daca Cloudflare il schimba din nou,
    # Lighthouse va semnala incidentul, ceea ce e preferabil deschiderii globale a CSP-ului.
    csp = ("default-src 'self'; "
           "script-src 'self' 'sha256-DzqzfYrgtaakHyuPGKa5knFv5IoTaJszzL9Fca3521M=' "
           "'sha256-LXd89R0ZNPfUJLyGqvxXmhTIA1mSPILGag0zh9noF7U=' "
           "https://static.cloudflareinsights.com https://www.googletagmanager.com "
           "https://*.clarity.ms; "
           "style-src 'self' 'unsafe-inline'; "
           "img-src 'self' data: https://*.google-analytics.com https://*.googletagmanager.com; "
           "font-src 'self'; "
           "connect-src 'self' https://cloudflareinsights.com https://*.google-analytics.com "
           "https://*.analytics.google.com https://*.googletagmanager.com https://*.clarity.ms; "
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
           # harta-stiri lives under /static/ but is a live page + dataset, not a
           # versioned asset -- without this override a CSS/JS/dataset fix stays
           # invisible to any browser that already cached the page for 30 days.
           # Cloudflare Pages JOINS same-named headers from multiple matching rules
           # (Cache-Control ends up "immutable, must-revalidate" -- self-contradicting)
           # instead of the more specific rule replacing the general one; "!" is the
           # documented way to unset the inherited value before setting the real one.
           "/static/harta-stiri/*\n  ! Cache-Control\n  Cache-Control: public, max-age=300, must-revalidate\n"
           "/favicon.svg\n  Cache-Control: public, max-age=2592000\n"
           "/*.jpg\n  Cache-Control: public, max-age=86400\n"
           "/*.png\n  Cache-Control: public, max-age=86400\n"
           "/*.webp\n  Cache-Control: public, max-age=86400\n"
           "/feed.xml\n  Cache-Control: public, max-age=1800\n"
           "/build.json\n  Cache-Control: public, max-age=0, must-revalidate\n")


def _write_redirects() -> None:
    """Cloudflare Pages redirects (fisierul _redirects).

    Categoria `zonal` a fost redenumita `judetean` (decizie owner, 2026-08-12), inclusiv
    in slug-ul din URL -- exceptie de la regula din CATEGORY_LABELS ("slug-ul nu se schimba
    niciodata"). Fara linia de mai jos, cele 295 de articole deja publicate si indexate sub
    `/zonal/<slug>/` ar da 404 permanent, iar orice link vechi distribuit (Google, retele
    sociale) s-ar rupe. Wildcard, nu o linie per articol: acopera si pagina de categorie
    (`/zonal/`, `/zonal/2/`) si orice viitor request catre calea veche, nu doar ce exista azi."""
    redirects = (
        "/harta-stiri/ /static/harta-stiri/ 301\n"
        "/zonal/* /judetean/:splat 301\n"
    )
    _write(os.path.join(OUT_DIR, "_redirects"), redirects)


def _rfc2822(value: str, url: str = "") -> str:
    """ISO 8601 -> data RFC 2822 ceruta de RSS 2.0, sau "" daca nu se poate parsa.

    `email.utils.format_datetime`, nu `strftime("%a, %d %b ...")`: `%a`/`%b` se traduc dupa
    LC_TIME. Azi iese engleza fiindca nimeni nu cheama `setlocale` si Python porneste pe
    locale-ul "C" (verificat: `locale.getlocale(LC_TIME)` -> `(None, None)`), deci
    `lastBuildDate` NU e stricat acum. Dar corectitudinea lui depinde de o absenta — un
    singur `setlocale` adaugat oriunde in proces ar emite "Joi, 06 Aug" in tot feedul, tacut.
    Helper-ul din stdlib e independent de locale prin constructie.

    Esecul se LOGHEAZA, nu se inghite: `published` e ISO valid pentru toate caile de ingestie
    (fetch.py cade pe `now()` cand nu poate parsa), deci un "" de aici inseamna stare stricata
    sau o cale de intrare noua care nu normalizeaza data. Fara linia asta, itemul ar iesi in
    feed fara data si nimic n-ar arata unde s-a pierdut — feedul ar parea valid.
    """
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        logging.warning("feed: `published` neparsabil (%r) pe %s — item fara pubDate",
                        value, url or "?")
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return format_datetime(dt.astimezone(timezone.utc))


def _feed_xml(articles: list, title: str, link: str, description: str,
              feed_url: str | None = None) -> str:
    url = config.SITE["url"]
    now = format_datetime(datetime.now(timezone.utc))
    entries = []
    for a in articles[:50]:
        body = a.get("synthesis") if a.get("model") == "C" else a.get("teaser")
        alink = f"{url}/{a['category']}/{a['slug']}/"
        # Fara `pubDate` un cititor RSS nu poate nici data, nici ordona intrarile — le arata
        # in ordinea din fisier si fara vechime, ceea ce pentru un flux de stiri il face
        # inutilizabil. Se OMITE cand data nu se poate parsa (si se logheaza acolo): o data
        # inventata ar urca un articol vechi in capul oricarui cititor care sorteaza pe ea.
        pub = _rfc2822(a.get("published") or "", alink)
        entries.append(
            "    <item>\n"
            f"      <title>{xml_escape(a.get('title',''))}</title>\n"
            f"      <link>{xml_escape(alink)}</link>\n"
            f"      <guid>{xml_escape(alink)}</guid>\n"
            + (f"      <pubDate>{xml_escape(pub)}</pubDate>\n" if pub else "")
            + f"      <description>{xml_escape(body or '')}</description>\n"
            "    </item>")
    # `atom:link rel="self"` = adresa canonica a FEEDULUI (nu a paginii din `<link>`). O cer
    # validatoarele RSS si o folosesc agregatoarele ca sa recunoasca acelasi flux mutat sau
    # oglindit — iar noi chiar servim site-ul de pe doua origini (Cloudflare Pages + mirror
    # GitHub Pages, build.yml), deci ambiguitatea e reala, nu teoretica.
    self_link = (f'  <atom:link href="{xml_escape(feed_url)}" rel="self" '
                 'type="application/rss+xml"/>\n') if feed_url else ""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>\n'
            f"  <title>{xml_escape(title)}</title>\n"
            f"  <link>{xml_escape(link)}</link>\n"
            + self_link
            + f"  <description>{xml_escape(description)}</description>\n"
            f"  <language>{config.SITE['lang']}</language>\n"
            f"  <lastBuildDate>{now}</lastBuildDate>\n"
            + "\n".join(entries) +
            "\n</channel></rss>\n")


def _write_feed(articles: list) -> None:
    _write(os.path.join(OUT_DIR, "feed.xml"),
           _feed_xml(articles, config.SITE["name"], config.SITE["url"], config.SITE["tagline"],
                     feed_url=f"{config.SITE['url']}/feed.xml"))
