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
            "liternet":   {"name": "Liternet",        "url": "https://feed.liternet.ro/agenda.xml",       "category": "cultura"},
            "scena9":     {"name": "Scena 9",         "url": "https://www.scena9.ro/feed",              "category": "cultura"},
            "bookhub":    {"name": "Bookhub",         "url": "https://bookhub.ro/feed",                 "category": "cultura"},
            "nwradu":       {"name": "NwRadu",         "url": "https://www.nwradu.ro/feed/",           "category": "discounturi"},
    # local — primărie (UAT); judetean — consilii județene + ziare județene.
    # Cerința owner 2026-07-17: informații de la primării și județe. 16 candidați verificați
    # cu feedcheck.yml in CI (run 29588587064, 2026-07-17): doar cei 3 de mai jos au feed VIU.
    # Cazuti la verificare (nu re-adauga fara re-test): primariatm/apulum/sibiu/primariacraiova/
    # baiamare/primariagalati/cjmaramures = 404, cjalba = 403, icc.ro = timeout, cjsuceava =
    # unreachable, oradea/rss = 0 intrari; primariaclujnapoca (2024) si primaria-constanta (2022)
    # raspund dar sunt inghetate. Majoritatea primariilor NU au RSS -> acoperirea "toate
    # primariile din tara" cere faza "Monitor Local" (html_list pe paginile de anunturi).
            "pr_buzau":     {"name": "Primăria Buzău",      "url": "https://primariabuzau.ro/feed/",         "category": "local"},
            "cj_cluj":      {"name": "CJ Cluj",             "url": "https://www.cjcluj.ro/feed/",            "category": "judetean"},
            "cj_timis":     {"name": "CJ Timiș",            "url": "https://www.cjtimis.ro/feed",            "category": "judetean"},
            # CJ cazuti la feedcheck 2026-07-20 (nu re-adauga fara re-test): arad/bihor/ilfov/sibiu=GOL, buzau=502, iasi=timeout, calarasi=inghetat 2022
            "cj_botosani":  {"name": "CJ Botoșani",         "url": "https://www.cjbotosani.ro/feed/",         "category": "judetean"},
            "cj_galati":    {"name": "CJ Galați",           "url": "https://cjgalati.ro/feed/",               "category": "judetean"},
            "cj_giurgiu":   {"name": "CJ Giurgiu",          "url": "https://cjgiurgiu.ro/feed/",              "category": "judetean"},
            "cj_ialomita":  {"name": "CJ Ialomița",         "url": "https://cjialomita.ro/feed/",             "category": "judetean"},
            "cj_vaslui":    {"name": "CJ Vaslui",           "url": "https://cjvs.eu/feed/",                   "category": "judetean"},
            "cj_vrancea":   {"name": "CJ Vrancea",          "url": "https://cjvrancea.ro/feed/",              "category": "judetean"},
    # judetean — ZIARE JUDETENE cu RSS (flux excelent, spre deosebire de paginile de primărie
    # care sunt blocate/JS). Acoperă "informații de la județe" cerute de owner. Categoria e
    # PINNED (axă geografică): un articol de la ziarul județean rămâne 'judetean', nu e mutat pe
    # temă. Cei 7 de mai jos = feed VIU la feedcheck (run 29605677325, 2026-07-17). Cazuti la
    # verificare (nu re-adauga fara re-test): stiridecluj.ro/feed=404, ziuaconstanta rss.html=
    # 0 intrari, gds.ro=403, ebihoreanul=500. Acoperire: Cluj/Iasi/Timis/Brasov.
    # `judet` NU e decor: primariile isi codeaza judetul in cheie (`pl_cluj_...`), ziarele nu —
    # `zcj` nu spune nimanui ca e Cluj. Campul asta deschide potrivirea pe SATE pentru sursa
    # respectiva (`geo.clasifica(text, judet)`): fara el, „Dezmir" sau „Urseni" nu inseamna
    # nimic pentru poarta si stirea ramane pe judetean. Se pune DOAR pe surse cu un singur judet;
    # publicatiile regionale de mai jos acopera mai multe si de aceea nu-l au.
            "zcj":          {"name": "Ziua de Cluj",        "url": "https://zcj.ro/feed",                    "category": "judetean", "judet": "CLUJ"},
            "bzi":          {"name": "BZI Iași",            "url": "https://www.bzi.ro/feed",                "category": "judetean", "judet": "IASI"},
            "ziaruldeiasi": {"name": "Ziarul de Iași",      "url": "https://www.ziaruldeiasi.ro/rss",        "category": "judetean", "judet": "IASI"},
            "pressalert":   {"name": "PressAlert Timișoara","url": "https://www.pressalert.ro/feed/",         "category": "judetean", "judet": "TIMIS"},
            "tion":         {"name": "Timiș Online",        "url": "https://www.tion.ro/feed/",              "category": "judetean", "judet": "TIMIS"},
            "bizbrasov":    {"name": "BizBrașov",           "url": "https://www.bizbrasov.ro/feed",          "category": "judetean", "judet": "BRASOV"},
            "newsbv":       {"name": "News Brașov",         "url": "https://www.newsbv.ro/feed/",            "category": "judetean", "judet": "BRASOV"},
    # judetean — Maramures (nivel judet; regiunea istorica ≈ judetul, deci ziarele MM sunt județene)
            "actualmm":     {"name": "actualMM",            "url": "https://actualmm.ro/feed/",              "category": "judetean", "judet": "MARAMURES"},
            "emaramures":   {"name": "eMaramureș",          "url": "https://www.emaramures.ro/feed/",        "category": "judetean", "judet": "MARAMURES"},
    # judetean — VALUL 1 al extinderii pe presa judeteana (2026-08-04). Fiecare URL de aici a fost
    # cerut REAL de pe IP-ul de acasa pe 2026-08-03 si a intors un feed cu intrari proaspete —
    # niciunul nu e ghicit dupa tiparul `<domeniu>/feed/`, care e exact felul in care valul
    # anterior de 79 de candidati a produs ~30% caderi. NU verifica astea cu `feedcheck.yml`:
    # ruleaza pe runnere GitHub, unde furnizorul serveste pagina de challenge (vezi READ FIRST
    # din specs/istoric-executie.md), deci un verdict „mort" de acolo nu inseamna nimic.
    # Se intra in VALURI de ~15, nu toate odata: bugetul AI e ~10 apeluri de iteme noi pe rulare.
    # Forma `www` unde apare mai jos NU e cosmetica — fara ea raspunsul e un 30x in plus.
            "cvlpress":     {"name": "Cuvântul Libertății",  "url": "https://cvlpress.ro/feed/",              "category": "judetean", "judet": "DOLJ"},
            "alba24":       {"name": "Alba24",               "url": "https://alba24.ro/feed",                 "category": "judetean", "judet": "ALBA"},
            "zidezi":       {"name": "Zi de Zi",             "url": "https://www.zi-de-zi.ro/feed/",          "category": "judetean", "judet": "MURES"},
            "monitorulbt":  {"name": "Monitorul de Botoșani","url": "https://www.monitorulbt.ro/feed/",       "category": "judetean", "judet": "BOTOSANI"},
            "turnulsfatului": {"name": "Turnul Sfatului",    "url": "https://www.turnulsfatului.ro/feed/",    "category": "judetean", "judet": "SIBIU"},
            "bihon":        {"name": "Bihon",                "url": "https://www.bihon.ro/feed/",             "category": "judetean", "judet": "BIHOR"},
            "mytex":        {"name": "MyTex",                "url": "https://mytex.ro/feed/",                 "category": "judetean", "judet": "BRASOV"},
    # `b365` e SINGURA sursa din val FARA `judet`, si nu din scapare. BUCURESTI e in geo.REGIUNI,
    # dar are ZERO randuri in data/sate_judet.csv, deci campul n-ar deschide nicio potrivire pe
    # sate — iar `test_toate_ziarele_judetene_declara_un_judet_cunoscut` interzice exact asta, pe
    # buna dreptate: un `judet` care nu deschide nimic e o declaratie pe care datele n-o sustin,
    # si tace in loc sa dea eroare. Nu-l „completa" ca sa arate ca celelalte; testul pica.
            "b365":         {"name": "B365",                 "url": "https://b365.ro/feed/",                  "category": "judetean"},
    # Saptamanale cerute explicit de owner. `gazetadecluj` e SINGURUL feed din val cu bozo=1
    # (SAXParseException); feedparser recupereaza 9 intrari si fetch.py tolereaza asta, dar e la
    # o modificare de XML distanta de zero. Daca apare vreodata ca „200 dar 0 articole ...
    # SAXParseException" in `dead`, asta e — nu re-diagnostica reteaua.
    # `saptamanagiurgiuveana` NU e la radacina: WordPress-ul lor sta sub /wp/, si de aia calea
    # ghicita `<domeniu>/feed/` daduse 404 si sursa fusese declarata moarta pe nedrept.
            "gazetadecluj": {"name": "Gazeta de Cluj",       "url": "https://gazetadecluj.ro/feed/",          "category": "judetean", "judet": "CLUJ"},
            "sptgiurgiu":   {"name": "Săptămâna Giurgiuveană","url": "https://saptamanagiurgiuveana.ro/wp/feed/", "category": "judetean", "judet": "GIURGIU"},
    # `monitorulsv` NU ARE RSS DELOC — /feed/, /rss, /rss/, /feed/rss/ si /?feed=rss2 intorc toate
    # 200 si aterizeaza tacut pe homepage, /rss.xml e 404, iar HTML-ul homepage-ului nu contine
    # niciun „rss"/„feed" si niciun <link rel=alternate>. Intra doar prin sitemap-ul de stiri, deci
    # `"type": "sitemap_news"` e OBLIGATORIU: fara cheia aia fetch.py il trateaza ca RSS si
    # feedparser da 0. robots.txt e „User-Agent: *" fara Disallow si declara chiar acest sitemap —
    # aceeasi baza pe care sta deja `piataauto`.
            "monitorulsv":  {"name": "Monitorul de Suceava", "url": "https://www.monitorulsv.ro/sitemap-news.xml", "category": "judetean", "judet": "SUCEAVA", "type": "sitemap_news"},
    # NEadaugate DELIBERAT din acelasi lot verificat, ca sa nu fie re-cautate:
    # · `monitorulexpres.ro` (BV) — feed viu, dar ar fi a PATRA sursa de Brasov si scrie curent
    #   despre Covasna; a-i pune `judet: BRASOV` e exact nepotrivirea pe care campul o previne.
    #   Daca se adauga, se adauga FARA `judet`.
    # · `gazetademaramures.ro` — feedul e real si bogat (50 de intrari, la `/rss`, NU `/feed/`),
    #   dar pe masina asta orice cerere catre el moare cu CERTIFICATE_VERIFY_FAILED: lantul e
    #   complet, insa radacina „ISRG Root YR" lipseste SI din magazinul sistemului SI din certifi
    #   2026.05.20 (testate separat, pica identic). http:// face 301 la https, deci nu exista
    #   ocolire. Adaugat asa, ar fi permanent `dead`. De testat pe un runner inainte, nu aici.
    # · `dobrogeanoua.ro` — mort definitiv, nu e o problema de cale: e o pagina statica index.php
    #   cu 13 linkuri si ani 2010-2016, fara robots/sitemap. CONSTANTA e oricum acoperita.
    # regional — publicatii MULTI-JUDET pe regiuni istorice (cercetare agenti + feedcheck
    # run 29776432687, 2026-07-20). 16 cu feed VIU. Cazuti (nu re-adauga fara re-test):
    # transilvaniareporter=timeout (posibil lent, re-testabil), crisanaonline=301 loop,
    # ziarulevenimentul=404, bucovinamedia/dobrogeatv=0 intrari. Exclusi motivat: TransilvaniaON
    # (retea SEO), pressalert (deja judetean), gds.ro (403 recurent), newsmoldova (amesteca Chisinau).
            "ziarultransilvaniei":  {"name": "Ziarul Transilvaniei",  "url": "https://ziarultransilvaniei.ro/feed/",   "category": "regional"},
            "gazetadetransilvania": {"name": "Gazeta de Transilvania","url": "https://gazetadetransilvania.ro/feed/",  "category": "regional"},
            "expressdebanat":       {"name": "Express de Banat",      "url": "https://expressdebanat.ro/feed/",        "category": "regional"},
            "ziuadevest":           {"name": "Ziua de Vest",          "url": "https://www.ziuadevest.ro/feed/",        "category": "regional"},
            "banatnews":            {"name": "Banat-News",            "url": "https://banat-news.ro/feed/",            "category": "regional"},
            "criticarad":           {"name": "Critic Arad",           "url": "https://www.criticarad.ro/feed/",        "category": "regional"},
            "zch":                  {"name": "ZCH News",              "url": "https://zch.ro/feed/",                   "category": "regional"},
            "stirilemoldovei":      {"name": "Știrile Moldovei",      "url": "https://stirilemoldovei.ro/feed/",       "category": "regional"},
            "newsbucovina":         {"name": "NewsBucovina",          "url": "https://www.newsbucovina.ro/feed/",      "category": "regional"},
            "stirimuntenia":        {"name": "Știri din Muntenia",    "url": "https://stiri-muntenia.ro/feed/",        "category": "regional"},
            "zdp":                  {"name": "Ziarul de Ploiești",    "url": "https://www.zdp.ro/feed/",               "category": "regional"},
            "jurnalulolteniei":     {"name": "Jurnalul Olteniei",     "url": "https://jurnalulolteniei.ro/feed/",      "category": "regional"},
            "cronicaolteniei":      {"name": "Cronica Olteniei",      "url": "https://cronicaolteniei.ro/feed/",       "category": "regional"},
            "stirileolteniei":      {"name": "Știrile Olteniei",      "url": "https://stirileolteniei.ro/feed/",       "category": "regional"},
            "dobrogeanews":         {"name": "DobrogeaNews",          "url": "https://www.dobrogeanews.ro/feed/",      "category": "regional"},
            "dobrogeaonline":       {"name": "Dobrogea Online",       "url": "https://www.dobrogeaonline.ro/feed/",    "category": "regional"},
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
            "piataauto": {"name": "Piata Auto MD", "url": "https://piataauto.md/sitemap-news.xml", "category": "auto", "type": "sitemap_news", "enrich_sitemap": True},
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
_gold = load_gold_sources(_GOLD_CSV, int(os.environ.get("LOCAL_GOLD_LIMIT", "120")))
# Bugetul AI proceseaza in ordinea dictului (niche-first) -> sursele locale intra
# imediat dupa blocul 'local' literal, nu la coada (altfel sunt infometate de buget).
if _gold:
    _items = list(SOURCES.items())
    _idx = max((i for i, (_k, _v) in enumerate(_items) if _v.get("category") == "local"),
               default=len(_items) - 1)
    _items[_idx + 1:_idx + 1] = list(_gold.items())
    SOURCES = dict(_items)

