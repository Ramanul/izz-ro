"""Helperi comuni pentru testele ai_gateway — registry synthetic + ceas injectabil.

Folosim variabile de env cu prefix TESTKEY_ ca testele să nu depindă (și să nu
contamineze) cheile reale ale mașinii.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_gateway.config import Settings  # noqa: E402
from ai_gateway.quota_guard import FreeQuotaGuard  # noqa: E402
from ai_gateway.registry import Registry  # noqa: E402
from ai_gateway.router import Router  # noqa: E402
from ai_gateway.usage_store import UsageStore  # noqa: E402

T0 = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)


def fake_clock():
    state = {"now": T0}
    return state, lambda: state["now"]


def registry_dict() -> dict:
    """Registry minimal cu toate categoriile ToS necesare testelor (spec §11, §28.14)."""
    return {
        "group_limits": {"1m": 0, "10m": 0},
        "providers": {
            "openai": {
                "tos_status": "SAFE", "billing_possible": True, "enabled": True,
                "api_key_env": "TESTKEY_OPENAI", "base_url": "https://api.openai.com/v1",
                "quota": {"type": "daily", "reset": "00:00 UTC"}, "fallback_priority": 5,
                "models": [
                    {"id": "gpt-5.4-mini", "quota_group": "10m", "context": 128000,
                     "priority": 10, "quality": {"coding": 5}},
                    {"id": "gpt-5.4", "quota_group": "1m", "context": 128000,
                     "priority": 10, "quality": {"coding": 5}},
                ],
            },
            "groq": {
                "tos_status": "SAFE", "billing_possible": False, "enabled": True,
                "api_key_env": "TESTKEY_GROQ", "base_url": "https://api.groq.com/openai/v1",
                "quota": {"type": "rate_limit_only"}, "fallback_priority": 10,
                "models": [
                    {"id": "llama-3.3-70b-versatile", "context": 128000, "priority": 10,
                     "quality": {"coding": 4}},
                    {"id": "llama-3.1-8b-instant", "context": 8000, "priority": 30,
                     "quality": {"coding": 2}},
                ],
            },
            "cerebras": {
                "tos_status": "SAFE", "billing_possible": False, "enabled": True,
                "api_key_env": "TESTKEY_CEREBRAS",
                "quota": {"type": "daily", "official_limit": 1_000_000},
                "fallback_priority": 20,
                "models": [
                    {"id": "llama-3.3-70b", "context": 128000, "priority": 10,
                     "quality": {"coding": 4}},
                ],
            },
            "gemini": {
                "tos_status": "SAFE", "billing_possible": False, "enabled": True,
                "api_key_env": "TESTKEY_GEMINI", "quota": {"type": "rate_limit_only"},
                "fallback_priority": 30,
                "models": [
                    {"id": "gemini-2.5-flash", "context": 128000, "priority": 10,
                     "quality": {"coding": 4}},
                ],
            },
            "monthlyprov": {
                "tos_status": "SAFE", "billing_possible": False, "enabled": True,
                "api_key_env": "TESTKEY_MONTHLY",
                "quota": {"type": "monthly", "official_limit": 100_000},
                "models": [{"id": "m-model", "context": 32000, "priority": 10,
                            "quality": {"coding": 3}}],
            },
            "blockedprov": {
                "tos_status": "NOT_ALLOWED", "billing_possible": False, "enabled": True,
                "api_key_env": "TESTKEY_BLOCKED", "quota": {"type": "rate_limit_only"},
                "models": [{"id": "blocked-model", "context": 128000, "priority": 1,
                            "quality": {"coding": 5}}],
            },
            "unverifiedprov": {
                "tos_status": "UNVERIFIED", "billing_possible": True, "enabled": True,
                "api_key_env": "TESTKEY_UNVERIFIED",
                "quota": {"type": "one_time", "official_limit": 100_000},
                "models": [{"id": "uv-model", "context": 128000, "priority": 1,
                            "quality": {"coding": 5}}],
            },
            "cautionprov": {
                "tos_status": "CAUTION", "billing_possible": False, "enabled": True,
                "api_key_env": "TESTKEY_CAUTION", "quota": {"type": "rate_limit_only"},
                "models": [{"id": "caution-model", "context": 128000, "priority": 40,
                            "quality": {"coding": 4}}],
            },
        },
    }


def _tmp_db():
    import tempfile

    return Path(tempfile.mkdtemp()) / "usage.sqlite3"


def build_full(env: dict[str, str] | None = None, *, settings: Settings | None = None,
               registry_data: dict | None = None, now: datetime | None = None):
    env = dict(env or {})
    settings = settings or Settings()
    clock_state, now_fn = fake_clock()
    if now is not None:
        clock_state["now"] = now
    store = UsageStore(_tmp_db(), now_fn=now_fn)
    registry = Registry(registry_data or registry_dict(), settings)
    guard = FreeQuotaGuard(registry, settings, store)
    router = Router(registry, settings, guard)
    return registry, store, guard, router, env, clock_state
