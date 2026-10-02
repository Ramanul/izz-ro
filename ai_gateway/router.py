"""Routerul de politică: ce provider/model poate primi cererea și cine e planul B.

Deciziile sunt pure (fără rețea): registry + guard + estimare → plan cu trace.
Ordinea NU e hardcodată (spec secțiunile 8, 10, 16): fiecare model poartă în
registry.yaml calități per clasă de task, prioritate și context; scorul combină
calitatea pe clasa cerută, prioritatea declarată și cota rămasă. GLOBAL_FREE_ONLY
și starea ToS decid CE intră deloc în cursă; guard-ul decide dacă ARE cotă.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ai_gateway.estimate import RequestEstimate
from ai_gateway.quota_guard import FreeQuotaGuard
from ai_gateway.registry import (
    Model,
    Provider,
    Registry,
    TOS_CAUTION,
    TOS_NOT_ALLOWED,
    TOS_UNVERIFIED,
)

NO_FREE_PROVIDER = "NO_FREE_PROVIDER_AVAILABLE"


@dataclass
class Trace:
    entries: list[dict] = field(default_factory=list)

    def add(self, target: str, verdict: str, reason: str = "") -> None:
        self.entries.append({"target": target, "verdict": verdict, "reason": reason})

    def as_lines(self) -> list[str]:
        return [f"{e['verdict']:>8}  {e['target']}" + (f"  ({e['reason']})" if e["reason"] else "")
                for e in self.entries]


@dataclass
class RoutingPlan:
    target: str  # „provider/model" pentru upstream, „" = passthrough
    task_class: str
    provider: str = ""
    quota_group: str = ""
    trace: Trace = field(default_factory=Trace)
    passthrough: bool = False  # model necunoscut permis explicit (în afara free-only)
    no_free_provider: bool = False

    @property
    def decision_header(self) -> str:
        head = f"task={self.task_class};target={self.target or 'passthrough'}"
        if self.no_free_provider:
            head += f";{NO_FREE_PROVIDER}"
        return head


def usable_provider(provider: Provider, settings) -> str | None:
    """Filtrul ToS + free-only (spec secțiunile 11, 30). None = folosibil, altfel motivul."""
    if provider.tos_status == TOS_NOT_ALLOWED:
        return "TOS_NOT_ALLOWED"
    if provider.tos_status == TOS_UNVERIFIED:
        return "TOS_UNVERIFIED"
    if provider.tos_status == TOS_CAUTION and not settings.allow_caution:
        return "CAUTION_OPT_IN_REQUIRED"
    if not provider.enabled:
        return "DISABLED_IN_REGISTRY"
    if settings.global_free_only and provider.billing_possible:
        # singura excepție: provider plătit-capabil cu cotă free verificată activă (OpenAI
        # complimentary confirmat + plafon oficial > 0 — altfel nu se poate garanta $0)
        if provider.name != "openai":
            return "BILLING_POSSIBLE_BLOCKED_BY_GLOBAL_FREE_ONLY"
    return None


def sort_key(provider: Provider, model: Model, task_class: str) -> tuple:
    """Ordinea de fallback, integral din registry (spec §10, §16): prioritatea
    providerului, apoi calitatea pe clasa de task, apoi prioritatea modelului."""
    return (provider.fallback_priority, -model.quality_for(task_class),
            model.priority, provider.name)


def resolve_model(registry: Registry, settings, model_str: str,
                  env: dict[str, str] | None = None) -> tuple[Model | None, str | None]:
    """Model din cerere → Model din registry. None + motiv pentru auto/necunoscut.

    Valorile speciale: „free" / „free/best" — gate-ul alege singur cel mai bun provider
    free pentru clasa de task (singurul mod de „auto" permis în GLOBAL_FREE_ONLY,
    pentru că alege doar din provideri verificați free — spec §8, §15).
    """
    normalized = (model_str or "").strip()
    if not normalized or normalized.lower() in ("auto", "default"):
        if settings.allow_auto:
            return None, None  # passthrough conștient, doar în afara free-only
        return None, "AUTO_MODEL_FORBIDDEN"
    if normalized.lower() in ("free", "free/best"):
        return None, None
    model = registry.model(normalized)
    if model is None:
        return None, "UNKNOWN_MODEL"
    return model, None


class Router:
    def __init__(self, registry: Registry, settings, guard: FreeQuotaGuard):
        self.registry = registry
        self.settings = settings
        self.guard = guard

    def resolve_model(self, model_str: str,
                      env: dict[str, str] | None = None) -> tuple[Model | None, str | None]:
        return resolve_model(self.registry, self.settings, model_str, env)

    def build_plan(self, model: Model | None, model_str: str, estimate: RequestEstimate,
                   task_class: str, env: dict[str, str] | None = None) -> RoutingPlan:
        trace = Trace()
        if model is None:
            if (model_str or "").strip().lower() in ("free", "free/best"):
                # sentinelul „free": cel mai bun provider free pentru clasa de task
                pick = self.next_usable(task_class, estimate, env, exclude=set(), trace=trace)
                if pick is None:
                    return RoutingPlan(target="", task_class=task_class, trace=trace,
                                       no_free_provider=True)
                provider, pick_model, _ = pick
                trace.add(f"{provider.name}/{pick_model.id}", "SELECTED", "FREE_BEST")
                return RoutingPlan(target=f"{provider.name}/{pick_model.id}",
                                   task_class=task_class, provider=provider.name,
                                   quota_group=self.guard.group_of(provider, pick_model),
                                   trace=trace)
            if model_str and not self.settings.allow_auto:
                trace.add(model_str or "auto", "REJECTED", "UNKNOWN_MODEL")
                return RoutingPlan(target="", task_class=task_class, trace=trace,
                                   no_free_provider=True)
            trace.add(model_str or "auto", "PASSTHROUGH", "ALLOW_AUTO")
            return RoutingPlan(target=model_str, task_class=task_class, trace=trace,
                               passthrough=True)

        provider = self.registry.provider_of(model)
        target = f"{provider.name}/{model.id}"
        allowed, reason, _state = self.guard.decide(model, estimate, env)
        if allowed:
            trace.add(target, "SELECTED", reason)
            return RoutingPlan(target=target, task_class=task_class, provider=provider.name,
                               quota_group=self.guard.group_of(provider, model), trace=trace)

        trace.add(target, "REJECTED", reason)
        fallback = self.next_usable(task_class, estimate, env, exclude={provider.name}, trace=trace)
        if fallback is None:
            return RoutingPlan(target="", task_class=task_class, trace=trace,
                               no_free_provider=True)
        fb_provider, fb_model, _ = fallback
        fb_target = f"{fb_provider.name}/{fb_model.id}"
        trace.add(fb_target, "FALLBACK_SELECTED", "PRIMARY_BLOCKED")
        return RoutingPlan(target=fb_target, task_class=task_class, provider=fb_provider.name,
                           quota_group=self.guard.group_of(fb_provider, fb_model), trace=trace)

    def next_usable(self, task_class: str, estimate: RequestEstimate,
                    env: dict[str, str] | None = None, exclude: set[str] | None = None,
                    trace: Trace | None = None) -> tuple[Provider, Model, tuple] | None:
        """Cel mai bun candidat liber, calculat din registry — niciodată un provider plătit.

        Cotă și context sunt filtru, nu bonus: candidatul trebuie să ÎNCAPĂ (guard-ul
        respinge cererile peste limita internă) și să aibă context suficient.
        """
        exclude = exclude or set()
        candidates: list[tuple[tuple, Provider, Model]] = []
        for provider in self.registry.providers.values():
            if provider.name in exclude:
                continue
            reason = usable_provider(provider, self.settings)
            if reason:
                if trace is not None:
                    trace.add(f"{provider.name}/*", "EXCLUDED", reason)
                continue
            if provider.api_key_env and not self.registry.api_key(provider, env):
                if trace is not None:
                    trace.add(f"{provider.name}/*", "EXCLUDED", f"NO_KEY:{provider.api_key_env}")
                continue
            if provider.billing_possible:
                # în free-only, un provider facturabil poate fi doar fallback „el însuși"
                # confirmat — pentru fallback alegem strict provideri fără facturare
                continue
            for model in provider.models:
                if estimate.total > model.context:
                    if trace is not None:
                        trace.add(f"{provider.name}/{model.id}", "EXCLUDED",
                                  f"CONTEXT:{model.context}")
                    continue  # contextul modelului nu acoperă cererea
                _ok, _why, _state = self.guard.decide(model, estimate, env)
                if not _ok:
                    if trace is not None:
                        trace.add(f"{provider.name}/{model.id}", "EXCLUDED", _why)
                    continue
                candidates.append((sort_key(provider, model, task_class), provider, model))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        _key, provider, model = candidates[0]
        return provider, model, _key

    def status_rows(self, env: dict[str, str] | None = None) -> list[dict]:
        """Rândurile pentru dashboard/status (spec secțiunile 6, 18)."""
        rows = []
        for provider in self.registry.providers.values():
            reason = usable_provider(provider, self.settings)
            has_key = bool(self.registry.api_key(provider, env)) if provider.api_key_env else True
            models = provider.models
            for model in models or [None]:
                group = self.guard.group_of(provider, model)
                state = self.guard.state_for(provider, model)
                if reason == "TOS_NOT_ALLOWED":
                    status = "NOT_ALLOWED"
                elif reason == "TOS_UNVERIFIED":
                    status = "UNVERIFIED"
                elif reason == "CAUTION_OPT_IN_REQUIRED":
                    status = "CAUTION"
                elif reason == "DISABLED_IN_REGISTRY":
                    status = "DISABLED"
                elif not has_key:
                    status = "NO_KEY"
                elif provider.billing_possible and (
                    not self.settings.openai_confirmed or state.official_limit <= 0
                ):
                    status = "FREE_QUOTA_DISABLED"
                else:
                    status = "FREE"
                rows.append({
                    "provider": provider.name,
                    "model": model.id if model else "(toate)",
                    "quota_group": group,
                    "status": status,
                    "level": state.level,
                    "used": state.used,
                    "remaining": state.remaining,
                    "official_limit": state.official_limit,
                    "safe_limit": state.safe_limit,
                    "reset": state.reset_at,
                    "margin": state.margin,
                    "billing_possible": provider.billing_possible,
                    "quota_type": provider.quota_type,
                    "tos_status": provider.tos_status,
                })
        return rows
