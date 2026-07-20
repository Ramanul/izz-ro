import os
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(APP_DIR)

SITE = {"name": "IZZ.ro", "tagline": "Portalul știrilor tale",
                "descriptor": "Informația Zilei",
                "url": "https://izz.ro", "lang": "ro", "contact": "contact@izz.ro"}

# Surse = DOAR publicații cu RSS oficial. Agențiile de presă sunt EXCLUSE (conținut licențiat).
SOURCES = {
            # Surse niche primele -> bugetul AI le proceseaza prioritar (altfel general le infometeaza)
    # lifestyle / fashion / discounturi — rubrici noi (2026-07-16, cerute de owner).
    # Feed-urile sunt candidati validati cu tools/feed_check.py in CI (sandbox-ul n-are internet);
    # cele care nu raspund / nu-s RSS se taie inainte de merge.
            "unica":      {"name": "Unica",            "url": "https://www.unica.ro/feed",             "category": "lifestyle"},
            "csid":       {"name": "CSÎD",             "url": "https://www.csid.ro/feed",              "category": "sanatate"},
            # sanatate — surse dedicate (scindate din lifestyle 2026-07-17)
            "sfatulparintilor": {"name": "Sfatul Părinților", "url": "https://www.sfatulparintilor.ro/feed", "category": "sanatate"},
            "urban":      {"name": "Urban.ro",         "url": "https://urban.ro/feed",                 "category": "lifestyle"},
            "elle":       {"name": "Elle România",     "url": "https://www.elle.ro/feed",              "category": "lifestyle"},
            "avantaje":   {"name": "Avantaje",         "url": "https://www.avantaje.ro/feed",          "category": "lifestyle"},
    # cultura — literatură, film, arte (2026-07-17)
            "liternet":   {"name": "Liternet",        "url": "https://www.liternet.ro/feed.php",       "category": "cultura"},
            "scena9":     {"name": "Scena 9",         "url": "https://www.scena9.ro/feed",              "category": "cultura"},
            "bookhub":    {"name": "Bookhub",         "url": "https://bookhub.ro/feed",                 "category": "cultura"},
            "nwradu":       {"name": "NwRadu",         "url": "https://www.nwradu.ro/feed/",           "category": "discounturi"},
    # local — surse OFICIALE gratuite (primarii + consilii judetene) cu RSS
    # (cerinta owner 2026-07-17: informatii de la primarii si judete). 16 candidati verificati
    # cu feedcheck.yml in CI (run 29588587064, 2026-07-17): doar cei 3 de mai jos au feed VIU.
    # Cazuti la verificare (nu re-adauga fara re-test): primariatm/apulum/sibiu/primariacraiova/
    # baiamare/primariagalati/cjmaramures = 404, cjalba = 403, icc.ro = timeout, cjsuceava =
    # unreachable, oradea/rss = 0 intrari; primariaclujnapoca (2024) si primaria-constanta (2022)
    # raspund dar sunt inghetate. Majoritatea primariilor NU au RSS -> acoperirea "toate
    # primariile din tara" cere faza "Monitor Local" (html_list pe paginile de anunturi).
            "pr_buzau":     {"name": "Primăria Buzău",      "url": "https://primariabuzau.ro/feed/",         "category": "local"},
            "cj_cluj":      {"name": "CJ Cluj",             "url": "https://www.cjcluj.ro/feed/",            "category": "local"},
            "cj_timis":     {"name": "CJ Timiș",            "url": "https://www.cjtimis.ro/feed",            "category": "local"},
            # CJ cazuti la feedcheck 2026-07-20 (nu re-adauga fara re-test): arad/bihor/ilfov/sibiu=GOL, buzau=502, iasi=timeout, calarasi=inghetat 2022
            "cj_botosani":  {"name": "CJ Botoșani",         "url": "https://www.cjbotosani.ro/feed/",         "category": "local"},
            "cj_galati":    {"name": "CJ Galați",           "url": "https://cjgalati.ro/feed/",               "category": "local"},
            "cj_giurgiu":   {"name": "CJ Giurgiu",          "url": "https://cjgiurgiu.ro/feed/",              "category": "local"},
            "cj_ialomita":  {"name": "CJ Ialomița",         "url": "https://cjialomita.ro/feed/",             "category": "local"},
            "cj_vaslui":    {"name": "CJ Vaslui",           "url": "https://cjvs.eu/feed/",                   "category": "local"},
            "cj_vrancea":   {"name": "CJ Vrancea",          "url": "https://cjvrancea.ro/feed/",              "category": "local"},
    # local — ZIARE JUDETENE cu RSS (flux excelent, spre deosebire de paginile de primarie
    # care sunt blocate/JS). Acopera "informatii de la judete" cerute de owner. Categoria e
    # PINNED (axa geografica): un articol de la ziarul judetean ramane 'local', nu e mutat pe
    # tema. Cei 7 de mai jos = feed VIU la feedcheck (run 29605677325, 2026-07-17). Cazuti la
    # verificare (nu re-adauga fara re-test): stiridecluj.ro/feed=404, ziuaconstanta rss.html=
    # 0 intrari, gds.ro=403, ebihoreanul=500. Acoperire: Cluj/Iasi/Timis/Brasov.
            "zcj":          {"name": "Ziua de Cluj",        "url": "https://zcj.ro/feed",                    "category": "local"},
            "bzi":          {"name": "BZI Iași",            "url": "https://www.bzi.ro/feed",                "category": "local"},
            "ziaruldeiasi": {"name": "Ziarul de Iași",      "url": "https://www.ziaruldeiasi.ro/rss",        "category": "local"},
            "pressalert":   {"name": "PressAlert Timișoara","url": "https://www.pressalert.ro/feed/",         "category": "local"},
            "tion":         {"name": "Timiș Online",        "url": "https://www.tion.ro/feed/",              "category": "local"},
            "bizbrasov":    {"name": "BizBrașov",           "url": "https://www.bizbrasov.ro/feed",          "category": "local"},
            "newsbv":       {"name": "News Brașov",         "url": "https://www.newsbv.ro/feed/",            "category": "local"},
    # extern — Europa/UE/vecinatate (en, AI traduce) + surse ro
            "bbc_europe": {"name": "BBC Europe",    "url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml", "category": "extern", "lang": "en"},
            "guardian_eu":{"name": "The Guardian",  "url": "https://www.theguardian.com/world/europe-news/rss",  "category": "extern", "lang": "en"},
            "politico_eu":{"name": "Politico EU",   "url": "https://www.politico.eu/feed/",                      "category": "extern", "lang": "en"},
            "dw_europe":  {"name": "DW Europe",     "url": "https://rss.dw.com/rdf/rss-en-eu",                   "category": "extern", "lang": "en"},
            "el_moldova": {"name": "Europa Liberă", "url": "https://moldova.europalibera.org/api/epiqq",          "category": "extern"},
            "extern":     {"name": "Digi24 Extern", "url": "https://www.digi24.ro/rss/stiri/externe",            "category": "extern"},
            "gsp":        {"name": "GSP",          "url": "https://www.gsp.ro/rss.xml",                "category": "sport"},
            "digisport":  {"name": "Digi Sport",   "url": "https://www.digisport.ro/rss",               "category": "sport"},
            "prosport":   {"name": "ProSport",     "url": "https://www.prosport.ro/feed/",              "category": "sport"},
            "startup":    {"name": "Start-up.ro",  "url": "https://start-up.ro/feed/",                 "category": "tech"},
            # "playtech": {"name": "Playtech",     "url": "https://playtech.ro/feed/",                 "category": "tech"},   # publica lifestyle/social, nu tech - dezactivat
                # "iqool":    {"name": "iQool",        "url": "https://iqool.ro/feed/",                    "category": "tech"},   # DNS mort - dezactivat
            # Fara RSS -> sitemap Google News (legal, robots.txt Allow, XML stabil fara Cloudflare).
            "piataauto": {"name": "Piata Auto MD", "url": "https://piataauto.md/sitemap-news.xml", "category": "auto", "type": "sitemap_news"},
            "autocritica": {"name": "AutoCritica",  "url": "https://www.autocritica.ro/feed/",          "category": "auto"},
            # Surse cu volum mare
            "spotmedia":  {"name": "Spotmedia",    "url": "https://spotmedia.ro/rss",                  "category": "general"},
            "digi24":     {"name": "Digi24",       "url": "https://www.digi24.ro/rss",                 "category": "general"},
            "hotnews":    {"name": "HotNews",      "url": "https://www.hotnews.ro/rss",                "category": "general"},
            "g4media":    {"name": "G4Media",      "url": "https://www.g4media.ro/feed",               "category": "politic"},
            "recorder":   {"name": "Recorder",     "url": "https://recorder.ro/feed/",                 "category": "politic"},
            "contributors":{"name": "Contributors", "url": "https://www.contributors.ro/feed/",          "category": "politic"},
            "tolo":       {"name": "Tolo.ro",      "url": "https://www.tolo.ro/feed/",                  "category": "politic"},
            "libertatea": {"name": "Libertatea",  "url": "https://www.libertatea.ro/rss",             "category": "general"},
            "zf":         {"name": "Ziarul Financiar", "url": "https://www.zf.ro/rss",                 "category": "economic"},
            "economica":  {"name": "Economica",    "url": "https://www.economica.net/rss",             "category": "economic"},
            "economedia": {"name": "Economedia",   "url": "https://economedia.ro/feed/",               "category": "economic"},
            "cursdeguv":  {"name": "Curs de Guvernare", "url": "https://cursdeguvernare.ro/feed",       "category": "economic"},
            "protv":      {"name": "Știrile ProTV","url": "https://stirileprotv.ro/rss",               "category": "general"},
}
from generator.local_sources import load_gold_sources
_GOLD_CSV = os.path.join(ROOT, "data", "primarii_lists", "gold_integrare.csv")
SOURCES.update(load_gold_sources(_GOLD_CSV, int(os.environ.get("LOCAL_GOLD_LIMIT", "35"))))

