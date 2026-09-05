import csv
import os
import re

from collections import Counter

from . import localities

# Normalizare pentru potrivirea codurilor de judet („ARGES", fara diacritice, cum vin in
# CSV) cu etichetele din gazetteer („Argeș"). Ambele variante de s/t sub litera exista in
# natura — cedilla U+015F/U+0163 SI virgula U+0219/U+021B — deci le acopar explicit; un
# singur cod lipsa duce la nume fara județ exact la omonimele pe care le depanez aici.
_DIA = str.maketrans({
    "ă": "a", "â": "a", "î": "i", "ș": "s", "ş": "s", "ț": "t", "ţ": "t",
    "Ă": "A", "Â": "A", "Î": "I", "Ș": "S", "Ş": "S", "Ț": "T", "Ţ": "T",
})


def _norm(s: str) -> str:
    """Forma de potrivire: litere mici... ba NU — codurile din CSV sunt MAJUSCULE, deci
    normalizarea le păstrează și scoate doar diacriticele."""
    return (s or "").translate(_DIA).upper()

# Prefixul administrativ din CSV („MUNICIPIUL PLOIESTI"). Acelasi tipar ca `localities._PREFIX`,
# scris aici ca sa nu depindem de un nume privat din alt modul.
_PREFIX_ADMIN = re.compile(r"^(MUNICIPIUL?|ORA[SȘ](UL)?|COMUNA)\b\s*", re.I)


# Potrivire pe CUVANT INTREG, nu substring: "ORASTIOARA DE SUS" e o COMUNA, dar contine
# "ORAS" -- cu `in` era clasificata gresit ca oras (bug real, prins la review 2026-07-24).
# `MUNICIPIUL?` accepta si forma fara -L, ca o scriere diferita in CSV sa nu cada tacut la comuna.
_MUNICIPIU_RE = re.compile(r"\bMUNICIPIUL?\b")
_ORAS_RE = re.compile(r"\bORA[SȘ](UL)?\b")


