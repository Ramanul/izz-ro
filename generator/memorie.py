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

# Vocabular judiciar și de acuzație: un fapt care îl conține nu intră în memorie, indiferent
# cât de definitiv sună. Rădăcini fără diacritice, potrivite la început de cuvânt.
_JUDICIAR = re.compile(
    r"\b(?:suspect|anchet|acuz|inculpa|arest|retinu|retinere|cercetat|cercetare|urmarir|"
    r"perchezit|condamn|achita|dosar|procuror|parchet|diicot|dna\b|instant|judecat|tribunal|"
    r"pedeaps|penal|infractiun|fraud|delapid|mit[aei]\b|spag|violen|agresi|crim|omor|ucis|"
    r"viol|abuz|victim|dispar)",
)


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
            "d": (rep.get("published") or acum.isoformat())[:10],
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
    """Intrările mai vechi decât fereastra activă despre același subiect (≥2 entități comune),
    cele mai recente întâi. Cele din fereastra activă sunt deja în „Articole conectate"."""
    ent = {_norm(e) for e in (articol.get("entities") or []) if e}
    if len(ent) < MIN_ENTITATI_COMUNE or not registru:
        return []
    try:
        pub = datetime.fromisoformat(articol.get("published") or "")
    except (ValueError, TypeError):
        return []
    limita = (pub - timedelta(days=ttl_zile)).date().isoformat()
    proprie = articol.get("story_id")
    out = []
    for e in registru:
        if e.get("story") == proprie or (e.get("d") or "") >= limita:
            continue
        if len(ent & {_norm(x) for x in e.get("ent") or []}) >= MIN_ENTITATI_COMUNE:
            out.append(e)
        if len(out) >= n:
            break
    return out
