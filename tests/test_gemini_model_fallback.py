"""Regresii pentru lista ordonată și fallback-ul serial al providerului Gemini."""
import io
import json
import socket
import urllib.error
from pathlib import Path

from generator.providers import gemini


class _Response:
    def __init__(self, text="ok"):
        self._body = json.dumps({
            "candidates": [{
                "finishReason": "STOP",
                "content": {"parts": [{"text": text}]},
            }],
        }).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, *_args):
        return self._body


def _http_error(request, code):
    return urllib.error.HTTPError(
        request.full_url, code, f"HTTP {code}", hdrs=None,
        fp=io.BytesIO(b"model unavailable"),
    )


def _model_from_url(url, models):
    return next(model for model in models if f"/models/{model}:" in url)


def test_models_configured_are_ordered_and_duplicates_removed(monkeypatch):
    monkeypatch.setenv(
        "GEMINI_MODELS",
        "gemini-3.8-flash, gemini-3.6-flash,gemini-3.8-flash gemini-3.5-flash-lite",
    )
    monkeypatch.setenv("GEMINI_MODEL", "legacy-model")

    assert gemini._models() == [
        "gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite",
    ]


def test_legacy_single_model_setting_remains_supported(monkeypatch):
    monkeypatch.delenv("GEMINI_MODELS", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "legacy-model")

    assert gemini._models() == ["legacy-model"]


def test_default_models_match_local_and_github_configuration(monkeypatch):
    monkeypatch.delenv("GEMINI_MODELS", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    assert gemini._models() == [
        "gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite",
    ]


def test_models_are_tried_serially_after_404_and_timeout(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    models = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]
    monkeypatch.setattr(gemini, "MODELS", models)
    monkeypatch.setattr(gemini, "THROTTLE", 0)
    monkeypatch.setattr(gemini, "REQUEST_TIMEOUT", 30)
    monkeypatch.setattr(gemini, "RETRIES_PER_KEY", 1)
    calls = []

    def fake_urlopen(request, timeout):
        model = _model_from_url(request.full_url, models)
        calls.append((model, timeout))
        if model == models[0]:
            raise _http_error(request, 404)
        if model == models[1]:
            raise socket.timeout("test timeout")
        return _Response("ok from last model")

    monkeypatch.setattr(gemini.urllib.request, "urlopen", fake_urlopen)

    result = gemini.GeminiProvider()._complete("system", "user")

    assert result == "ok from last model"
    assert calls == [(model, 30) for model in models]


def test_rate_limit_retries_same_model_with_backoff_before_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    models = ["gemini-3.8-flash", "gemini-3.6-flash"]
    monkeypatch.setattr(gemini, "MODELS", models)
    monkeypatch.setattr(gemini, "THROTTLE", 0)
    monkeypatch.setattr(gemini, "RETRIES_PER_KEY", 2)
    sleeps = []
    calls = []

    def fake_urlopen(request, timeout):
        model = _model_from_url(request.full_url, models)
        calls.append(model)
        if len(calls) == 1:
            raise _http_error(request, 429)
        return _Response("retry succeeded")

    monkeypatch.setattr(gemini.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(gemini.time, "sleep", sleeps.append)

    result = gemini.GeminiProvider()._complete("system", "user")

    assert result == "retry succeeded"
    assert calls == [models[0], models[0]]
    assert sleeps == [2]


def test_actions_and_local_example_share_gemini_configuration():
    root = Path(__file__).resolve().parents[1]
    env_example = (root / ".env.example").read_text(encoding="utf-8")
    workflow = (root / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
    settings = (
        ("GEMINI_MODELS=gemini-3.8-flash,gemini-3.6-flash,gemini-3.5-flash-lite",
         "GEMINI_MODELS: ${{ vars.GEMINI_MODELS }}"),
        ("GEMINI_MAX_OUTPUT_TOKENS=8192", "GEMINI_MAX_OUTPUT_TOKENS: ${{ vars.GEMINI_MAX_OUTPUT_TOKENS }}"),
        ("GEMINI_TIMEOUT=30", "GEMINI_TIMEOUT: ${{ vars.GEMINI_TIMEOUT }}"),
    )

    assert "GEMINI_API_KEY=\n" in env_example
    assert workflow.count("GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}") == 4
    for local_setting, actions_setting in settings:
        assert local_setting in env_example
        assert workflow.count(actions_setting) == 4