# Primarii care erau GOLD la scanarea initiala dar sunt MOARTE sau GOALE acum, masurate pe
# feedcheck run 30121199000 (2026-07-24), prima verificare completa dupa LOCAL_GOLD_LIMIT=120.
# Scopul listei nu e igiena, ci CONTINUT: fara ea ocupa 10 din cele 120 de sloturi degeaba,
# iar candidatii de pe pozitiile 121+ (probabil vii) raman pe dinafara. Se aplica INAINTE de
# taierea la limita, deci fiecare slug scos elibereaza slotul pentru urmatorul candidat.
# Daca o sursa isi revine, sterge-i linia si reruleaza feedcheck ca sa confirmi.
_DEAD_SLUGS = frozenset({
    "covasna_oras_intorsura_buzaului",    # network unreachable
    "timis_oras_gataia",                  # DNS: name resolution failed
    "dolj_oras_segarcea",                 # 200 dar 0 intrari
    "galati_oras_beresti",                # 200 dar 0 intrari
    "galati_oras_targu_bujor",            # 200 dar 0 intrari
    "giurgiu_oras_mihailesti",            # 200 dar 0 intrari
    "prahova_oras_plopeni",               # 200 dar 0 intrari
    "valcea_oras_babeni",                 # 200 dar 0 intrari
    # 403 WAF de pe runnerii GitHub (feedcheck 30096781843). Conteaza pentru ca build.yml
    # ruleaza pe ACEIASI runneri: daca verificatorul nu trece de WAF, nici pipeline-ul nu trece.
    # Nu inseamna „site mort" — inseamna „inaccesibil de acolo de unde tragem noi".
    "vaslui_dragomiresti",
    # Confirmata pe DOUA rulari feedcheck consecutive, la ~12h distanta si de pe runneri
    # diferiti: 30125482616 (24 iul) si 30152246525 (25 iul). In amandoua e SINGURA sursa
    # moarta din cele 120, acelasi 403 pe primariatacuta.ro -- deci WAF stabil, nu o pana.
    "vaslui_tacuta",
    # COMPROMIS, nu mort (2026-08-09). primariarovinari.ro raspunde 200 si feed-ul merge --
    # exact de-asta e periculos: `rss_ok=yes` in gold_integrare.csv, deci ar reintra la fiecare
    # rulare. WordPress-ul lor e spart si publica pagini de warez la ~3h fix (03:51, 06:51,
    # 09:51 ...), intercalate cu anunturi reale ale primariei. 8 astfel de pagini au ajuns pe
    # izz.ro pe 8-9 aug. Verificat live de pe alta retea decat runnerii CI (curl direct pe
    # /feed/, 9 aug 19:20): titlurile de warez sunt inca acolo, plus unul nou aparut intre timp.
    # Excluderea aici opreste re-ingestia; `moderation.yaml` ascunde ce e deja in articles.json.
    # Se scoate din lista DOAR dupa ce primaria curata site-ul si feed-ul e reverificat manual.
    #
    # REVERIFICAT 2026-08-12: feed-ul e CURAT. `curl -sSL https://www.primariarovinari.ro/feed/`
    # -> 200, 53929 octeti, 12 titluri, **0 ostile** trecute prin `guard.verdict` + `anomalie`
    # (toate anunturi reale: concursuri, colectare deseuri, ambrozie). Conditia din R6 pentru
    # ridicarea suprimarii ESTE indeplinita.
    # **Suprimarea ramane totusi, si nu din inertie:** un feed curat azi nu dovedeste ca CMS-ul
    # a fost patch-uit — atacatorul poate avea inca acces. Reactivarea schimba ce apare PUBLIC
    # pe izz.ro, deci e decizia proprietarului, nu a unei masuratori. E o linie de sters.
    # Riscul reactivarii e acum materialmente mai mic decat pe 9 aug: `guard.carantina`
    # (stratul 9) taie automat tot lotul sursei la >=2 respingeri intr-o rulare.
    "gorj_oras_rovinari",
    # COMPROMIS (2026-08-09, descoperit abia pe 11 aug). cajvana.ro a fost DEFACED: un articol
    # intitulat „Hacked by Chinafans", cu corp „Hacked By Chinafans https://t.me/Hack_0xTeam
    # https://t.me/Hello_root", link https://cajvana.ro/0x-htm-1906/. A ajuns pe izz.ro si a stat
    # live doua zile, la https://izz.ro/local/hacked-by-chinafans/ (HTTP 200, verificat).
    # DE CE A SCAPAT, si de-asta conteaza: nu are warez, nici markup, nici homoglife, nici titlu-
    # gunoi — deci TOATE cele cinci straturi din `guard.verdict` l-au lasat sa treaca. E cazul care
    # dovedeste ca apararea pe cuvinte nu e suficienta si ca ai nevoie de anomalie pe COMPORTAMENTUL
    # sursei: o primarie romaneasca cu 100% titluri in romana care publica brusc unul in engleza.
    # `guard.anomalie` il prinde din primul articol; l-am gasit tocmai masurand pentru garda aia.
    # Site-ul nu raspundea la verificarea din 11 aug 20:2x (curl -> 000, conexiune esuata), deci
    # nu s-a putut confirma daca e inca defaced sau a fost luat jos.
    #
    # REVERIFICAT 2026-08-12 — raspunsul e mai tare decat „luat jos": **domeniul nu mai exista.**
    # `nslookup cajvana.ro` da NXDOMAIN pe TREI resolvere independente (local, 1.1.1.1, 8.8.8.8),
    # cu control pozitiv pe acelasi resolver (`primariarovinari.ro` -> 92.83.6.19), deci nu e o
    # problema de retea la noi. Nici `www.cajvana.ro`, `primariacajvana.ro`,
    # `www.primariacajvana.ro` nu raspund (curl -> 000).
    # Consecinta: sursa e MOARTA, nu doar compromisa — n-are cum sa reintre. Suprimarea ramane
    # ca document al incidentului. Daca domeniul reapare, e o entitate NOUA si se reverifica de
    # la zero inainte de orice reactivare.
    "suceava_oras_cajvana",
    # Feed verificat 2026-08-18: comunaluncavita.ro/rss.xml raspunde 302 in bucla catre
    # /#E403, iar itemele nu trec garda http/https. Se reactiveaza doar dupa repararea
    # endpointului si o reverificare manuala a feedului.
    "tulcea_luncavita",
    # COMPROMIS (2026-09-05). Feed-ul primariei Plenita publica spam cazino intercalat cu
    # anunturi reale, exact tiparul Rovinari: „Chicken Cross the Road Gambling Game Review
    # for Canada", „VulkanSpieleBonus Polish App" — prins de garda lingvistica la primul
    # fetch al listei rescanate (104s/308 surse), apoi carantinat automat (2 din 8 iteme
    # respinse in aceeasi rulare). Suprimarea opreste re-ingestia; se scoate doar dupa ce
    # primaria curata site-ul si feed-ul e reverificat manual prin garda.
    "dolj_plenita",
})


