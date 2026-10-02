"""Scenariile de politică: fallback din registry, no-paid-fallback, ToS, task-uri."""
from __future__ import annotations

import pytest

from ai_gateway.config import Settings
from ai_gateway.estimate import RequestEstimate
from gateway_helpers import build_full, registry_dict


def _est(total: int = 1000) -> RequestEstimate:
    return RequestEstimate(input_tokens=total // 2, output_tokens=total - total // 2,
                           total=total)


# 16. fallback calculat din registry, nu hardcodat -------------------------------------
def test_fallback_calculat_din_registry():
    registry, store, guard, router, env, _ = build_full(
        env={"TESTKEY_GROQ": "k", "TESTKEY_CEREBRAS": "k", "TESTKEY_GEMINI": "k"})
    model = registry.model("openai/gpt-5.4-mini")  # blocat: OpenAI neconfirmat
    plan = router.build_plan(model, "openai/gpt-5.4-mini", _est(), "coding", env)
    assert plan.target == "groq/llama-3.3-70b-versatile"  # fallback_priority 10
    assert plan.no_free_provider is False
    verdicts = {e["target"]: e["verdict"] for e in plan.trace.entries}
    assert verdicts["openai/gpt-5.4-mini"] == "REJECTED"
    assert verdicts["groq/llama-3.3-70b-versatile"] == "FALLBACK_SELECTED"

    # fără cheie Groq → următorul din registry preia (Cerebras)
    plan2 = router.build_plan(model, "openai/gpt-5.4-mini", _est(), "coding",
                              {"TESTKEY_CEREBRAS": "k"})
    assert plan2.target == "cerebras/llama-3.3-70b"


# 13. NO paid fallback: doar OpenAI blocat în registry → NO_FREE_PROVIDER_AVAILABLE ----
def test_no_paid_fallback():
    data = registry_dict()
    data["providers"] = {"openai": data["providers"]["openai"]}  # doar provider facturabil
    fresh = build_full(env={"TESTKEY_OPENAI": "k"}, registry_data=data)
    router = fresh[3]
    model = fresh[0].model("openai/gpt-5.4-mini")
    plan = router.build_plan(model, "openai/gpt-5.4-mini", _est(), "coding", fresh[4])
    assert plan.no_free_provider is True and plan.target == ""


# 14. stările ToS: NOT_ALLOWED/UNVERIFIED excluse, CAUTION doar opt-in ------------------
def test_tos_status_enforcement():
    env = {"TESTKEY_BLOCKED": "k", "TESTKEY_UNVERIFIED": "k", "TESTKEY_CAUTION": "k",
           "TESTKEY_GROQ": "k"}
    registry, store, guard, router, env, _ = build_full(env=env)
    targets = []
    for model_str in ("blockedprov/blocked-model", "unverifiedprov/uv-model",
                      "cautionprov/caution-model", "groq/llama-3.3-70b-versatile"):
        model = registry.model(model_str)
        plan = router.build_plan(model, model_str, _est(), "coding", env)
        targets.append((model_str, plan.target, plan.no_free_provider))
    by_src = dict((src, (target, nofree)) for src, target, nofree in targets)
    # NOT_ALLOWED și UNVERIFIED nu ruldelază niciodată — cererea cade pe groq (SAFE)
    assert by_src["blockedprov/blocked-model"][0] == "groq/llama-3.3-70b-versatile"
    assert by_src["unverifiedprov/uv-model"][0] == "groq/llama-3.3-70b-versatile"
    # CAUTION, fără opt-in → cade pe groq; cu ALLOW_CAUTION=true → rămâne
    assert by_src["cautionprov/caution-model"][0] == "groq/llama-3.3-70b-versatile"
    settings = Settings(allow_caution=True)
    fresh = build_full(env=env, settings=settings)
    model = fresh[0].model("cautionprov/caution-model")
    plan = fresh[3].build_plan(model, "cautionprov/caution-model", _est(), "coding", env)
    assert plan.target == "cautionprov/caution-model"


