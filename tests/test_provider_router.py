"""Regresii pentru routerul multi-provider opt-in."""
import importlib


def test_legacy_router_is_default(monkeypatch):
    monkeypatch.delenv("AI_ROUTER_MODE", raising=False)
    monkeypatch.delenv("AI_FALLBACK_PROVIDERS", raising=False)
    from generator import config
    importlib.reload(config)
    assert config.AI_ROUTER_MODE == "legacy"
    assert config.AI_FALLBACK_PROVIDERS == ""


def test_compatible_provider_catalog_skips_missing_keys(monkeypatch):
    monkeypatch.setenv("AI_FALLBACK_PROVIDERS", "groq,cerebras,mistral")
    for key in ("GROQ_API_KEY", "CEREBRAS_API_KEY", "MISTRAL_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    from generator.providers.openai_compat import configured_compatible_providers
    assert configured_compatible_providers() == []


def test_scaleway_requires_explicit_endpoint_and_model(monkeypatch):
    monkeypatch.setenv("AI_FALLBACK_PROVIDERS", "scaleway")
    monkeypatch.setenv("SCALEWAY_API_KEY", "test-scaleway")
    monkeypatch.delenv("SCALEWAY_BASE_URL", raising=False)
    monkeypatch.delenv("SCALEWAY_MODEL", raising=False)
    from generator.providers.openai_compat import configured_compatible_providers
    assert configured_compatible_providers() == []


def test_compatible_provider_order_and_models(monkeypatch):
    monkeypatch.setenv("AI_FALLBACK_PROVIDERS", "mistral,groq")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-mistral")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq")
    monkeypatch.setenv("MISTRAL_MODEL", "mistral-test")
    monkeypatch.setenv("GROQ_MODEL", "groq-test")
    from generator.providers.openai_compat import configured_compatible_providers
    providers = configured_compatible_providers()
    assert [p.name for p in providers] == ["mistral", "groq"]
    assert [p.model for p in providers] == ["mistral-test", "groq-test"]