def nume_primarie(judet: str, localitate: str, by_name: dict) -> str:
    """Numele AFISAT al sursei, cu diacritice si fara prefixul administrativ.

    De ce nu `"Primăria " + localitate.title()`, cum era: coloana `localitate` din
    `primarii_status.csv` e in MAJUSCULE FARA DIACRITICE, iar `.title()` nu le poate inventa.
    Masurat pe `data/articles.json` la 2026-08-06: **39 de nume distincte stricate, pe 143 de
    articole** — „Primăria Municipiul Sebes" (corect: Sebeș), „Primăria Oras Navodari"
    (Năvodari). Numele apare pe FIECARE card al sursei, deci e cea mai vizibila greseala de pe
    site, si e in plus inconsistenta: „Primăria" avea diacritice, restul numelui nu.

    Diacriticele se recupereaza din `data/localities.json` (3179 de UAT-uri de la Wikidata),
    prin `localities.match`, care cere potrivire pe JUDET — obligatoriu, fiindca 12 din cele
    120 de primarii GOLD au omonime in alte judete.

    Prefixul administrativ se scoate deliberat: forma „Primăria Municipiul Ploiesti" e gresita
    gramatical (ar cere genitivul, „Municipiului"), iar declinarea corecta ar adauga un caz de
    intretinut fara ca cititorul sa castige ceva. „Primăria Ploiești" e scurt, corect si
    identic ca forma cu intrarile scrise de mana din `config.py` („Primăria Buzău").

    Fara potrivire in dataset -> comportamentul vechi, `.title()` pe numele din CSV. Sursa
    ramane utilizabila; un nume imperfect e mai bun decat o sursa pierduta.
    """
    curat = _PREFIX_ADMIN.sub("", (localitate or "").strip())
    rec = localities.match(judet, curat, by_name) if by_name else None
    return "Primăria " + (rec["label"] if rec else curat.title())


# Cele doua coduri de judet care lipsesc din gazetteerul Wikidata (masurat 2026-09-05 pe
# toate codurile din primarii_status: BUCURESTI, VALCEA). Numere oficiale, nu inventate.
_ETICHETE_JUDETE_MANUALE = {"BUCURESTI": "București", "VALCEA": "Vâlcea"}


def _impact_tier(localitate: str) -> int:
    """Prioritate de IMPACT, dedusa STATIC din numele localitatii (nu re-analiza la runtime):
    municipiu (oras mare) inaintea orasului, orasul inaintea comunei. Reper cheie: un primar
    de municipiu are zeci de mii de cititori vs. o comuna de cateva sute -> incarcam intai
    localitatile mari, apoi comunele pentru acoperire. Marile resedinte de judet (Cluj, Iasi...)
    lipsesc din lista GOLD -- site-urile lor n-au RSS -- deci municipiile sunt varful disponibil."""
    loc = localitate.upper()
    if _MUNICIPIU_RE.search(loc):
        return 0
    if _ORAS_RE.search(loc):
        return 1
    return 2  # comuna