# Exclude orice URL/sursă de agenție (verificare suplimentară pe domeniul linkului)
AGENCY_BLOCKLIST = ["agerpres", "mediafax", "reuters", "afp.com", "apnews", "ap.org"]

CATEGORIES = ["general", "politic", "economic", "extern", "tech", "sport",
              "auto", "sanatate", "cultura", "lifestyle", "discounturi",
              "regional", "judetean", "local"]

# Categorii in INSAMANTARE: nou-adaugate, cu surse de volum mic — pot fi goale fara sa pice
# QA (warn, nu FAIL). Se scot de aici dupa ce categoria s-a populat stabil.
SEED_CATEGORIES = {"regional", "judetean", "local"}

# Categorii GEOGRAFICE (axa proprie): articolele surselor cu aceste categorii NU sunt
# re-clasificate pe tema de catre AI (vezi process._resolve_category). Un ziar judetean
# ramane in sectiunea 'local', nu ajunge pe sport/politic dupa continut.
PINNED_CATEGORIES = {"regional", "judetean", "local"}

# Categorii care si-au schimbat NUMELE de-a lungul timpului. Istoricul lui
# `data/articles.json` pastreaza articolele vechi sub numele de atunci, iar o categorie
# moarta nu mai primeste pagina de articol la randare, dar tot produce linkuri catre ea
# din listari -- adica exact legaturi interne rupte. Orice cod care scoate articole din
# istoric trece prin harta asta (vezi tools/recupereaza_404.py).
CATEGORII_REDENUMITE = {"zonal": "judetean"}

