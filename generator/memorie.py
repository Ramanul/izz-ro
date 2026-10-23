"""E4 — memoria subiectelor: un registru mic, separat de fereastra de 12 zile, cu DECIZIILE
ÎNCHEIATE pe care sursele le-au confirmat (`specs/plan-paradigma-izz.md` §3 E4).

De ce există: fereastra TTL face site-ul finit (P10), dar o lege promulgată acum patru luni
e context legitim pentru știrea de azi despre aceeași lege. Registrul ține un rând per subiect:
data, titlul nostru, faptul central confirmat, publicațiile, entitățile — nimic din textul
surselor. Plafon: 12 luni, câteva sute de KB pe an.

Garda Memoriei (Argon R3 — „singura eroare fatală rămasă", reparată aici, mecanic):
- intră DOAR ce sinteza dialectică a marcat `milestone` (decizie finală / eveniment încheiat),
  în stare validă, fără nicio rezervă la sursă;
- NU intră nicio stare judiciară sau acuzație, oricât de „încheiată" ar părea formularea —
  registrul ar îngheța o persoană într-o stare trecută: un cazier automat fără drept de apel;
- o corecție sau o retragere (`moderation.yaml`) scoate rândul și din registru, nu doar din
  fereastra activă.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone

from . import config
from .util import normalize_url
from .verifica_sinteza import _norm

CALE = os.path.join(config.ROOT, "data", "memory_ledger.json")
ZILE_PASTRARE = 365
MIN_ENTITATI_COMUNE = 2
MAX_INTRARI = 3000

# Vocabular penal, contravențional și de integritate: un fapt care îl conține nu intră în
# memorie, oricât de definitiv ar suna — agregarea automată a unor astfel de stări pe știri noi,
# luni mai târziu, ar fi un cazier fără drept de apel (Argon R3; R5: „condamnat definitiv" e
# exclus și el — GDPR art. 10, reabilitare). Deciziile CCR rămân: sunt constituționalitate, nu
# zonă penală. Rădăcini fără diacritice, potrivite la început de cuvânt.
_JUDICIAR = re.compile(
    r"\b(?:suspect|banuit|anchet|acuz|inculpa|imputat|arest|retinu|retinere|audiat|cercetat|"
    r"cercetare|urmarir|perchezit|flagrant|plangere|denunt|prejudici|condamn|achita|dosar|"
    r"procuror|parchet|diicot|dna\b|eppo\b|ani\b|instant|judecat|tribunal|pedeaps|penal|"
    r"infractiun|fraud|delapid|mit[aei]\b|spag|coruptie|trafic de influenta|conflict\w* de interes|"
    r"incompatibil|plagiat|amend|sanctionat|violen|agresi|crim|omor|ucis|viol|abuz|victim|dispar)",
)

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


def eligibil(rep: dict) -> bool:
    d = rep.get("dialectic") if isinstance(rep, dict) else None
    if not isinstance(d, dict) or not d.get("milestone") or d.get("state") != "SYNTHESIS_VALID":
        return False
    fapt = (d.get("common") or [{}])[0]
    if not fapt.get("text") or fapt.get("hedged"):
        return False
    text = _norm(f"{rep.get('title') or ''} {fapt.get('text') or ''}")
    if _JUDICIAR.search(text):
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
                 acum: datetime | None = None) -> dict:
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
            "url": rep.get("original_link") or rep.get("url") or "",
            "titlu": rep.get("title") or "",
            "fapt": fapt["text"],
            "surse": list(fapt.get("src") or [])[:6],
            "ent": list(rep.get("entities") or [])[:4],
        }
    blocate = set()
    for cheie in ("corrections", "takedowns"):
        for u in ((mod or {}).get(cheie) or {}):
            blocate.add(normalize_url(u))
    limita = (acum - timedelta(days=ZILE_PASTRARE)).date().isoformat()
    inainte = len(reg)
    pastrate = [e for e in reg.values()
                if normalize_url(e.get("url") or "") not in blocate and (e.get("d") or "") >= limita]
    pastrate.sort(key=lambda e: e.get("d") or "", reverse=True)
    pastrate = pastrate[:MAX_INTRARI]
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