# Exclude orice URL/sursă de agenție (verificare suplimentară pe domeniul linkului)
AGENCY_BLOCKLIST = ["agerpres", "mediafax", "reuters", "afp.com", "apnews", "ap.org"]

CATEGORIES = ["general", "politic", "economic", "extern", "tech", "sport",
              "auto", "sanatate", "cultura", "lifestyle", "discounturi", "local"]

# Categorii in INSAMANTARE: nou-adaugate, cu surse de volum mic — pot fi goale fara sa pice
# QA (warn, nu FAIL). Se scot de aici dupa ce categoria s-a populat stabil.
SEED_CATEGORIES = {"local"}

# Categorii GEOGRAFICE (axa proprie): articolele surselor cu aceste categorii NU sunt
# re-clasificate pe tema de catre AI (vezi process._resolve_category). Un ziar judetean
# ramane in sectiunea 'local', nu ajunge pe sport/politic dupa continut.
PINNED_CATEGORIES = {"local"}

# Etichete AFISATE (owner 2026-07-17): slug-ul din URL ramane neschimbat (SEO), doar
# textul din nav/titluri/carduri foloseste aceste nume. Fallback = slug capitalizat.
CATEGORY_LABELS = {
    "general": "Actualitate", "politic": "Politică", "economic": "Economie",
    "extern": "Externe", "tech": "Tech", "sport": "Sport", "auto": "Auto",
    "sanatate": "Sănătate", "cultura": "Cultură", "lifestyle": "Lifestyle",
    "discounturi": "Discounturi", "local": "Local",
}