# Etichete AFISATE (owner 2026-07-17): slug-ul din URL ramane neschimbat (SEO), doar
# textul din nav/titluri/carduri foloseste aceste nume. Fallback = slug capitalizat.
# EXCEPTIE explicita a owner-ului (2026-08-12): categoria 'zonal' a fost redenumita
# 'judetean' inclusiv in slug/URL, cu redirect 301 de la /zonal/* -- vezi render.py
# (_write_redirects) si tools/migrate_zonal_to_judetean.py pentru cele 295 de articole
# deja publicate sub vechiul slug.
CATEGORY_LABELS = {
    "general": "Actualitate", "politic": "Politică", "economic": "Economie",
    "extern": "Externe", "tech": "Tech", "sport": "Sport", "auto": "Auto",
    "sanatate": "Sănătate", "cultura": "Cultură", "lifestyle": "Lifestyle",
    "discounturi": "Discounturi", "regional": "Regional", "judetean": "Județean", "local": "Local",
}

# Cate cuvinte trebuie sa aduca `description` PESTE titlu ca itemul sa merite sintetizat.
# Sub prag nu exista nimic de sintetizat, iar un model caruia i se cere totusi un rezumat nu
# poate produce decat o parafraza a titlului — daca titlul e clickbait, iese clickbait fluent,
# care trece de orice verificare de FORMA. Vezi `specs/sinteza-fara-substanta.md`.
# Pragul 5 e ales pe distributia masurata (2026-08-04, 256 de iteme): 56 de iteme au 0 cuvinte
# noi, 2 au 1-4, 17 au 5-9, 181 au 10+. Deci taie exact grupul imposibil (23%) si lasa in pace
# zona ambigua. E o manetă: ridicat la 10 ar taia 29%.
# NU se aplica surselor oficiale (pl_/cj_/pr_) — alea nu trec prin AI deloc (`process_official`).
MIN_SUBSTANTA_CUVINTE = 5

