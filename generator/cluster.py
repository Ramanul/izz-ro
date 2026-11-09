"""Grupare a articolelor care descriu acelasi eveniment (candidat pentru model C)."""
import hashlib
import re
from datetime import datetime, timezone, timedelta

from . import config
from .util import title_tokens, domain_of, strip_diacritics

RECENT_HOURS = 24
JACCARD_MIN = 0.30        # suprapunere minima (cu stemming) — necesara IMPREUNA cu pragul de tokeni
SHARED_TOKENS_MIN = 3     # cuvinte-cheie comune (dupa stemming) cerute SIMULTAN cu Jaccard
STEM_LEN = 6              # stemming RO crud: primele N litere (israelul/israelian -> israel)


def _stemset(title: str) -> set:
    """Tokeni semnificativi, redusi la radacina (prefix) ca sa prinda formele flexionate RO."""
    return {t[:STEM_LEN] for t in title_tokens(title)}


def _recent(articles: list) -> list:
    """Articolele din ultimele `RECENT_HOURS` ore. O data neparsabila EXCLUDE articolul.

    Varianta veche punea `datetime.now()` pe data stricata, adica trata vechimea
    necunoscuta drept „cea mai proaspata cu putinta" — cel mai putin conservator raspuns
    posibil. Consecinta: o stire de varsta necunoscuta ramanea vesnic eligibila sa fie
    lipita de stirile de azi prin `attach_recent`. Sect. 7 spune exact invers pentru un
    fallback care nu poate atinge bara: SARE itemul.

    Excluderea NU pierde articolul: ce nu intra in niciun grup e publicat ca `single`
    (`main.py:166`, `singles += [it for it in new_items if it["url"] not in clustered]`).
    Pierde doar sansa de a fi CLUSTERIZAT, ceea ce e si intentia — nu poti decide ca doua
    stiri sunt acelasi eveniment recent cand nu stii cand s-a intamplat una din ele.

    Masurat inainte de schimbare (`IZZ-0278`): din 13.916 articole din `data/articles.json`,
    **zero** au `published` lipsa sau neparsabil. Deci diferenta pe datele reale e nula in
    ambele directii — nici over-merge, nici under-merge — si schimbarea e o intarire a
    caii de fallback, nu o schimbare de comportament observabil (sect. 7).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_HOURS)
    out = []
    for a in articles:
        try:
            dt = datetime.fromisoformat(a.get("published", ""))
        except (ValueError, TypeError):
            continue
        dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        if dt >= cutoff:
            out.append(a)
    return out


def _similar(t1: set, t2: set) -> bool:
    """Acelasi eveniment doar daca impart SUFICIENTE cuvinte-cheie SI o proportie reala.
    Conditie AND (nu OR) -> evita lipirea a doua titluri lungi cu 3 cuvinte generice comune.
    """
    if not t1 or not t2:
        return False
    inter = len(t1 & t2)
    union = len(t1 | t2)
    return inter >= SHARED_TOKENS_MIN and union > 0 and inter / union >= JACCARD_MIN


def cluster(articles: list) -> list:
    """Grupeaza articolele despre acelasi eveniment (candidat pentru model C).

    LEADER clustering (nu single-link): un articol intra intr-un cluster doar daca seamana
    cu SAMANTA (primul membru), nu cu orice membru -> elimina 'chaining'-ul (A~B, B~C => A,B,C
    desi A si C n-au legatura). Tokeni cu stemming RO ca sa prinda formele flexionate.
    """
    recent = _recent(articles)
    clusters = []  # fiecare: {"sig": set_tokeni (uniunea membrilor), "members": [articole]}
    for a in recent:
        # fallback pe titlul AI: itemele deja procesate nu mai au original_title
        # (scrub-ul juridic il sterge), dar trebuie sa poata intra in clustere cross-run
        tk = _stemset(a.get("original_title") or a.get("title") or "")
        for c in clusters:
            if _similar(tk, c["sig"]):
                c["members"].append(a)
                c["sig"] |= tk          # semnatura creste; Jaccard-ul cere tot suprapunere reala
                break
        else:
            clusters.append({"sig": set(tk), "members": [a]})
    return [c["members"] for c in clusters]


def _strict_match(inter: int, union: int) -> bool:
    """Pragul de absorbtie cross-run, calibrat pe perechi reale:
    CFR/Ceara (duplicat real)    3 tokeni / jac 0.50 -> DA
    Messi vs Ronaldo (diferite)  3 tokeni / jac 0.43 -> NU
    Ormuz (duplicat real)        5 tokeni / jac 0.63 -> DA
    Titluri lungi acelasi eveniment pot avea jac mic dar multi tokeni comuni."""
    if not union:
        return False
    jac = inter / union
    return (inter >= 4 and jac >= 0.40) or (inter == 3 and jac >= 0.50)


def _entity_stems(a: dict) -> set:
    """Stemuri din entitatile AI ale unei stiri (garda anti-sablon)."""
    return {t[:STEM_LEN] for e in (a.get("entities") or []) for t in title_tokens(e)}


def attach_recent(groups: list, candidates: list) -> list:
    """Ataseaza stiri din rulari ANTERIOARE (deja procesate) la clusterele itemelor
    noi -- doua surse care relateaza acelasi eveniment la ~20-30 min distanta cad in
    rulari diferite si altfel raman stiri duplicate separate. Candidatii pot fi si
    sinteze C, nu doar stiri B (IZZ-0151): o sinteza publicata absoarbe stirea noua si
    se actualizeaza la acelasi permalink. Praguri STRICTE, plus
    garda pe entitati: cronici sportive-sablon ('X invinge Y si avanseaza in optimi')
    se potrivesc textual desi sunt meciuri diferite -- daca ambele parti au entitati
    AI si acestea sunt disjuncte, NU se unesc. (Itemele dinainte de extractia de
    entitati nu au garda -> regula simpla, tranzitoriu.)"""
    cands = [(c, _stemset(c.get("original_title") or c.get("title") or ""))
             for c in _recent(candidates)]
    used: set = set()
    out = []
    for g in groups:
        sig: set = set()
        ge: set = set()
        for a in g:
            sig |= _stemset(a.get("original_title") or a.get("title") or "")
            ge |= _entity_stems(a)
        members = list(g)
        for c, tk in cands:
            if c["url"] in used or not tk or not sig:
                continue
            if not _strict_match(len(tk & sig), len(tk | sig)):
                continue
            ce = _entity_stems(c)
            if ge and ce and not (ge & ce):
                continue  # potrivire textuala, dar entitati disjuncte -> evenimente diferite
            members.append(c)
            used.add(c["url"])
            sig |= tk
            ge |= ce
        out.append(members)
    return out


# ---- regruparea post-AI (8.11.2026) ------------------------------------------------------
# Gruparea de mai sus ruleaza INAINTE de AI si compara titlul ORIGINAL al itemului nou (uneori
# in engleza, alt unghi) cu titlul AI al celor publicate. Dupa rescriere titlurile converg, dar
# nu mai erau comparate: masurat pe 3 zile, „Spania si Olanda candideaza pentru sefia BCE"
# statea pe site ca 4 articole B separate. Regruparea compara articolele DEJA publicate intre
# ele, pe titlul AI, cu praguri mai stricte decat `_strict_match` (citite pe perechi reale:
# la jac 0,40-0,44 lipituri gresite frecvente; la >=0,6 niciuna la citire). Revizuit cu Argon.
REGRUPARE_MAX_PE_RULARE = 3
REGRUPARE_ESECURI_MAX = 2   # un articol prezent in 2 grupuri esuate nu mai intra in regrupare
_NUMAR = re.compile(r"\d+(?:[.,]\d+)?")
# „Guvernul a aprobat X" vs „Guvernul nu a aprobat X": Jaccard mare, aceleasi entitati, sens opus.
_NEGATIE_TITLU = re.compile(r"\b(nu|n-a|n-au|n-ar|nici|fara|respin\w*|resping\w*|amana\w*|amanat\w*|refuz\w*)\b")


def _polaritate(titlu: str) -> bool:
    return bool(_NEGATIE_TITLU.search(strip_diacritics(titlu).lower()))


def _entitati(a: dict) -> set:
    return {strip_diacritics(e).lower().strip() for e in (a.get("entities") or [])
            if isinstance(e, str) and e.strip()}


def _domenii(a: dict) -> set:
    """Publicatiile din spatele unui articol: la o sinteza C toate sursele ei, nu doar prima."""
    surse = [s.get("url") or "" for s in (a.get("sources") or [])] or [a.get("original_link") or ""]
    return {domain_of(u) for u in surse if u}


def _cifre_disjuncte(t1: str, t2: str) -> bool:
    """„15 perchezitii" vs „55 perchezitii", „etapa 5" vs „etapa 6": ambele titluri au cifre si
    niciuna comuna -> evenimente diferite, oricat ar semana restul (Argon)."""
    n1, n2 = set(_NUMAR.findall(t1)), set(_NUMAR.findall(t2))
    return bool(n1 and n2 and not (n1 & n2))


def _potrivire_regrupare(a: dict, b: dict) -> bool:
    ta, tb = _stemset(a.get("title") or ""), _stemset(b.get("title") or "")
    inter, union = len(ta & tb), len(ta | tb)
    if not union or _cifre_disjuncte(a.get("title") or "", b.get("title") or ""):
        return False
    if _polaritate(a.get("title") or "") != _polaritate(b.get("title") or ""):
        return False
    ea, eb = _entity_stems(a), _entity_stems(b)
    if not (ea and eb and ea & eb):
        return False                       # entitati AI comune obligatorii, fara exceptie
    comune = len(_entitati(a) & _entitati(b))
    # „Olanda" vs „Tarile de Jos" e acelasi stat: acolo raman >=2 entitati AI comune
    # (Spania, BCE). La Tezaur/FIDELIS singura comuna e „Ministerul Finantelor".
    if comune < 2 and _schimba_doar_numele(a.get("title") or "", b.get("title") or ""):
        return False
    jac = inter / union
    if jac >= 0.6 and inter >= 3:
        return True
    # zona gri: o singura entitate comuna nu ajunge (Fidelis/Tezaur, ambele „Ministerul Finantelor")
    if not (jac >= 0.5 and inter >= 4 and comune >= 2):
        return False
    # ...si nici cand o parte numeste un actor pe care cealalta nu-l are deloc: „Reghecampf isi
    # critica jucatorii" vs „Becali il critica pe Reghecampf" — aceeasi zi, alt vorbitor.
    for x, y in ((a, b), (b, a)):
        titlu = strip_diacritics(x.get("title") or "").lower()
        if any(e in titlu for e in _entitati(x) - _entitati(y)):
            return False
    return True


def _schimba_doar_numele(t1: str, t2: str) -> bool:
    """Titluri identice cu exceptia UNUI nume propriu de fiecare parte: „...titlurilor de stat
    Tezaur" vs „...titlurilor de stat FIDELIS" — sablonul e acelasi, produsul nu (proba pe 3 zile)."""
    s1, s2 = _stemset(t1), _stemset(t2)
    d1, d2 = s1 - s2, s2 - s1
    if len(d1) != 1 or len(d2) != 1:
        return False

    def _propriu(titlu: str, d: set) -> bool:
        cuvinte = re.findall(r"[^\W\d_]+", titlu)
        return any(w[:1].isupper() and _stemset(w) & d for w in cuvinte[1:])
    return _propriu(t1, d1) and _propriu(t2, d2)


def semnatura_grup(group: list) -> str:
    return hashlib.sha1("|".join(sorted(a.get("url") or "" for a in group)).encode()).hexdigest()[:12]


def regrupeaza_publicate(candidates: list) -> list:
    """Grupuri de articole DEJA publicate (B, si cel mult o sinteza C ca lider) despre acelasi
    eveniment, pe titlul AI. Fiecare grup: >=1 articol B, publicatii distincte in TOT grupul,
    potrivire stricta cu liderul si veto pe cifre fata de fiecare membru. Un grup care a esuat
    deja la sinteza (semnatura memorata pe membri, `regrupare_esuata`) nu se reia pana nu se
    schimba componenta lui. Sintezele C vin primele ca lideri: altfel doua B noi despre un
    eveniment deja sintetizat ar forma o a DOUA sinteza langa prima (Argon)."""
    pool = [a for a in _recent(candidates)
            if a.get("model") in ("B", "C") and not a.get("anunt_fara_corp") and a.get("title")
            and (a.get("regrupare_esecuri") or 0) < REGRUPARE_ESECURI_MAX]
    pool.sort(key=lambda a: (a.get("model") != "C", a.get("published") or ""))
    grupuri: list = []
    for a in pool:
        for g in grupuri:
            if a.get("model") == "C" and any(m.get("model") == "C" for m in g["m"]):
                continue
            if _domenii(a) & g["dom"] or not _potrivire_regrupare(g["m"][0], a):
                continue
            if any(_cifre_disjuncte(a["title"], m["title"]) for m in g["m"][1:]):
                continue
            g["m"].append(a)
            g["dom"] |= _domenii(a)
            break
        else:
            grupuri.append({"m": [a], "dom": set(_domenii(a))})
    out = []
    for g in grupuri:
        m = g["m"]
        if len(m) < 2 or not any(x.get("model") == "B" for x in m) or len(g["dom"]) < config.CLUSTER_MIN_SOURCES:
            continue
        sig = semnatura_grup(m)
        if any(x.get("regrupare_esuata") == sig for x in m):
            continue
        out.append(m)
    return out


def marcheaza_esec_regrupare(group: list) -> None:
    sig = semnatura_grup(group)
    for a in group:
        a["regrupare_esuata"] = sig
        # semnatura noua la fiecare sursa noua ar relua la nesfarsit un grup cu un articol
        # care strica sinteza (paywall, text corupt) — contorul per articol il scoate (Argon)
        a["regrupare_esecuri"] = (a.get("regrupare_esecuri") or 0) + 1


def is_synthesis_candidate(group: list) -> bool:
    """Cluster cu >= CLUSTER_MIN_SOURCES domenii DISTINCTE -> sinteza C.

    Domeniu, nu cheia din config: 2 feed-uri RSS ale aceluiasi site
    (ex. "digi24" si "extern"/Digi24 Extern) nu inseamna 2 surse independente.
    """
    return len({domain_of(a.get("original_link", "")) for a in group}) >= config.CLUSTER_MIN_SOURCES