# 15. cerere mare: sentinelul „free" alege din registry; contextul + cota filtrează -----
def test_large_request_context_si_cota():
    # fără cheie Groq → candidații sunt Cerebras (prioritate 20) și Gemini (30)
    env = {"TESTKEY_CEREBRAS": "k", "TESTKEY_GEMINI": "k"}
    registry, store, guard, router, env, _ = build_full(env=env)
    # cerere de 200K tokeni: niciun model free nu are context suficient → respins, nu
    # „trimitem orbește" (spec §15: preferă providerul cu context suficient)
    plan = router.build_plan(None, "free", _est(200_000), "large_context", env)
    assert plan.no_free_provider is True
    # cerere de 60K: încape pe ambele → prioritatea din registry alege Cerebras
    plan2 = router.build_plan(None, "free", _est(60_000), "coding", env)
    assert plan2.target == "cerebras/llama-3.3-70b"
    # Cerebras epuizat (safe 800K atins) → decide îl exclude, Gemini preia
    store.record("cerebras", "cerebras", "llama-3.3-70b", input_tokens=800_000)
    plan3 = router.build_plan(None, "free", _est(60_000), "coding", env)
    assert plan3.target == "gemini/gemini-2.5-flash"


# 16. auto/necunoscut: interzis în free-only --------------------------------------------
def test_auto_si_modele_necunoscute():
    registry, store, guard, router, env, _ = build_full(env={"TESTKEY_GROQ": "k"})
    model, reason = router.resolve_model("auto", env)
    assert model is None and reason == "AUTO_MODEL_FORBIDDEN"
    model, reason = router.resolve_model("model-inexistent", env)
    assert model is None and reason == "UNKNOWN_MODEL"
    # GLOBAL_FREE_ONLY=true + ALLOW_AUTO=true → configurație respinsă (spec §30)
    bad = Settings(global_free_only=True, allow_auto=True)
    with pytest.raises(ValueError):
        bad.validate()
    # iar OPENAI_FREE_ONLY=false sub GLOBAL_FREE_ONLY e respins
    bad2 = Settings(global_free_only=True, openai_free_only=False)
    with pytest.raises(ValueError):
        bad2.validate()


# 8. sentinelul „free": singurul „auto" permis în free-only ----------------------------
def test_sentinel_free_alege_din_registry():
    env = {"TESTKEY_GROQ": "k", "TESTKEY_CEREBRAS": "k"}
    registry, store, guard, router, env, _ = build_full(env=env)
    model, reason = router.resolve_model("free", env)
    assert model is None and reason is None  # permis fără ALLOW_AUTO
    plan = router.build_plan(None, "free", _est(1000), "coding", env)
    assert plan.target == "groq/llama-3.3-70b-versatile"
    assert plan.passthrough is False


# 9.E clasificarea task-urilor (spec §9) -------------------------------------------------
def test_clasificare_taskuri():
    from ai_gateway.classify import classify

    assert classify({"messages": [{"role": "user", "content": "explică-mi ce e un dict"}]}) \
        == "simple"
    assert classify({"messages": [{"role": "user",
                                   "content": "fix this bug in the function"}]}) == "coding"
    assert classify({"messages": [{"role": "user",
                                   "content": "analizează arhitectura și trade-off-urile"}]}) \
        == "reasoning"
    assert classify({"messages": [{"role": "user", "content": "a" * 70_000}]}) \
        == "large_context"
    assert classify({"messages": [{"role": "user", "content": "caută docs pentru versiune"}]}) \
        == "search"
    assert classify({"messages": [{"role": "user", "content": "mergează"}],
                     "tools": [{"type": "function", "function": {"name": "edit"}}]}) \
        == "agentic"
    assert classify({"messages": [{"role": "user", "content": "ceva"}]},
                    override="reasoning") == "reasoning"


# 30. GLOBAL_FREE_ONLY blochează provideri facturabili neconfirmați -----------------------
def test_global_free_only_blocheaza_billing():
    env = {"TESTKEY_OPENAI": "k", "TESTKEY_GROQ": "k"}
    registry, store, guard, router, env, _ = build_full(env=env)
    rows = router.status_rows(env)
    openai_row = next(r for r in rows if r["provider"] == "openai"
                      and r["model"] == "gpt-5.4-mini")
    assert openai_row["status"] == "FREE_QUOTA_DISABLED"
    groq_row = next(r for r in rows if r["provider"] == "groq")
    assert groq_row["status"] == "FREE"