# Model B+C
PROMPT_VERSION = "v2-esenta"  # versiunea regulilor AI; la schimbare, articolele vechi se reprocesează
BATCH_SIZE = 10                # articole model-B procesate intr-UN singur apel AI (economie quota).
# clustere model-C procesate intr-UN singur apel AI. MASURAT 2026-08-16: cate un apel per
# cluster epuiza bugetul la 17-18 clustere/rulare, lasand 0 apeluri pentru model B -- coada
# de articole amanate a crescut monoton 0->84->152->220 in 8 ore (4 citiri din build.yml).
# 3 e un compromis: destul de mic ca sursele evenimentelor sa nu se amestece in promptul AI
# (fiecare cluster ramane un bloc separat, etichetat), destul de mare ca 17-18 clustere sa
# incapa in ~6 apeluri in loc de 17-18. Vezi process.py:process_clusters_batch. Cautat in
# registru inainte (`cluster batch`, `model c`, `buget AI`): niciun precedent respins.
CLUSTER_BATCH_SIZE = 3
                               # Ridicat 6->10 (owner 2026-08-02, "riscam, vedem ce iese"): ~+67%
                               # articole/rulare. Cere maxOutputTokens marit (gemini.py, 4096) ca
                               # lotul JSON sa nu se trunchieze -> altfel pierdere tacuta de lot.