def _etichete_judete(by_name: dict) -> dict:
    """Cod de judet („ARGES") -> eticheta cu diacritice („Argeș"), din gazetteer.

    Nevoie reala: omonimele de localitate legitime (3x Ștefănești in Botoșani/Argeș/Vâlcea,
    2x Beclean, 2x Vidra) produceau nume afisate identice pe surse DIFERITE, iar catalogul
    de surse cere unicitate (test_render_sources::test_catalog_respects_one_axis_one_home,
    masurat 397 nume pe 392 unice la primele 300 surse). Județul in paranteza disambigueaza.
    """
    etichete: dict = {}
    for intrari in by_name.values():
        for e in intrari:
            brut = (e.get("judet") or "").strip()
            if brut:
                curat = re.sub(r"^Jude[tț]ul\s+", "", brut).strip()
                if curat:
                    etichete.setdefault(_norm(curat), curat)
    for cod, eticheta in _ETICHETE_JUDETE_MANUALE.items():
        etichete.setdefault(cod, eticheta)
    return etichete


def _make_slug(judet: str, localitate: str) -> str:
    raw = f"{judet}_{localitate}".lower()
    slug = re.sub(r"[^a-z0-9]", "_", raw)
    slug = re.sub(r"_+", "_", slug)
    slug = slug.strip("_")
    return slug


def load_gold_sources(csv_path: str, limit: int, min_date: str = "2026-01-01") -> dict:
    if limit <= 0:
        return {}
    if not os.path.isfile(csv_path):
        return {}

    rows = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rss_url = (row.get("rss_url") or "").strip()
            if row.get("rss_ok") == "yes" and rss_url:
                last_date = (row.get("last_signal_date") or "").strip()
                if last_date and last_date >= min_date:
                    # exclus INAINTE de taierea la limita: slotul eliberat se duce
                    # automat la urmatorul candidat viu, nu se pierde
                    if _make_slug(row["judet"], row["localitate"]) in _DEAD_SLUGS:
                        continue
                    rows.append(row)

    # sortare STATICA in 2 pasi (sort stabil): intai prospetime desc, apoi nivel de impact asc.
    # Rezultat: municipiile cele mai active primele, apoi orasele, apoi comunele -> primele
    # `limit` sloturi merg la localitatile cu cel mai mare impact, nu la comune la intamplare.
    rows.sort(key=lambda r: (r["judet"], r["localitate"]))
    rows.sort(key=lambda r: r.get("last_signal_date") or "", reverse=True)
    rows.sort(key=lambda r: _impact_tier(r["localitate"]))

    # o singura incarcare pentru toate randurile (fisier de ~370 KB); `{}` daca lipseste,
    # caz in care `nume_primarie` cade pe `.title()` si sursele raman utilizabile
    _by_name = localities.load_dataset()

    result = {}
    judet_by_key: dict = {}
    for row in rows[:limit]:
        slug = _make_slug(row["judet"], row["localitate"])
        key = "pl_" + slug
        if key not in result:
            result[key] = {
                "name": nume_primarie(row["judet"], row["localitate"], _by_name),
                "url": row["rss_url"].strip(),
                "category": "local",
            }
            judet_by_key[key] = row["judet"]

    # omonimele legitime primesc județul in paranteza, ca numele afisat sa fie unic
    # (vezi _etichete_judete: 3x Ștefănești, 2x Beclean, 2x Vidra — masurat pe 300 surse)
    if result:
        _dubluri = {n for n, c in Counter(v["name"] for v in result.values()).items() if c > 1}
        if _dubluri:
            _et = _etichete_judete(_by_name)
            for _key, _v in result.items():
                if _v["name"] in _dubluri:
                    _etiqueta = _et.get(_norm(judet_by_key.get(_key, "").upper()))
                    if _etiqueta:
                        _v["name"] = f"{_v['name']} ({_etiqueta})"

    return result
