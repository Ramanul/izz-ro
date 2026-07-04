"""Grupare a articolelor care descriu acelasi eveniment (candidat pentru model C)."""
from datetime import datetime, timezone, timedelta

from . import config
from .util import title_tokens, domain_of

RECENT_HOURS = 24
JACCARD_MIN = 0.30        # suprapunere minima (cu stemming) — necesara IMPREUNA cu pragul de tokeni
SHARED_TOKENS_MIN = 3     # cuvinte-cheie comune (dupa stemming) cerute SIMULTAN cu Jaccard
STEM_LEN = 6              # stemming RO crud: primele N litere (israelul/israelian -> israel)


def _stemset(title: str) -> set:
    """Tokeni semnificativi, redusi la radacina (prefix) ca sa prinda formele flexionate RO."""
    return {t[:STEM_LEN] for t in title_tokens(title)}


def _recent(articles: list) -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_HOURS)
    out = []
    for a in articles:
        try:
            dt = datetime.fromisoformat(a.get("published", ""))
            dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            dt = datetime.now(timezone.utc)
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
    rulari diferite si altfel raman stiri duplicate separate. Praguri STRICTE, plus
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


def is_synthesis_candidate(group: list) -> bool:
    """Cluster cu >= CLUSTER_MIN_SOURCES domenii DISTINCTE -> sinteza C.

    Domeniu, nu cheia din config: 2 feed-uri RSS ale aceluiasi site
    (ex. "digi24" si "extern"/Digi24 Extern) nu inseamna 2 surse independente.
    """
    return len({domain_of(a.get("original_link", "")) for a in group}) >= config.CLUSTER_MIN_SOURCES