TITLE_MAX_WORDS = 22           # titlu: soft-cap care transmite faptul complet (nu mai taie la 12)
TEASER_MAX_WORDS = 40          # B: teaser scurt ("extras foarte scurt")
SYNTHESIS_MAX_WORDS = 90       # C: sinteză multi-sursă (doar pentru clustere importante)
CLUSTER_MIN_SOURCES = 2        # >=2 surse pe același eveniment -> candidat pentru C
RELATED_MIN_SHARED = 2         # "Articole conectate": minim entitati comune. 1 singura entitate
                               # comuna (de regula o tara larga: "Franța") = zgomot, nu relevanta.
# Cat timp ramane un articol PUBLICAT. `state.expire()` sterge din stare tot ce trece de prag,
# iar site-ul fiind generat static asta inseamna ca PAGINA DISPARE: Google ramane cu adresa in
# index si serveste 404 cititorului.
#
# Ridicat 7 -> 30 (owner 2026-08-20), dupa ce Search Console a aratat 193 de pagini "Nu a fost
# gasita". Verificat pe exportul lor: 186 din 186 nu mai erau in `articles.json`, iar unul
# urmarit prin istoric (`seceta-extrema-...-albia-dunarii`) fusese adaugat pe 5 aug si sters pe
# 10 aug, in commitul `897f180f` care a scos 107 articole intr-o singura rulare. Efectul se
# vedea in trafic: "maria baetica" - pozitia 7,5 in Google, 18 afisari, ZERO clicuri, fiindca
# pagina nu mai exista.
#
# Motivul vechi ("incape in quota free Gemini") NU se sustine: `state.merge()` pastreaza
# articolele existente cu procesarea lor, deci un articol vechi nu mai consuma niciun apel AI,
# iar consumul e plafonat separat prin `max_ai_calls`. Constrangerea reala e DIMENSIUNEA:
# `data/articles.json` e comis in repo la fiecare rulare (~12/zi). Masurat la TTL 7: 5.062
# articole = 5,9 MB (~1.186 octeti/articol, ~723 articole/zi). Proiectie: 30 zile ~ 21.700
# articole ~ 25 MB; 90 de zile ar da ~77 MB - de aceea 30, nu mai mult.
#
# Doua efecte secundare cunoscute, cautate in registru inainte de schimbare:
#   IZZ-0104 - pipeline-ul sare itemele din feed deja peste TTL (main.py:486). Cu pragul la 30,
#     stiri de pana la 30 de zile din feeduri devin eligibile. Bugetul ramane plafonat de
#     `max_ai_calls`, deci costul nu creste; se schimba doar CE intra in el.
#   IZZ-0143 - cele 62 de articole din surse fara substanta erau lasate "sa expire pe TTL".
#     Acum raman 30 de zile, nu 7. Daca deranjeaza, se curata explicit, nu prin scurtarea TTL.
# Efect pozitiv colateral: setul de aur pentru masuratori nu mai erodeaza la fel de repede
# (STATE.md nota 17 din 40 de randuri deja expirate).
#
# Plafonul se ridica definitiv doar prin arhiva separata de starea de lucru (paginile raman
# publicate, articolele ies doar din procesare) - proiect separat, programat pe 21 aug.
ARTICLE_TTL_DAYS = 30

