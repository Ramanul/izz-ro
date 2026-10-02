"""FreeQuotaGuard — poarta de buget înainte de fiecare cerere (spec secțiunile 2, 5, 7, 14-15, 19).

Lanțul obligatoriu pentru orice provider care POATE factura (OpenAI):
    FREE QUOTA → SAFE INTERNAL LIMIT → STOP → FALLBACK
niciodată     FREE QUOTA → depășire → paid usage.

- safe_limit = official_limit * (1 - safety_margin), implicit margine 20% (secțiunea 5);
- pragurile 80/90/100% se referă la LIMITA INTERNĂ de siguranță, deci BLOCKED vine
  mereu ÎNAINTE de plafonul oficial care ar putea factura;
- resetele sunt UTC (daily: 00:00 UTC, monthly: 1 ale lunii, one_time: niciodată,
  rolling_window: fereastră glisantă, rate_limit_only: nu se blochează pe tokeni);
- când nu există usage exact de la provider, consumul se contorizează ca ESTIMATED.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ai_gateway.estimate import RequestEstimate
from ai_gateway.registry import Model, Provider, Registry, TOS_NOT_ALLOWED, TOS_UNVERIFIED
from ai_gateway.usage_store import Totals, UsageStore

LEVELS = ("OK", "WARNING", "HIGH", "BLOCKED")
LEVEL_RANK = {name: i for i, name in enumerate(LEVELS)}
WARNING_AT = 0.80
HIGH_AT = 0.90
BLOCKED_AT = 1.00


@dataclass
class QuotaState:
    provider: str
    quota_group: str
    quota_type: str
    official_limit: int
    safe_limit: int | None
    used: Totals
    remaining: int | None  # None = nu se blochează pe tokeni (rate_limit_only)
    level: str
    reset_at: str
    billing_possible: bool
    margin: float

    @property
    def pct_of_safe(self) -> float | None:
        if not self.safe_limit:
            return None
        return self.used.total_tokens / self.safe_limit

    @property
    def status_word(self) -> str:
        return self.level if self.level != "OK" else "SAFE"


def _next_utc_midnight(now: datetime) -> datetime:
    tomorrow = (now + timedelta(days=1)).date()
    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc)


def _next_utc_month(now: datetime) -> datetime:
    if now.month == 12:
        return datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)


class FreeQuotaGuard:
    def __init__(self, registry: Registry, settings, store: UsageStore):
        self.registry = registry
        self.settings = settings
        self.store = store

    # ---- grupul de cotă -------------------------------------------------------------
    def group_of(self, provider: Provider, model: Model | None) -> str:
        if model and model.quota_group:
            return model.quota_group
        return provider.name

    def official_limit(self, provider: Provider, group: str) -> int:
        if provider.name == "openai":
            # grupurile OpenAI au plafon comun; plafonul e pe grup (spec secțiunea 3)
            return self.registry.openai_group_limit(group, self.settings)
        return provider.official_limit

    # ---- starea de cotă -------------------------------------------------------------
    def state_for(self, provider: Provider, model: Model | None = None) -> QuotaState:
        group = self.group_of(provider, model)
        now = self.store.now_fn()
        official = self.official_limit(provider, group)
        margin = self.settings.openai_safety_margin if provider.name == "openai" else 0.20
        safe = int(official * (1 - margin)) if official > 0 else None

        if provider.quota_type == "daily":
            used = self.store.totals(provider.name, group, scope="daily")
            reset = _next_utc_midnight(now)
        elif provider.quota_type == "monthly":
            used = self.store.totals(provider.name, group, scope="monthly")
            reset = _next_utc_month(now)
        elif provider.quota_type == "one_time":
            used = self.store.totals(provider.name, group, scope="lifetime")
            reset = None
        elif provider.quota_type == "rolling_window":
            used = self.store.totals(provider.name, group, scope="window")
            reset = now + timedelta(seconds=provider.window_seconds)
        else:  # rate_limit_only
            used = self.store.totals(provider.name, group, scope="daily")
            reset = _next_utc_midnight(now)

        if provider.quota_type == "rate_limit_only" or official <= 0:
            remaining = None
            level = "OK"
        else:
            remaining = max(0, (safe or 0) - used.total_tokens)
            pct = used.total_tokens / safe if safe else 0.0
            if pct >= BLOCKED_AT:
                level = "BLOCKED"
            elif pct >= HIGH_AT:
                level = "HIGH"
            elif pct >= WARNING_AT:
                level = "WARNING"
            else:
                level = "OK"

        reset_word = "fără reset (one_time)" if reset is None else (
            reset.isoformat(timespec="seconds") if isinstance(reset, datetime)
            else str(reset))
        return QuotaState(
            provider=provider.name, quota_group=group, quota_type=provider.quota_type,
            official_limit=official, safe_limit=safe, used=used, remaining=remaining,
            level=level, reset_at=reset_word, billing_possible=provider.billing_possible,
            margin=margin,
        )

    # ---- decizia înainte de cerere ---------------------------------------------------
    def decide(self, model: Model, estimate: RequestEstimate,
               env: dict[str, str] | None = None) -> tuple[bool, str, QuotaState]:
        provider = self.registry.provider_of(model)
        group = self.group_of(provider, model)

        if provider.tos_status in (TOS_UNVERIFIED, TOS_NOT_ALLOWED):
            # ultimul filtru (defence in depth): routerul îi exclude deja, guard-ul repetă
            return False, f"TOS_{provider.tos_status}", self.state_for(provider, model)
        if provider.tos_status == "CAUTION" and not self.settings.allow_caution:
            # CAUTION e opt-in și pe calea primară, nu doar în fallback (spec §11)
            return False, "CAUTION_OPT_IN_REQUIRED", self.state_for(provider, model)

        if provider.api_key_env and not self.registry.api_key(provider, env):
            return False, f"NO_KEY:{provider.api_key_env}", self.state_for(provider, model)

        if provider.billing_possible:
            # singurul provider care poate factura: OpenAI complimentary (docs oficiale:
            # depășirea se facturează integral) — porțile de la secțiunea 14, mecanic:
            if self.settings.openai_free_only and (
                not self.settings.openai_confirmed or self.official_limit(provider, group) <= 0
            ):
                return False, "FREE_QUOTA_DISABLED", self.state_for(provider, model)

        state = self.state_for(provider, model)
        if state.remaining is None:
            return True, "RATE_LIMIT_ONLY_NO_TOKEN_BLOCK", state
        if estimate.total > state.remaining:
            return False, "WOULD_EXCEED_SAFE_LIMIT", state
        return True, "ALLOWED", state

    # ---- înregistrare după răspuns ---------------------------------------------------
    def record_usage(self, provider_name: str, quota_group: str, model_id: str, *,
                     input_tokens: int = 0, output_tokens: int = 0, cached_tokens: int = 0,
                     estimated: bool = False) -> QuotaState:
        provider = self.registry.providers.get(provider_name)
        self.store.record(
            provider_name, quota_group, model_id,
            input_tokens=input_tokens, output_tokens=output_tokens,
            cached_tokens=cached_tokens, estimated=estimated,
        )
        if provider is None:
            return QuotaState(provider_name, quota_group, "unknown", 0, None, Totals(),
                              None, "OK", "-", False, 0.0)
        state = self.state_for(provider)
        self.maybe_alert(provider, state)
        return state

    def maybe_alert(self, provider: Provider, state: QuotaState) -> None:
        """Alerte la 80% / 90% / 100% din limita internă (spec secțiunea 19)."""
        if state.level == "OK":
            return
        previous = self.store.latest_alert_today(state.provider, state.quota_group)
        if previous and LEVEL_RANK.get(previous, 0) >= LEVEL_RANK[state.level]:
            return
        message = (
            f"{state.provider}[{state.quota_group}] {state.level}: "
            f"{state.used.total_tokens}/{state.safe_limit} tokeni azi "
            f"(plafon oficial {state.official_limit}, margine {state.margin:.0%}); "
            f"reset: {state.reset_at}"
        )
        self.store.record_alert(state.provider, state.quota_group, state.level, message)
        print(f"[FreeQuotaGuard] {message}", file=sys.stderr)
