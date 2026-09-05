"""Reusable decision layer for IZZ Intelligence products.

The web prototype can use the same contracts as the future SSG/API adapters.
No network calls happen here: callers provide already-verified records.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LeadMatch:
    provider: dict[str, Any]
    score: int
    reasons: tuple[str, ...]


def _norm(value: str) -> str:
    return " ".join((value or "").strip().casefold().split())


def match_leads(
    providers: list[dict[str, Any]],
    *,
    need: str,
    city: str,
    budget: str,
    limit: int = 3,
) -> list[LeadMatch]:
    """Rank providers using deterministic, explainable matching.

    Score contract: category 45, locality 30, budget 15, baseline 10.
    Unknown/empty fields never receive points, and every returned match includes reasons.
    """
    if limit <= 0:
        return []
    need_n = _norm(need)
    city_n = _norm(city)
    budget_n = _norm(budget)
    matches: list[LeadMatch] = []
    for provider in providers:
        reasons: list[str] = []
        categories = [_norm(x) for x in provider.get("categories", [])]
        cities = [_norm(x) for x in provider.get("cities", [provider.get("city", "")])]
        budgets = [_norm(x) for x in provider.get("budgets", [])]
        score = 10
        category_hit = bool(need_n and any(need_n in x or x in need_n for x in categories))
        city_hit = bool(city_n and city_n in cities)
        budget_hit = bool(budget_n and budget_n in budgets)
        if category_hit:
            score += 45
            reasons.append("categorie")
        if city_hit:
            score += 30
            reasons.append("localitate")
        if budget_hit:
            score += 15
            reasons.append("buget")
        matches.append(LeadMatch(provider=provider, score=min(100, score), reasons=tuple(reasons)))
    matches.sort(key=lambda item: (-item.score, _norm(item.provider.get("name", ""))))
    return matches[:limit]


def get_company_monitor(companies: dict[str, dict[str, Any]], cui: str) -> dict[str, Any] | None:
    """Return a normalized company record by CUI, stripping whitespace."""
    key = "".join((cui or "").split()).upper()
    company = companies.get(key)
    if not company:
        return None
    changes = sorted(company.get("changes", []), key=lambda item: str(item.get("date", "")), reverse=True)
    return {**company, "changes": changes}


def suggest_actions(text: str) -> list[str]:
    """Map a piece of information to useful next actions without an AI dependency."""
    value = _norm(text)
    actions: list[str] = []
    rules = (
        (("salari", "tax", "impozit", "venit"), "Calculează impactul pentru profilul tău"),
        (("lege", "ordonan", "reglement", "guvern", "minister"), "Verifică textul oficial și termenul de aplicare"),
        (("achizi", "contract", "licit", "proiect"), "Caută oportunități și contracte similare"),
        (("preț", "energie", "credit", "asigur", "rca", "locuin"), "Compară ofertele și costul total"),
    )
    for needles, action in rules:
        if any(needle in value for needle in needles):
            actions.append(action)
    return actions or ["Salvează subiectul și activează o alertă de schimbare"]


def validate_dataset(data: dict[str, Any], minimum_catalog: int = 37) -> list[str]:
    """Return human-readable contract violations; empty list means valid."""
    errors: list[str] = []
    required = ("catalog", "providers", "companies", "market", "commerce", "events")
    missing = [key for key in required if key not in data]
    if missing:
        errors.append(f"missing sections: {', '.join(missing)}")
    catalog = data.get("catalog", [])
    if not isinstance(catalog, list) or len(catalog) < minimum_catalog:
        errors.append(f"catalog must contain >= {minimum_catalog} products")
    else:
        names = [str(item.get("name", "")).strip() for item in catalog if isinstance(item, dict)]
        if any(not name for name in names):
            errors.append("catalog contains an empty name")
        if len(names) != len(set(names)):
            errors.append("catalog contains duplicate names")
    for index, provider in enumerate(data.get("providers", [])):
        for key in ("name", "city", "categories", "budgets", "contact"):
            if not provider.get(key):
                errors.append(f"provider[{index}] missing {key}")
    for cui, company in data.get("companies", {}).items():
        if not company.get("name"):
            errors.append(f"company[{cui}] missing name")
        for index, change in enumerate(company.get("changes", [])):
            confidence = change.get("confidence")
            try:
                valid_confidence = 0 <= int(confidence) <= 100
            except (TypeError, ValueError):
                valid_confidence = False
            if not valid_confidence:
                errors.append(f"company[{cui}].changes[{index}] invalid confidence")
            for key in ("date", "type", "text"):
                if not change.get(key):
                    errors.append(f"company[{cui}].changes[{index}] missing {key}")
    return errors
