"""E2 — sinteza dialectică: ce confirmă publicațiile împreună, unde diferă, ce vine dintr-o
singură origine. Planul «izz.ro prin prisma cărților» (`specs/plan-paradigma-izz.md` §3 E2, §5).

Diviziunea muncii, deliberată:
- MODELUL citește propozițiile numerotate ale surselor și propune structura (fapte comune,
  divergențe, afirmații dintr-o singură sursă), fiecare afirmație cu propozițiile care o susțin;
- PYTHON decide ce rămâne: verifică fiecare citare (propoziția există și e a ACESTUI eveniment),
  fiecare cifră (e în propozițiile citate), fiecare „fapt comun" (vine din cel puțin două
  ORIGINI — clonele și preluările declarate nu sunt origini noi), copierea (secvențe verbatim),
  rezerva („ar fi" la sursă rămâne rezervă). Starea finală — sinteză validă, o singură origine
  sau Tăcere Asumată — o stabilesc pragurile de aici, nu declarația modelului.

O regulă care trăiește doar în prompt e o speranță; una verificată aici e un fapt al sistemului
(aceeași disciplină ca `verifica_sinteza.py`). Nimic din textul surselor nu se persistă: în stare
intră doar parafrazele modelului care au trecut verificările și NUMELE publicațiilor.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from . import fetch_deep
from .util import domain_of, truncate_words
from .verifica_sinteza import (
    _cea_mai_lunga_comuna, _cuvinte, _norm, PRAG_PROPOZITIE_COPIATA, cifre_straine,
    citate_inventate,
)

DIALECTIC_VERSION = "e2-v1"

# Plafonul de context per cluster, în caractere, pe propoziții ÎNTREGI. Lotul are 3 clustere,
# deci ~18.000 de caractere de context per apel — sub plafoanele free-tier de tokeni/minut.
CONTEXT_CHARS = int(os.environ.get("DIALECTIC_CONTEXT_CHARS", "6000"))
# Peste această fracție de afirmații respinse (citare inexistentă/străină, cifră absentă din
# propozițiile citate), clusterul intră în Tăcere Asumată. Calibrabil, nu ghicit definitiv
# (Argon R3): se urmărește în raportul rulării (`stats()`).
SILENCE_REJECTION_THRESHOLD = float(os.environ.get("SILENCE_REJECTION_THRESHOLD", "0.34"))
# Copierea: gate-ul de release blochează ≥15 cuvinte verbatim; aici se oprește afirmația cu
# o marjă de două cuvinte, ca un fapt copiat să cadă singur, nu să amâne tot clusterul.
COPY_RUN_MAX = PRAG_PROPOZITIE_COPIATA - 2
MAX_FACTS = 5
MAX_DIVERGENCES = 3
MAX_SINGLE = 4

STATE_VALID = "SYNTHESIS_VALID"
STATE_SINGLE = "SINGLE_ORIGIN"
STATE_SILENCE = "ASSUMED_SILENCE"

# Roluri care nu aduc o origine nouă: aceeași informație, altă adresă.
NON_ORIGIN_ROLES = fetch_deep.NON_CONFIRMING_ROLES

# Incertitudinea epistemică la sursă (listă îngustă, deliberat): dacă propozițiile citate o au
# și afirmația nu are nici rezervă, nici atribuire, faptul e marcat „cu rezervă la sursă" și nu
# intră în textul scurt de pe card. Verbele de declarație NU sunt incertitudine — „a declarat că"
# e o atribuire corectă, nu o rezervă pierdută.
_INCERTITUDINE = (
    "ar fi", "ar putea", "presupus", "presupusa", "acuzat", "acuzata", "suspectat",
    "suspectata", "banuit", "banuita", "potrivit unor surse", "surse neoficiale",
    "neconfirmat", "neconfirmata", "posibil", "pretins", "pretinsa",
    # estimarea nu e constatare (P8: separarea faptului de estimare)
    "estimeaza", "estimat", "estimata", "estimate", "estimari", "estimarile", "estimarilor",
)
_ATRIBUIRE = _INCERTITUDINE + (
    "potrivit", "conform", "a declarat", "au declarat", "a spus", "au spus", "a afirmat",
    "au afirmat", "sustine", "sustin", "a anuntat", "au anuntat", "a precizat", "au precizat",
    "a transmis", "au transmis", "a relatat", "relateaza", "a scris", "scrie", "afirma",
    "declara", "anunta", "spune", "spun", "a sustinut", "au sustinut", "a acuzat", "acuza",
)

_STATISTICI: dict = {}


def stats() -> dict:
    return dict(_STATISTICI)


def reset_stats() -> None:
    _STATISTICI.clear()


def _numara(cheie: str, n: int = 1) -> None:
    _STATISTICI[cheie] = _STATISTICI.get(cheie, 0) + n


# ---------------------------------------------------------------------------
# 1. CONTEXTUL: propozițiile numerotate, per cluster
# ---------------------------------------------------------------------------

@dataclass
class Source:
    idx: int
    name: str
    domain: str
    role: str
    mode: str


@dataclass
class Block:
    cid: int
    text: str
    chunks: dict = field(default_factory=dict)      # "C0S1.2" -> (frozenset(nume surse), text)
    sources: list = field(default_factory=list)     # [Source]

    def origin_names(self) -> set:
        """Numele publicațiilor care sunt ORIGINI (nu clone, nu preluări declarate)."""
        return {s.name for s in self.sources if s.role not in NON_ORIGIN_ROLES}


_ROLE_ORDER = {"ROOT": 0, "INDEPENDENT_CONTRIBUTOR": 1, "ECHO": 2, "CLONE": 3, "DERIVED": 4}
_ROLE_LABEL = {
    "ROOT": "prima relatare",
    "INDEPENDENT_CONTRIBUTOR": "aduce detalii suplimentare",
    "ECHO": "relatează aceleași fapte",
    "CLONE": "text comun cu altă publicație (posibil comunicat)",
    "DERIVED": "preia explicit de la altă publicație",
}


def _sentences_of(it: dict) -> list[str]:
    """Propozițiile unui membru, în ordine. Textul integral (E0) dacă există; altfel lead-ul
    RSS. Pentru o sinteză deja publicată fără text integral NU se folosește propria noastră
    sinteză ca „text al sursei" (ar fi atribuit publicației cuvintele noastre): se folosește
    titlul ei original, păstrat în `members`."""
    sents = it.get("_deep_sentences") or {}
    if sents:
        def _k(key: str) -> int:
            m = re.search(r"\.(\d+)$", key)
            return int(m.group(1)) if m else 0
        return [sents[k] for k in sorted(sents, key=_k) if sents[k]]
    if it.get("processed_by") and it.get("model") == "C":
        own = it.get("original_link") or it.get("url") or ""
        for m in it.get("members") or []:
            if isinstance(m, dict) and m.get("url") == own and m.get("title"):
                return [m["title"]]
        return []
    txt = " ".join(filter(None, (
        it.get("original_title") or it.get("title"),
        it.get("description") or it.get("teaser"),
    )))
    return list(fetch_deep.split_romanian_sentences(txt, source_id="S0").values())


def build_block(cid: int, group: list, roles_by_url: dict | None = None,
                char_budget: int = CONTEXT_CHARS, src_offset: int = 0) -> Block:
    """Blocul promptului pentru un cluster: o linie de antet per publicație și propozițiile ei,
    `[S{j}.{k}]`. Numerotarea surselor e UNICĂ în tot lotul (`src_offset`): modelul copiază
    doar etichete pe care le vede, iar o etichetă aparține unui singur eveniment — deci o
    citare din alt eveniment al lotului e prinsă mecanic (măsurat 23.10: cu prefixe de
    cluster pe care modelul trebuia să le compună, 10 din 33 de citări ale unui lot au ieșit
    greșite, iar un meci pe care toate sursele îl relatau identic a fost declarat „ireconciliabil").

    Propozițiile se iau ROUND-ROBIN între surse, întregi, până la plafon: o sursă lungă nu le
    lasă pe celelalte fără nicio propoziție. Prima propoziție a fiecărei surse intră mereu.
    Faptele din versiunea anterioară a sintezei (la actualizare) intră ca `[P{cid}.{k}]`, cu
    publicațiile lor — altfel o actualizare ar pierde tăcut faptele surselor absorbite în
    rulările trecute."""
    roles_by_url = roles_by_url or {}
    by_name: dict[str, dict] = {}
    for it in group:
        name = it.get("source_name") or it.get("source") or domain_of(it.get("url") or "") or "?"
        url = it.get("url") or it.get("original_link") or ""
        role = it.get("_epistemic_role") or roles_by_url.get(url) or "ECHO"
        sents = _sentences_of(it)
        prev = by_name.get(name)
        if prev is None or _ROLE_ORDER.get(role, 9) < _ROLE_ORDER.get(prev["role"], 9):
            by_name[name] = {"it": it, "role": role, "sents": sents or (prev or {}).get("sents", []),
                             "mode": it.get("_deep_mode") or "RSS_FALLBACK"}
    ordered = sorted(by_name.items(), key=lambda kv: (_ROLE_ORDER.get(kv[1]["role"], 9),
                                                       kv[1]["it"].get("published") or ""))
    block = Block(cid=cid, text="")
    picked: dict[int, list] = {}
    for j, (name, info) in enumerate(ordered, start=src_offset + 1):
        it = info["it"]
        block.sources.append(Source(j, name, domain_of(it.get("original_link") or it.get("url") or ""),
                                    info["role"], info["mode"]))
        picked[j] = []
    used = 0
    rnd = 0
    while True:
        progressed = False
        for j, (_, info) in enumerate(ordered, start=src_offset + 1):
            sents = info["sents"]
            if rnd >= len(sents):
                continue
            s = sents[rnd]
            if rnd > 0 and used + len(s) > char_budget:
                continue
            picked[j].append(s)
            used += len(s)
            progressed = True
        rnd += 1
        if not progressed:
            break

    lines = []
    for src in block.sources:
        it = ordered[src.idx - src_offset - 1][1]["it"]
        ora = (it.get("published") or "")[11:16]
        lines.append(f"[S{src.idx}] {src.name} · ora {ora or '?'} · {_ROLE_LABEL.get(src.role, src.role)}")
        for k, s in enumerate(picked[src.idx], start=1):
            chunk_id = f"S{src.idx}.{k}"
            block.chunks[chunk_id] = (frozenset({src.name}), s)
            lines.append(f"  [{chunk_id}] {s}")

    prev = None
    for it in group:
        if it.get("processed_by") and isinstance(it.get("dialectic"), dict):
            prev = it["dialectic"]
            break
    if prev:
        prev_facts = list(prev.get("common") or []) + list(prev.get("single") or [])
        if prev_facts:
            lines.append(f"[P{cid}] fapte din versiunea anterioară a acestei sinteze, deja atribuite")
            for k, f in enumerate(prev_facts[:MAX_FACTS + MAX_SINGLE], start=1):
                names = frozenset(n for n in (f.get("src") or []) if n)
                if not names or not f.get("text"):
                    continue
                chunk_id = f"P{cid}.{k}"
                block.chunks[chunk_id] = (names, f["text"])
                lines.append(f"  [{chunk_id}] ({', '.join(sorted(names))}) {f['text']}")
                # publicațiile din versiunea anterioară rămân origini dacă nu sunt clone/preluări
                for n in names:
                    if n not in {s.name for s in block.sources}:
                        role = "ECHO"
                        block.sources.append(Source(-1, n, "", role, "PREV"))
    block.text = "\n".join(lines)
    return block


# ---------------------------------------------------------------------------
# 2. VALIDAREA: ce propune modelul vs. ce rămâne
# ---------------------------------------------------------------------------

# Eticheta exactă din prompt; un prefix „C<n>" pus de model din obișnuință se ignoră — eticheta
# însăși e unică în lot, deci apartenența la eveniment o decide dicționarul blocului, nu prefixul.
_CHUNK_RE = re.compile(r"^\[?(?:C\d+)?((?:S\d+|P\d+)\.\d+)\]?$")


def _resolve_ids(raw_ids, block: Block) -> tuple[list[str], bool]:
    """(chunk-urile valide ale acestui cluster, a existat o citare invalidă/străină)."""
    ok, bad = [], False
    for raw in raw_ids if isinstance(raw_ids, list) else []:
        m = _CHUNK_RE.match(str(raw).strip())
        if not m:
            bad = True
            continue
        key = m.group(1)
        if key in block.chunks:
            if key not in ok:
                ok.append(key)
        else:
            bad = True                       # inexistentă sau a altui eveniment din lot
    return ok, bad


def _cited(ids: list[str], block: Block) -> tuple[set, str]:
    names: set = set()
    texts = []
    for i in ids:
        n, t = block.chunks[i]
        names |= set(n)
        texts.append(t)
    return names, " ".join(texts)


def _clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _fails_grounding(statement: str, cited_text: str, all_text: str) -> str | None:
    """Motivul respingerii afirmației, sau None. Cifrele se verifică față de propozițiile
    CITATE (nu de tot clusterul): o cifră reală dintr-o altă propoziție, lipită de faptul
    greșit, e exact asocierea falsă pe care pagina metodei o numea limită."""
    if cifre_straine(statement, cited_text):
        return "cifra"
    if citate_inventate(statement, all_text):
        return "citat"
    lungime, _ = _cea_mai_lunga_comuna(_cuvinte(statement), _cuvinte(all_text))
    if lungime > COPY_RUN_MAX:
        return "copiat"
    return None


def _has_any(text: str, markers) -> bool:
    t = _norm(text)
    return any(re.search(r"\b" + re.escape(m) + r"\b", t) for m in markers)


def validate(obj: dict, block: Block) -> dict | None:
    """Transformă propunerea modelului pentru UN cluster în structura publicabilă, sau None
    când nu rămâne nimic publicabil (clusterul se amână, ca la eșecul AI).

    Rata de respingere numără DOAR erorile de grounding (citare inexistentă sau din alt
    cluster, cifră absentă din propozițiile citate, citat inventat, copiere). Un „fapt comun"
    susținut de o singură origine nu e o eroare — e retrogradat la „o singură origine"."""
    if not isinstance(obj, dict):
        return None
    all_text = " ".join(t for _, t in block.chunks.values())
    origins = block.origin_names()
    total = rejected = 0
    common, single, diverg = [], [], []

    def _fact(raw, kind):
        nonlocal total, rejected
        if not isinstance(raw, dict):
            return
        text = _clean(raw.get("statement"))
        if not text:
            return
        total += 1
        ids, bad = _resolve_ids(raw.get("chunk_ids"), block)
        if bad or not ids:
            rejected += 1
            _numara("respinse_citare")
            return
        names, cited_text = _cited(ids, block)
        motiv = _fails_grounding(text, cited_text, all_text)
        if motiv:
            rejected += 1
            _numara(f"respinse_{motiv}")
            return
        hedged_src = _has_any(cited_text, _INCERTITUDINE)
        hedged_out = _has_any(text, _ATRIBUIRE)
        fact = {"text": text, "src": sorted(names),
                "hedged": bool(raw.get("has_hedging")) or hedged_src,
                # rezerva există la sursă, dar afirmația n-o mai poartă: se arată pe pagină cu
                # eticheta de rezervă, dar NU intră în textul scurt (card, RSS, meta)
                "forced": hedged_src and not hedged_out}
        # Clasificarea o dă CITAREA, nu eticheta modelului: susținut de ≥2 origini = comun
        # (și când modelul l-a pus la „o singură sursă"); de una singură = o singură origine
        # (și când modelul l-a numit „comun" — aici e retrogradat, nu respins).
        if len(names & origins) >= 2:
            common.append(fact)
        else:
            if kind == "common":
                _numara("retrogradate_o_origine")
            single.append(fact)

    for raw in (obj.get("common_facts") or [])[:MAX_FACTS * 2]:
        _fact(raw, "common")
    for raw in (obj.get("uncorroborated_claims") or [])[:MAX_SINGLE * 2]:
        _fact(raw, "single")

    for raw in (obj.get("divergences") or [])[:MAX_DIVERGENCES * 2]:
        if not isinstance(raw, dict):
            continue
        axis = _clean(raw.get("axis"))
        positions = []
        seen_names: set = set()
        for p in raw.get("positions") or []:
            if not isinstance(p, dict):
                continue
            claim = _clean(p.get("claim"))
            if not claim:
                continue
            total += 1
            ids, bad = _resolve_ids(p.get("chunk_ids") or p.get("source_chunk_ids"), block)
            if bad or not ids:
                rejected += 1
                _numara("respinse_citare")
                continue
            names, cited_text = _cited(ids, block)
            motiv = _fails_grounding(claim, cited_text, all_text)
            if motiv:
                rejected += 1
                _numara(f"respinse_{motiv}")
                continue
            positions.append({"text": claim, "src": sorted(names)})
            seen_names |= names
        # o divergență cere cel puțin două poziții, din publicații diferite
        if axis and len(positions) >= 2 and len(seen_names) >= 2:
            diverg.append({"axis": axis, "pos": positions})

    # „Faptele" care repetă un fapt deja comun (același text normalizat) nu se dublează
    seen = {_norm(f["text"]) for f in common}
    single = [f for f in single if _norm(f["text"]) not in seen][:MAX_SINGLE]
    common = common[:MAX_FACTS]
    diverg = diverg[:MAX_DIVERGENCES]

    ratio = (rejected / total) if total else 1.0
    if ratio > SILENCE_REJECTION_THRESHOLD:
        # Peste prag, problema e a MODELULUI (citări greșite, cifre fără temei), nu a surselor:
        # a publica „datele sunt ireconciliabile" ar fi o afirmație falsă despre presă. Nu se
        # publică nimic din răspunsul ăsta — clusterul se reia la rularea următoare.
        _numara("amanate_peste_prag")
        return None
    # Starea o decide conținutul VALIDAT, nu declarația modelului: Tăcerea Asumată se spune
    # doar când există poziții divergente, atribuite și verificate, și niciun fapt comun.
    if common:
        state = STATE_VALID
    elif diverg:
        state = STATE_SILENCE
    elif single:
        state = STATE_SINGLE
    else:
        return None
    if state != STATE_SILENCE and not any(not f["forced"] for f in (common if state == STATE_VALID else single)):
        # nu există niciun fapt care să poată sta, fără rezervă pierdută, în textul scurt
        _numara("amanate_doar_rezerva")
        return None

    _numara(f"stare_{state}")
    return {
        "v": DIALECTIC_VERSION,
        "state": state,
        "common": common,
        "diverg": diverg,
        "single": single,
        "rejected": rejected,
        "total": total,
        "milestone": bool(obj.get("is_milestone")) and state == STATE_VALID
                     and not any(f["hedged"] for f in common),
    }


def derive_synthesis(d: dict, title: str, max_words: int) -> str:
    """Textul scurt (card, RSS, meta, JSON-LD) DERIVAT din faptele validate — nu un text liber
    al modelului. Faptele cu rezervă pierdută nu intră. La Tăcere: formulare neutră, cu
    subiectul, ca două tăceri din aceeași zi să nu aibă meta-descrieri identice."""
    if d["state"] == STATE_SILENCE:
        subiect = (title or "").rstrip(" .")
        return (f"{subiect}: datele din surse sunt în acest moment ireconciliabile. "
                "Versiunea fiecărei publicații este redată separat, atribuită.")
    facts = d["common"] if d["state"] == STATE_VALID else d["single"]
    parts = []
    for f in facts:
        if f["forced"]:
            continue
        t = f["text"].rstrip()
        parts.append(t if t.endswith((".", "!", "?")) else t + ".")
        if len(" ".join(parts).split()) >= max_words:
            break
    return truncate_words(" ".join(parts), max_words)


def all_text_of(d: dict) -> str:
    """Tot textul publicat al structurii (pentru gate-ul de copiere/cifre/citate)."""
    return " ".join(flat_texts(d))


FLAT_SEP = " ¶ "


def flat_texts(d: dict) -> list[str]:
    """Textele structurii, într-o ordine fixă — pentru corectura de diacritice, care trebuie
    să atingă fiecare fapt de pe pagină, nu doar rezumatul derivat din ele."""
    out = [f["text"] for f in d.get("common", [])] + [f["text"] for f in d.get("single", [])]
    for dv in d.get("diverg", []):
        out.append(dv["axis"])
        out.extend(p["text"] for p in dv["pos"])
    return out


def assign_flat(d: dict, texts: list[str]) -> bool:
    """Inversa lui `flat_texts`. False (și nimic schimbat) dacă numărul nu se potrivește —
    o corectură care a pierdut sau a lipit un separator nu se aplică pe jumătate."""
    texts = [_clean(t) for t in texts]
    if len(texts) != len(flat_texts(d)) or not all(texts):
        return False
    it = iter(texts)
    for f in d.get("common", []):
        f["text"] = next(it)
    for f in d.get("single", []):
        f["text"] = next(it)
    for dv in d.get("diverg", []):
        dv["axis"] = next(it)
        for p in dv["pos"]:
            p["text"] = next(it)
    return True


def source_roles(block: Block) -> dict:
    """{nume publicație: rol} pentru Radiografia surselor (fără sursele din versiunea
    anterioară, care își păstrează rolul de atunci în `epistemic_roles`)."""
    return {s.name: s.role for s in block.sources if s.mode != "PREV"}


def build_blocks(groups_roles: list) -> list:
    """Blocurile unui lot, cu numerotarea surselor continuă între evenimente."""
    blocks, offset = [], 0
    for cid, (group, roles) in enumerate(groups_roles):
        b = build_block(cid, group, roles, src_offset=offset)
        offset += sum(1 for s in b.sources if s.mode != "PREV")
        blocks.append(b)
    return blocks
