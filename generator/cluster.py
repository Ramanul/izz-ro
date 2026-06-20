"""Grupare a articolelor care descriu acelasi eveniment (candidat pentru model C)."""
from datetime import datetime, timezone, timedelta

from . import config
from .util import title_tokens

RECENT_HOURS = 24
JACCARD_MIN = 0.40        # similaritate minima titluri
SHARED_TOKENS_MIN = 3     # sau cel putin atatea cuvinte-cheie comune


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
    if not t1 or not t2:
        return False
    inter = len(t1 & t2)
    if inter >= SHARED_TOKENS_MIN:
        return True
    union = len(t1 | t2)
    return union > 0 and inter / union >= JACCARD_MIN


def cluster(articles: list) -> list:
    """Returneaza lista de clustere (fiecare = lista de articole). Greedy single-link."""
    recent = _recent(articles)
    tokens = [title_tokens(a.get("original_title", "")) for a in recent]
    n = len(recent)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if _similar(tokens[i], tokens[j]):
                parent[find(i)] = find(j)

    groups: dict = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(recent[i])
    return list(groups.values())


def is_synthesis_candidate(group: list) -> bool:
    """Cluster cu >= CLUSTER_MIN_SOURCES surse DISTINCTE -> sinteza C."""
    return len({a.get("source") for a in group}) >= config.CLUSTER_MIN_SOURCES
