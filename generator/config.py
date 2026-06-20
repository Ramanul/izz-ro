import os
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(APP_DIR)

SITE = {"name": "IZZ.ro", "tagline": "Informația Zero Zgomot",
        "url": "https://izz.ro", "lang": "ro", "contact": "contact@izz.ro"}

# Surse = DOAR publicații cu RSS oficial. Agențiile de presă sunt EXCLUSE (conținut licențiat).
SOURCES = {
    "digi24":     {"name": "Digi24",     "url": "https://www.digi24.ro/rss",        "category": "general"},
    "hotnews":    {"name": "HotNews",    "url": "https://www.hotnews.ro/rss",       "category": "general"},
    "g4media":    {"name": "G4Media",    "url": "https://www.g4media.ro/feed",      "category": "politic"},
    "libertatea": {"name": "Libertatea", "url": "https://www.libertatea.ro/rss",    "category": "general"},
    "zf":         {"name": "Ziarul Financiar", "url": "https://www.zf.ro/rss",      "category": "economic"},
    "economica":  {"name": "Economica",  "url": "https://www.economica.net/rss",    "category": "economic"},
    "protv":      {"name": "Știrile ProTV","url": "https://stirileprotv.ro/rss",    "category": "general"},
    "gsp":        {"name": "GSP",        "url": "https://www.gsp.ro/rss.xml",       "category": "sport"},
}
# Exclude orice URL/sursă de agenție (verificare suplimentară pe domeniul linkului)
AGENCY_BLOCKLIST = ["agerpres", "mediafax", "reuters", "afp.com", "apnews", "ap.org"]

CATEGORIES = ["general", "politic", "economic", "extern", "tech", "sport"]

# Model B+C
TEASER_MAX_WORDS = 40          # B: teaser scurt ("extras foarte scurt")
SYNTHESIS_MAX_WORDS = 90       # C: sinteză multi-sursă (doar pentru clustere importante)
CLUSTER_MIN_SOURCES = 2        # >=2 surse pe același eveniment -> candidat pentru C
ARTICLE_TTL_DAYS = 14          # după 14 zile: arhivat, nu șters brusc (SEO)
MAX_PER_SOURCE = 12

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")  # "gemini" | "anthropic"