# Plafonul de fisiere al gazdei. Cloudflare Pages Free refuza deploy-ul peste 20.000 de
# fisiere si NU raporteaza inapoi in pipeline: jobul de continut trece verde, iar esecul
# apare 25 de minute mai tarziu in `release-probe`, ca "izz.ro serveste <sha vechi>".
# Asa a stat site-ul inghetat 21 de ore pe 63bcc9bd (2026-08-21 10:25 -> 08-22 07:00),
# cu sase rulari complete picate una dupa alta. Bracket masurat: 19.987 fisiere = deploy
# verde, 20.337 = build picat.
#
# Randarea nu mai are voie sa lase marimea output-ului pe seama ingestului. Bugetul de
# mai jos e ce respecta EA, sub plafonul real, iar marja acopera derivatele webp care nu
# se pot prezice inainte de scriere. Ridica-l doar impreuna cu o masuratoare noua a
# plafonului gazdei -- nu "ca sa incapa".
OUTPUT_FILE_BUDGET = int(os.getenv("OUTPUT_FILE_BUDGET", "19500"))
# Fisierele care NU stau in directoarele de articol: static, categorii cu paginare,
# subiecte + feedurile lor, ghiduri, instrumente, harta, sitemapuri, feed, cautare.
# MASURAT pe o randare reala din 2026-08-22: 3.483 de fisiere care nu sunt nici pagina de
# articol, nici imagine de articol (`python tools/count_output.py`). Include paginile de
# paginare si de subiect, care stau INAUNTRUL directoarelor de categorie -- o prima
# masuratoare le-a numarat gresit ca pagini de articol si bugetul a iesit cu 183 de fisiere
# peste. Cifra de aici e rotunjita in sus, ca marja.
# Se scade din buget INAINTE de imparteala pe articole: paginile de articol au prioritate
# absoluta, imaginile se dau din ce ramane. Remasoara dupa orice rubrica sau sectiune noua.
OUTPUT_NON_ARTICLE_RESERVE = int(os.getenv("OUTPUT_NON_ARTICLE_RESERVE", "3600"))
MAX_PER_SOURCE = 8             # redus de la 12 ca sa scada apelurile AI/rulare
# Homepage-ul este un tablou de bord, nu arhiva zilei: patru carduri per categorie pastreaza
# orientarea larga, iar restul raman accesibile prin pagina de categorie. Limita reduce DOM-ul
# si timpul de citire initial, fara a taia acoperirea editoriala sau indexarea individuala.
HOME_CARDS_PER_CATEGORY = 4

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")  # "gemini" | "anthropic" | "ollama" (local, gratuit — vezi generator/providers/ollama.py)
# Fallback AUTOMAT pe Qwen local cand providerul de mai sus (gemini/anthropic) esueaza (429,
# quota, cheie lipsa) -- vezi process.get_provider(). Implicit ON: fara Ollama pornit local,
# `available()` esueaza rapid si nu schimba nimic. Se dezactiveaza cu AI_FALLBACK_OLLAMA=0.
AI_FALLBACK_OLLAMA = os.getenv("AI_FALLBACK_OLLAMA", "1") == "1"
# Router multi-provider opt-in. Fluxul legacy Gemini + Ollama ramane implicit.
AI_ROUTER_MODE = os.getenv("AI_ROUTER_MODE", "legacy").strip().lower()
AI_FALLBACK_PROVIDERS = os.getenv("AI_FALLBACK_PROVIDERS", "").strip()

# IndexNow (Bing/Seznam/Yandex): cheia e PUBLICA prin protocol (motorul o citeste de la
# https://izz.ro/<cheie>.txt ca dovada ca detinem domeniul). render.py scrie fisierul,
# tools/indexnow_submit.py anunta URL-urile noi la fiecare rulare a pipeline-ului.
INDEXNOW_KEY = "f9b2f9cd7e5e9677f83454b525ad2c77"
