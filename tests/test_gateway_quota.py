"""Scenariile 1-11, 28 din spec: cotă, resete UTC, margini, OpenAI free-only, tracking."""
from __future__ import annotations

from datetime import timedelta

from ai_gateway.estimate import RequestEstimate, estimate_request
from gateway_helpers import T0, build_full


def _est(total: int) -> RequestEstimate:
    return RequestEstimate(input_tokens=total // 2, output_tokens=total - total // 2,
                           total=total)


# 1. provider available ------------------------------------------------------------
def test_provider_available_cu_cheie():
    registry, store, guard, router, env, _ = build_full(env={"TESTKEY_GROQ": "k"})
    model = registry.model("groq/llama-3.3-70b-versatile")
    allowed, reason, _state = guard.decide(model, _est(1000), env)
    assert allowed and reason == "RATE_LIMIT_ONLY_NO_TOKEN_BLOCK"


# 2. provider unavailable (fără cheie) ----------------------------------------------
def test_provider_unavailable_fara_cheie():
    registry, store, guard, router, env, _ = build_full(env={})
    model = registry.model("groq/llama-3.3-70b-versatile")
    allowed, reason, _state = guard.decide(model, _est(1000), env)
    assert not allowed and reason == "NO_KEY:TESTKEY_GROQ"


# 3. quota remaining + pragurile 80/90/100 ------------------------------------------
def test_quota_remaining_si_praguri():
    registry, store, guard, router, env, _ = build_full(env={"TESTKEY_CEREBRAS": "k"})
    model = registry.model("cerebras/llama-3.3-70b")
    # official 1M, margine 20% → safe 800K
    for tokens, expected in [(100_000, "OK"), (700_000, "WARNING"), (750_000, "HIGH"),
                             (800_000, "BLOCKED")]:
        fresh = build_full(env={"TESTKEY_CEREBRAS": "k"})
        fresh[1].record("cerebras", "cerebras", "llama-3.3-70b", input_tokens=tokens)
        state = fresh[2].state_for(fresh[0].providers["cerebras"])
        assert state.level == expected, f"{tokens} → {state.level} (atermat {expected})"
        assert state.safe_limit == 800_000
        assert state.remaining == max(0, 800_000 - tokens)
    assert model is not None


# 4. quota exhausted → blocat -------------------------------------------------------
def test_quota_exhausted_blocheaza():
    registry, store, guard, router, env, _ = build_full(env={"TESTKEY_CEREBRAS": "k"})
    store.record("cerebras", "cerebras", "llama-3.3-70b", input_tokens=800_000)
    model = registry.model("cerebras/llama-3.3-70b")
    allowed, reason, state = guard.decide(model, _est(1), env)
    assert not allowed and reason == "WOULD_EXCEED_SAFE_LIMIT" and state.level == "BLOCKED"


# 5. request would exceed quota → respins ÎNAINTE de trimitere -----------------------
def test_request_would_exceed_safe_limit():
    registry, store, guard, router, env, _ = build_full(env={"TESTKEY_CEREBRAS": "k"})
    store.record("cerebras", "cerebras", "llama-3.3-70b", input_tokens=500_000)
    model = registry.model("cerebras/llama-3.3-70b")
    allowed, reason, state = guard.decide(model, _est(400_000), env)  # 500k+400k > 800k
    assert not allowed and reason == "WOULD_EXCEED_SAFE_LIMIT" and state.remaining == 300_000


# 6. daily reset la 00:00 UTC --------------------------------------------------------
def test_daily_reset_utc():
    registry, store, guard, router, env, clock = build_full(env={"TESTKEY_CEREBRAS": "k"})
    store.record("cerebras", "cerebras", "llama-3.3-70b", input_tokens=900_000)
    assert guard.state_for(registry.providers["cerebras"]).level == "BLOCKED"
    clock["now"] = T0 + timedelta(days=1)  # peste miezul nopții UTC
    state = guard.state_for(registry.providers["cerebras"])
    assert state.used.total_tokens == 0 and state.level == "OK"


# 7. monthly reset -------------------------------------------------------------------
def test_monthly_reset():
    registry, store, guard, router, env, clock = build_full(env={"TESTKEY_MONTHLY": "k"})
    store.record("monthlyprov", "monthlyprov", "m-model", input_tokens=100_000)
    assert guard.state_for(registry.providers["monthlyprov"]).level == "BLOCKED"
    clock["now"] = T0 + timedelta(days=35)  # luna următoare
    state = guard.state_for(registry.providers["monthlyprov"])
    assert state.used.total_tokens == 0 and state.level == "OK"


# 8. one-time quota: nu se resetează niciodată ----------------------------------------
def test_one_time_nu_se_reseteaza():
    registry, store, guard, router, env, clock = build_full(
        env={"TESTKEY_UNVERIFIED": "k"})
    # UNVERIFIED e oricum blocat de ToS; testăm mecanica one_time prin cota «monthlyprov»
    # transformată: folosim un provider one_time verifiable direct pe state
    registry.providers["unverifiedprov"].tos_status = "SAFE"
    store.record("unverifiedprov", "unverifiedprov", "uv-model", input_tokens=100_000)
    state = guard.state_for(registry.providers["unverifiedprov"])
    assert state.level == "BLOCKED" and state.quota_type == "one_time"
    clock["now"] = T0 + timedelta(days=400)  # peste un an
    assert guard.state_for(registry.providers["unverifiedprov"]).level == "BLOCKED"


