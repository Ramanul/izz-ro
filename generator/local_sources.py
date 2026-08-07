import csv
import os
import re

from . import localities

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
    for row in rows[:limit]:
        slug = _make_slug(row["judet"], row["localitate"])
        key = "pl_" + slug
        if key not in result:
            result[key] = {
                "name": nume_primarie(row["judet"], row["localitate"], _by_name),
                "url": row["rss_url"].strip(),
                "category": "local",
            }

    return result
