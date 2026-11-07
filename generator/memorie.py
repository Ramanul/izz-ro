"""E4 — memoria subiectelor: un registru mic, separat de fereastra de 11 zile, cu DECIZIILE
ÎNCHEIATE pe care sursele le-au confirmat (`specs/plan-paradigma-izz.md` §3 E4).

De ce există: fereastra TTL face site-ul finit (P10), dar o lege promulgată acum patru luni
e context legitim pentru știrea de azi despre aceeași lege. Registrul ține un rând per subiect:
data, titlul nostru, faptul central confirmat, publicațiile, entitățile — nimic din textul
surselor. Plafon: 12 luni, câteva sute de KB pe an.

Garda Memoriei (Argon R3 — „singura eroare fatală rămasă", reparată aici, mecanic):
- intră DOAR ce sinteza dialectică a marcat `milestone` (decizie finală / eveniment încheiat),
  în stare validă, fără nicio rezervă la sursă;
- NU intră nicio stare judiciară, litigiu sau acuzație (nici din text, nici din entități),
  oricât de „încheiată" ar părea formularea — registrul ar îngheța o persoană într-o stare
  trecută: un cazier automat fără drept de apel;
- sub-clusterele aceluiași eveniment din zile apropiate se unifică într-o singură intrare;
- o corecție sau o retragere (`moderation.yaml`) scoate rândul și din registru, nu doar din
  fereastra activă.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone

from . import config, guard
from .util import normalize_url
from .verifica_sinteza import _norm

CALE = os.path.join(config.ROOT, "data", "memory_ledger.json")
ZILE_PASTRARE = 365
MIN_ENTITATI_COMUNE = 2
MAX_INTRARI = 3000
FEREASTRA_DEDUP_ZILE = 3

# Vocabular penal, contravențional, litigios și de integritate: un fapt sau o entitate care îl
# conține nu intră în memorie, oricât de definitiv ar suna — agregarea automată a unor astfel de
# stări pe știri noi, luni mai târziu, ar fi un cazier fără drept de apel (Argon R3; R5:
# „condamnat definitiv" e exclus și el — GDPR art. 10, reabilitare). Deciziile CCR rămân: sunt
# constituționalitate, nu zonă penală ori litigiu individual. Rădăcini fără diacritice.
_JUDICIAR = re.compile(
    r"\b(?:suspect|banuit|anchet|acuz|inculpa|imputat|arest|retinu|retinere|audiat|cercetat|"
    r"cercetare|urmarir|perchezit|flagrant|plangere|denunt|prejudici|condamn|achita|dosar|"
    r"procuror|parchet|diicot|dna\b|eppo\b|ani\b|instant|judecat|tribunal|pedeaps|penal|"
    r"infractiun|fraud|delapid|mit[aei]\b|spag|coruptie|trafic de influenta|conflict\w* de interes|"
    r"incompatibil|plagiat|amend|sanctionat|violen|agresi|crim|omor|ucis|viol|abuz|victim|dispar|"
    r"litigi|intentat|chemat\w*\s+in\s+judecat|actiun\w*\s+in\s+instant|execut\w*\s+silit|"
    r"iccj\b|inalta\s+curte|curtea\s+de\s+apel|"
    r"(?:pierdut|castigat)\s+(?:definitiv\s+)?(?:al\s+\w+\s+)?proces(?:ul|ele|elor|ului)?\b)",
)

# Cuvinte funcționale/participii englezești rămase netraduse în ieșirea modelului și formule
# evaluative de titlu care încalcă registrul de proces-verbal al memoriei pe termen lung.
_ENGLEZA_SCAPATA = re.compile(
    r"\b(?:surpassing|following|meanwhile|however|according|despite|amid|against|during|"
    r"between|announced|defeated|winning|breaking|ahead\s+of|after\s+the)\b",
)
_EPITETE_EVALUATIVE = re.compile(
    r"\b(?:victori[ae]\s+(?:categoric|zdrobitoar|spectaculoas|rasunatoar|uluitoar)|"
    r"infranger[ea]\s+(?:usturatoar|rusinoas|umilitoar|categoric)|"
    r"scandal\w*\s+urias|lovitur[ae]\s+de\s+teatru)",
)
_PREFIX_CLUB = re.compile(r"^(?:fc|ac|as|afc|cf|csm|acs|cs|sc|fk|sk|nk|ud)\s+")
_URL_DUBLU = re.compile(r"^https?://[^/?#\s]+/?(https?://\S+)$", re.I)

# Entități prea generale ca să lege singure două subiecte (Argon R5): aproape orice știre politică
# are („Guvernul", „România") sau („PSD", „PNL"). Nu se numără la pragul de entități comune.
_GENERICE = frozenset("""
romania romaniei guvern guvernul guvernului executivul parlament parlamentul senat senatul
camera deputatilor presedintia presedintele administratia prezidentiala premierul ministerul
uniunea europeana ue comisia europeana nato onu sua statele unite rusia ucraina europa
psd pnl usr aur udmr pmp sos
bucuresti alba arad arges bacau bihor bistrita-nasaud botosani braila brasov buzau calarasi
caras-severin cluj cluj-napoca constanta covasna dambovita dolj galati giurgiu gorj harghita
hunedoara ialomita iasi ilfov maramures mehedinti mures neamt olt prahova salaj satu mare sibiu
suceava teleorman timis timisoara tulcea valcea vaslui vrancea craiova ploiesti oradea pitesti
""".split()) | {"camera deputatilor", "uniunea europeana", "comisia europeana", "statele unite",
                "satu mare", "administratia prezidentiala"}

_CUVANT = re.compile(r"[a-z]{6,}")  # după `_norm`: litere mici, fără diacritice
_COMUNE = frozenset("""
pentru despre dintre impotriva asupra privind potrivit aceasta acestea acestui acestei
fiindca deoarece totusi inclusiv anunta anuntat declarat afirmat precizat spune spunea
astazi saptamana anului octombrie noiembrie decembrie ianuarie februarie septembrie
""".split())


def _canon(entitate: str) -> str:
    return re.sub(r"\s+", " ", _norm(entitate)).strip()


def _specifice(entitati) -> set:
    out = set()
    for e in entitati or []:
        c = _canon(e)
        if c and c not in _GENERICE and c.split(" ")[0] not in _GENERICE:
            out.add(c)
    return out


def _cuvinte_cheie(text: str, excluse: set) -> set:
    """Rădăcini de 6 litere ale cuvintelor lungi: flexiunea românească („producția" /
    „producției", „casnică" / „casnice") nu are voie să rupă potrivirea."""
    toks = set(_CUVANT.findall(_norm(text)))
    excl = {w[:6] for e in excluse for w in e.split()}
    return {t[:6] for t in toks if t not in _COMUNE and t[:6] not in excl}


def _curata_url(url: str) -> str:
    """Repară URL-urile din feeduri care lipesc gazda în fața unui link deja absolut."""
    u = (url or "").strip()
    m = _URL_DUBLU.match(u)
    return m.group(1) if m else u


def _text_eligibil(titlu: str, fapt: str, entitati) -> bool:
    ent_text = " ".join(str(e) for e in (entitati or []))
    complet = _norm(f"{titlu or ''} {fapt or ''} {ent_text}")
    if _JUDICIAR.search(complet):
        return False
    proza = _norm(f"{titlu or ''} {fapt or ''}")
    if _ENGLEZA_SCAPATA.search(proza) or _EPITETE_EVALUATIVE.search(proza):
        return False
    return True


def _ent_dedup(entitati) -> set[str]:
    out = set()
    for e in _specifice(entitati):
        scurt = _PREFIX_CLUB.sub("", e).strip()
        if scurt:
            out.add(scurt)
    return out


def _acelasi_eveniment(a: dict, b: dict) -> bool:
    """Două intrări din zile apropiate (≤3 zile) care descriu același eveniment sub-clusterizat."""
    try:
        da = date.fromisoformat((a.get("d") or "")[:10])
        db = date.fromisoformat((b.get("d") or "")[:10])
    except ValueError:
        return False
    if abs((da - db).days) > FEREASTRA_DEDUP_ZILE:
        return False
    comune = _ent_dedup(a.get("ent")) & _ent_dedup(b.get("ent"))
    if len(comune) < MIN_ENTITATI_COMUNE:
        return False
    chei_a = _cuvinte_cheie(f"{a.get('titlu') or ''} {a.get('fapt') or ''}", comune)
    chei_b = _cuvinte_cheie(f"{b.get('titlu') or ''} {b.get('fapt') or ''}", comune)
    return len(chei_a & chei_b) >= 2


def _igienizeaza(intrari: list) -> list:
    """Re-aplică garda pe intrările existente, repară URL-urile duble și unifică dublurile."""
    valide = []
    for raw in intrari:
        if not isinstance(raw, dict):
            continue
        url = _curata_url(raw.get("url") or "")
        if url and guard.url_ostil(url) is not None:
            continue
        if not _text_eligibil(raw.get("titlu") or "", raw.get("fapt") or "", raw.get("ent") or []):
            continue
        copie = dict(raw)
        copie["url"] = url
        valide.append(copie)

    # Intrarea susținută de cele mai multe publicații devine canonică și absoarbe sub-clusterele.
    valide.sort(
        key=lambda e: (len(e.get("surse") or []), e.get("d") or "", len(e.get("ent") or [])),
        reverse=True,
    )
    canonice: list[dict] = []
    for cand in valide:
        existent = next((c for c in canonice if _acelasi_eveniment(c, cand)), None)
        if existent is None:
            canonice.append(cand)
            continue
        surse_unite = sorted(set(existent.get("surse") or []) | set(cand.get("surse") or []))
        existent["surse"] = surse_unite[:6]
        vazute_ent = {_canon(x) for x in (existent.get("ent") or [])}
        ent_unite = list(existent.get("ent") or [])
        for x in cand.get("ent") or []:
            cx = _canon(x)
            if cx and cx not in vazute_ent and len(ent_unite) < 4:
                ent_unite.append(x)
                vazute_ent.add(cx)
        existent["ent"] = ent_unite
        if (cand.get("d") or "") > (existent.get("d") or ""):
            existent["d"] = cand["d"]
    canonice.sort(key=lambda e: e.get("d") or "", reverse=True)
    return canonice


def eligibil(rep: dict) -> bool:
    d = rep.get("dialectic") if isinstance(rep, dict) else None
    if not isinstance(d, dict) or not d.get("milestone") or d.get("state") != "SYNTHESIS_VALID":
        return False
    fapt = (d.get("common") or [{}])[0]
    if not fapt.get("text") or fapt.get("hedged"):
        return False
    url = _curata_url(rep.get("original_link") or rep.get("url") or "")
    if url and guard.url_ostil(url) is not None:
        return False
    if not _text_eligibil(rep.get("title") or "", fapt.get("text") or "", rep.get("entities") or []):
        return False
    return len(rep.get("entities") or []) >= 1


def incarca(cale: str | None = None) -> list:
    try:
        with open(cale or CALE, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def actualizeaza(procesate: list, mod: dict | None, cale: str | None = None,
                 acum: datetime | None = None, corrections: dict | None = None) -> dict:
    """Adaugă deciziile noi, aplică garda și curăță registrul. Întoarce contoarele."""
    acum = acum or datetime.now(timezone.utc)
    reg = {e.get("story"): e for e in incarca(cale) if isinstance(e, dict) and e.get("story")}
    adaugate = 0
    for rep in procesate or []:
        if not eligibil(rep) or not rep.get("story_id"):
            continue
        d = rep["dialectic"]
        fapt = d["common"][0]
        if rep["story_id"] not in reg:
            adaugate += 1
        reg[rep["story_id"]] = {
            "story": rep["story_id"],
            # o sinteză veche care absoarbe azi decizia o datează AZI (`updated`), nu la prima
            # ei publicare, de acum câteva zile (Argon R5)
            "d": (rep.get("updated") or rep.get("published") or acum.isoformat())[:10],
            "url": _curata_url(rep.get("original_link") or rep.get("url") or ""),
            "titlu": rep.get("title") or "",
            "fapt": fapt["text"],
            "surse": list(fapt.get("src") or [])[:6],
            "ent": list(rep.get("entities") or [])[:4],
        }
    blocate_urls = set()
    blocate_stories = set()
    for cheie in ("corrections", "takedowns"):
        for u in ((mod or {}).get(cheie) or {}):
            blocate_urls.add(normalize_url(u))
            if isinstance(u, str) and not u.startswith("http://") and not u.startswith("https://"):
                blocate_stories.add(u)

    # E4 Garda Memoriei: catalogul public de corecții și retrageri (publication.py)
    if corrections is None:
        try:
            from . import publication
            corrections = publication.load()
        except Exception:
            corrections = {}

    for key, row in (corrections or {}).items():
        if isinstance(key, str):
            blocate_stories.add(key)
            if key.startswith("http://") or key.startswith("https://"):
                blocate_urls.add(normalize_url(key))
        if isinstance(row, dict):
            k = row.get("key")
            if isinstance(k, str):
                blocate_stories.add(k)
                if k.startswith("http://") or k.startswith("https://"):
                    blocate_urls.add(normalize_url(k))

    limita = (acum - timedelta(days=ZILE_PASTRARE)).date().isoformat()
    inainte = len(reg)
    pastrate = [e for e in reg.values()
                if e.get("story") not in blocate_stories
                and normalize_url(e.get("url") or "") not in blocate_urls
                and (e.get("d") or "") >= limita]
    pastrate.sort(key=lambda e: e.get("d") or "", reverse=True)
    pastrate = _igienizeaza(pastrate)[:MAX_INTRARI]
    try:
        os.makedirs(os.path.dirname(cale or CALE), exist_ok=True)
        tmp = (cale or CALE) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(pastrate, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, cale or CALE)
    except OSError as exc:
        print(f"   !! memoria subiectelor nescrisă ({exc}) — rularea continuă")
    return {"adaugate": adaugate, "scoase": inainte - len(pastrate), "total": len(pastrate)}


def din_memorie(articol: dict, registru: list, ttl_zile: int, n: int = 2) -> list:
    """Intrările mai vechi decât fereastra activă despre ACELAȘI subiect, cele mai recente întâi.

    Același subiect = cel puțin MIN_ENTITATI_COMUNE entități comune care NU sunt generice și
    cel puțin un cuvânt-cheie comun (≥6 litere, în afara numelor) între titlul+faptul de atunci și
    titlul+rezumatul de azi. Două știri despre aceiași doi politicieni, dar despre lucruri
    diferite, nu se leagă (Argon R5). Cele din fereastra activă sunt deja în „Articole conectate"."""
    ent = _specifice(articol.get("entities"))
    if len(ent) < MIN_ENTITATI_COMUNE or not registru:
        return []
    try:
        pub = datetime.fromisoformat(articol.get("published") or "")
    except (ValueError, TypeError):
        return []
    limita = (pub - timedelta(days=ttl_zile)).date().isoformat()
    proprie = articol.get("story_id")
    chei = _cuvinte_cheie(f"{articol.get('title') or ''} {articol.get('synthesis') or ''}", ent)
    out = []
    for e in registru:
        if e.get("story") == proprie or (e.get("d") or "") >= limita:
            continue
        comune = ent & _specifice(e.get("ent"))
        if len(comune) < MIN_ENTITATI_COMUNE:
            continue
        if not chei & _cuvinte_cheie(f"{e.get('titlu') or ''} {e.get('fapt') or ''}", comune):
            continue
        out.append(e)
        if len(out) >= n:
            break
    return out
