"""E2E: gate-ul real pe port efemergent + upstream OmniRoute fals.

Verifică: DRY_RUN nu trimite nimic, redactarea ajunge la upstream, fallback-ul
rescrie modelul, 429 NO_FREE_PROVIDER_AVAILABLE fără provideri, auth, concurență.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ai_gateway.config import Settings
from ai_gateway.proxy import GatewayApp, make_server
from gateway_helpers import build_full


class MockOmniRoute(BaseHTTPRequestHandler):
    """Upstream fals: înregistrează cererile, răspunde OpenAI-compatibil."""

    calls: list[dict] = []
    fail_with: int | None = None

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        type(self).calls.append({"path": self.path, "body": body})
        if type(self).fail_with:
            payload = json.dumps({"error": "simulat"}).encode()
            self.send_response(type(self).fail_with)
        else:
            payload = json.dumps({
                "id": "mock-1", "model": body.get("model"),
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                          "total_tokens": 15,
                          "prompt_tokens_details": {"cached_tokens": 4}},
            }).encode()
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        pass


@pytest.fixture()
def stack(monkeypatch):
    """Gate + upstream fals, ambele pe porturi efemere."""
    MockOmniRoute.calls = []
    MockOmniRoute.fail_with = None
    # proxy-ul citește cheile din os.environ (nu dintr-un dict) — punem chei de test
    monkeypatch.setenv("TESTKEY_GROQ", "k")
    monkeypatch.setenv("TESTKEY_CEREBRAS", "k")
    monkeypatch.delenv("TESTKEY_OPENAI", raising=False)
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), MockOmniRoute)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()

    settings = Settings()
    settings.upstream_base = f"http://127.0.0.1:{upstream.server_address[1]}"
    registry, store, guard, router, _env, _clock = build_full(settings=settings)
    app = GatewayApp(settings, registry, guard, router, store)
    server = make_server(app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    yield base, app, settings
    server.shutdown()
    upstream.shutdown()


def _chat(base: str, payload: dict, headers: dict | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(
        base + "/v1/chat/completions", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def test_dry_run_nu_trimite_nimic(stack):
    base, app, settings = stack
    settings.dry_run = True
    status, body = _chat(base, {"model": "groq/llama-3.3-70b-versatile",
                                "messages": [{"role": "user", "content": "salut"}]})
    assert status == 200 and body["dry_run"] is True
    assert body["decision"]["target"] == "groq/llama-3.3-70b-versatile"
    assert body["usage"]["estimated"] is True
    assert MockOmniRoute.calls == []  # NICIUN apel real (spec §29)


def test_redactare_ajunge_la_upstream(stack):
    base, app, settings = stack
    status, _ = _chat(base, {
        "model": "groq/llama-3.3-70b-versatile",
        "messages": [{"role": "user",
                      "content": "cheia mea e sk-proj-ABCDEFGHIJKLMNOPQRSTU1234"}]})
    assert status == 200
    sent = MockOmniRoute.calls[0]["body"]
    assert "sk-proj-" not in json.dumps(sent)
    assert "[REDACTED]" in sent["messages"][0]["content"]


def test_openai_blocat_rescris_pe_fallback(stack):
    base, app, settings = stack
    status, body = _chat(base, {
        "model": "openai/gpt-5.4-mini",
        "messages": [{"role": "user", "content": "salut"}]})
    assert status == 200
    # OpenAI neconfirmat → cererea ajunge la upstream CU model rescris pe Groq
    assert MockOmniRoute.calls[0]["body"]["model"] == "groq/llama-3.3-70b-versatile"
    assert body["model"] == "groq/llama-3.3-70b-versatile"


def test_no_free_provider_429_si_niciun_apel(stack):
    base, app, settings = stack
    # model necunoscut → nimic valid de rutat → 429, nu trimitem nicăieri (spec §17/§30)
    status, body = _chat(base, {"model": "model-necunoscut-cutare",
                                "messages": [{"role": "user", "content": "x"}]})
    assert status == 429
    assert body["error"]["message"] == "NO_FREE_PROVIDER_AVAILABLE"
    assert MockOmniRoute.calls == []


def test_usage_exact_inregistrat(stack):
    base, app, settings = stack
    _chat(base, {"model": "groq/llama-3.3-70b-versatile",
                 "messages": [{"role": "user", "content": "salut"}]})
    totals = app.store.totals("groq", "groq", scope="daily")
    assert totals.requests == 1 and totals.input_tokens == 10
    assert totals.output_tokens == 5 and totals.cached_tokens == 4
    assert totals.estimated_tokens == 0  # usage exact de la provider


def test_auth_cu_cheie_locala(stack):
    base, app, settings = stack
    settings.gateway_api_key = "secret-local"
    status, _ = _chat(base, {"model": "groq/llama-3.3-70b-versatile",
                             "messages": [{"role": "user", "content": "x"}]})
    assert status == 401
    status, _ = _chat(base, {"model": "groq/llama-3.3-70b-versatile",
                             "messages": [{"role": "user", "content": "x"}]},
                      headers={"Authorization": "Bearer secret-local"})
    assert status == 200


def test_status_si_dashboard_rute(stack):
    base, app, settings = stack
    with urllib.request.urlopen(base + "/guard/status", timeout=10) as resp:
        payload = json.loads(resp.read().decode())
    assert payload["free_only"] is True
    assert any(r["provider"] == "openai" for r in payload["providers"])
    with urllib.request.urlopen(base + "/guard/dashboard", timeout=10) as resp:
        html = resp.read().decode()
    assert "FreeQuotaGuard" in html and "Provider" in html
    with urllib.request.urlopen(base + "/v1/models", timeout=10) as resp:
        models = json.loads(resp.read().decode())
    assert any(m["id"].startswith("groq/") for m in models["data"])


def test_cereri_concurente(stack):
    base, app, settings = stack
    n = 16
    results: list[int] = []
    lock = threading.Lock()

    def worker():
        status, _ = _chat(base, {"model": "groq/llama-3.3-70b-versatile",
                                 "messages": [{"role": "user", "content": "x"}]})
        with lock:
            results.append(status)

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert results == [200] * n
    totals = app.store.totals("groq", "groq", scope="daily")
    assert totals.requests == n  # SQLite consistent sub concurență