# Model B+C
PROMPT_VERSION = "v2-esenta"  # versiunea regulilor AI; la schimbare, articolele vechi se reprocesează
BATCH_SIZE = 6                 # articole model-B procesate intr-UN singur apel AI (economie quota)
TITLE_MAX_WORDS = 22           # titlu: soft-cap care transmite faptul complet (nu mai taie la 12)
TEASER_MAX_WORDS = 40          # B: teaser scurt ("extras foarte scurt")
SYNTHESIS_MAX_WORDS = 90       # C: sinteză multi-sursă (doar pentru clustere importante)
CLUSTER_MIN_SOURCES = 2        # >=2 surse pe același eveniment -> candidat pentru C
RELATED_MIN_SHARED = 2         # "Articole conectate": minim entitati comune. 1 singura entitate
                               # comuna (de regula o tara larga: "Franța") = zgomot, nu relevanta.
ARTICLE_TTL_DAYS = 7           # mai scurt -> volum mai mic -> incape in quota free Gemini
MAX_PER_SOURCE = 8             # redus de la 12 ca sa scada apelurile AI/rulare

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")  # "gemini" | "anthropic"

# IndexNow (Bing/Seznam/Yandex): cheia e PUBLICA prin protocol (motorul o citeste de la
# https://izz.ro/<cheie>.txt ca dovada ca detinem domeniul). render.py scrie fisierul,
# tools/indexnow_submit.py anunta URL-urile noi la fiecare rulare a pipeline-ului.
INDEXNOW_KEY = "f9b2f9cd7e5e9677f83454b525ad2c77"