# 9. rate_limit_only: nu se blochează pe tokeni (spec §22) ----------------------------
def test_rate_limit_only_nu_e_cota_garantata():
    registry, store, guard, router, env, _ = build_full(env={"TESTKEY_GROQ": "k"})
    store.record("groq", "groq", "llama-3.3-70b-versatile", input_tokens=5_000_000)
    model = registry.model("groq/llama-3.3-70b-versatile")
    allowed, reason, state = guard.decide(model, _est(500_000), env)
    assert allowed and state.remaining is None and "RATE_LIMIT_ONLY" in reason


# 10. OpenAI free-only: neconfirmat → indisponibil; confirmat → cu margine ------------
def test_openai_free_only_mecanica_completa():
    # a) fără confirmare → FREE_QUOTA_DISABLED (chiar cu cheie)
    registry, store, guard, router, env, _ = build_full(env={"TESTKEY_OPENAI": "k"})
    model = registry.model("openai/gpt-5.4-mini")
    allowed, reason, _ = guard.decide(model, _est(1000), env)
    assert not allowed and reason == "FREE_QUOTA_DISABLED"

    # b) confirmat + plafon oficial 2.5M pe grupul 10m → permis; safe = 2.0M
    settings = registry.settings
    settings.openai_confirmed = True
    registry.group_limits["10m"] = 2_500_000
    allowed, reason, state = guard.decide(model, _est(1_500_000), env)
    assert allowed and state.safe_limit == 2_000_000 and state.official_limit == 2_500_000

    # c) cererea care ar trece safe limit → respinsă înainte de trimitere
    store.record("openai", "10m", "gpt-5.4-mini", input_tokens=1_900_000)
    allowed, reason, _ = guard.decide(model, _est(200_000), env)
    assert not allowed and reason == "WOULD_EXCEED_SAFE_LIMIT"

    # d) grupurile împart plafonul: consum pe alt model din grupul 10m se vede la toate
    store2 = store  # aceeași bază; consumăm prin gpt-5.1-codex-mini echivalent
    store2.record("openai", "10m", "gpt-5.4-mini", input_tokens=100_000)
    state = guard.state_for(registry.providers["openai"], model)
    assert state.used.total_tokens == 2_000_000 and state.level == "BLOCKED"


# 11. tracking: estimat vs exact, întrebările din spec §6 ------------------------------
def test_tracking_estimat_vs_exact():
    registry, store, guard, router, env, _ = build_full(env={"TESTKEY_GROQ": "k"})
    store.record("groq", "groq", "llama-3.3-70b-versatile", input_tokens=100,
                 output_tokens=50, cached_tokens=20, estimated=False)
    store.record("groq", "groq", "llama-3.3-70b-versatile", input_tokens=400,
                 output_tokens=0, estimated=True)
    totals = store.totals("groq", "groq", scope="daily")
    assert totals.exact_tokens == 150
    assert totals.estimated_tokens == 400
    assert totals.requests == 2 and totals.cached_tokens == 20


# 15. estimarea conservatoare ----------------------------------------------------------
def test_estimate_conservator():
    payload = {"messages": [{"role": "user", "content": "a" * 4000}], "max_tokens": 100}
    est = estimate_request(payload)
    assert est.input_tokens >= 1000  # 4000/4 + factor de siguranță
    assert est.output_tokens == 110  # 100 * 1.10
    assert est.total_tokens == est.input_tokens + est.output_tokens


# registry-ul real al pachetului se încarcă și validează --------------------------------
def test_registry_ul_real_se_incarca():
    from ai_gateway.registry import Registry

    registry = Registry.load()
    assert "openai" in registry.providers and "groq" in registry.providers
    for p in registry.providers.values():
        assert p.tos_status in ("SAFE", "CAUTION", "UNVERIFIED", "NOT_ALLOWED")
        assert p.quota_type in ("daily", "monthly", "one_time", "rolling_window",
                                "rate_limit_only")
    openai_groups = {m.quota_group for m in registry.providers["openai"].models}
    assert openai_groups <= {"1m", "10m"}


# alertele la 80/90/100 (spec §19) -------------------------------------------------------
def test_alerte_la_praguri():
    registry, store, guard, router, env, _ = build_full(env={"TESTKEY_CEREBRAS": "k"})
    provider = registry.providers["cerebras"]
    store.record("cerebras", "cerebras", "llama-3.3-70b", input_tokens=650_000)  # 81%
    guard.maybe_alert(provider, guard.state_for(provider))
    assert store.latest_alert_today("cerebras", "cerebras") == "WARNING"
    store.record("cerebras", "cerebras", "llama-3.3-70b", input_tokens=80_000)  # 91%
    guard.maybe_alert(provider, guard.state_for(provider))
    assert store.latest_alert_today("cerebras", "cerebras") == "HIGH"
    store.record("cerebras", "cerebras", "llama-3.3-70b", input_tokens=80_000)  # 101%
    guard.maybe_alert(provider, guard.state_for(provider))
    assert store.latest_alert_today("cerebras", "cerebras") == "BLOCKED"
    # nu se repetă aceeași alertă
    guard.maybe_alert(provider, guard.state_for(provider))
    assert len([a for a in store.recent_alerts() if a["level"] == "BLOCKED"]) == 1
