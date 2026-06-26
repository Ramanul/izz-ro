import os
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(APP_DIR)

SITE = {"name": "IZZ.ro", "tagline": "Informația Zero Zgomot",
                "descriptor": "Raportul știrilor principale",
                "url": "https://izz.ro", "lang": "ro", "contact": "contact@izz.ro"}

# Surse = DOAR publicații cu RSS oficial. Agențiile de presă sunt EXCLUSE (conținut licențiat).
SOURCES = {
            # Surse niche primele -> bugetul AI le proceseaza prioritar (altfel general le infometeaza)
    "extern":     {"name": "Digi24 Extern","url": "https://www.digi24.ro/rss/stiri/externe",   "category": "extern"},
            "bbc_world":  {"name": "BBC World",    "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "extern", "lang": "en"},
            "guardian":   {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss",       "category": "extern", "lang": "en"},
            "politico_eu":{"name": "Politico EU",  "url": "https://www.politico.eu/feed/",               "category": "extern", "lang": "en"},
            "dw_en":      {"name": "DW English",   "url": "https://rss.dw.com/rdf/rss-en-all",          "category": "extern", "lang": "en"},
            "aljazeera":  {"name": "Al Jazeera",   "url": "https://www.aljazeera.com/xml/rss/all.xml",  "category": "extern", "lang": "en"},
            "gsp":        {"name": "GSP",          "url": "https://www.gsp.ro/rss.xml",                "category": "sport"},
            "digisport":  {"name": "Digi Sport",   "url": "https://www.digisport.ro/rss",               "category": "sport"},
            "prosport":   {"name": "ProSport",     "url": "https://www.prosport.ro/feed/",              "category": "sport"},
            "startup":    {"name": "Start-up.ro",  "url": "https://start-up.ro/feed/",                 "category": "tech"},
            # "playtech": {"name": "Playtech",     "url": "https://playtech.ro/feed/",                 "category": "tech"},   # publica lifestyle/social, nu tech - dezactivat
                # "iqool":    {"name": "iQool",        "url": "https://iqool.ro/feed/",                    "category": "tech"},   # DNS mort - dezactivat
                    "piataauto": {"name": "Piata Auto MD", "url": "https://piataauto.md/Stiri/", "base_url": "https://piataauto.md", "category": "tech", "type": "html_scraper"},
      "autocritica": {"name": "AutoCritica",  "url": "https://www.autocritica.ro/feed/",          "category": "tech"},
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
# Exclude orice URL/sursă de agenție (verificare suplimentară pe domeniul linkului)
AGENCY_BLOCKLIST = ["agerpres", "mediafax", "reuters", "afp.com", "apnews", "ap.org"]

CATEGORIES = ["general", "politic", "economic", "extern", "tech", "sport"]

# Model B+C
PROMPT_VERSION = "v2-esenta"  # versiunea regulilor AI; la schimbare, articolele vechi se reprocesează
TITLE_MAX_WORDS = 22           # titlu: soft-cap care transmite faptul complet (nu mai taie la 12)
TEASER_MAX_WORDS = 40          # B: teaser scurt ("extras foarte scurt")
SYNTHESIS_MAX_WORDS = 90       # C: sinteză multi-sursă (doar pentru clustere importante)
CLUSTER_MIN_SOURCES = 2        # >=2 surse pe același eveniment -> candidat pentru C
ARTICLE_TTL_DAYS = 7           # mai scurt -> volum mai mic -> incape in quota free Gemini
MAX_PER_SOURCE = 8             # redus de la 12 ca sa scada apelurile AI/rulare

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")  # "gemini" | "anthropic"
