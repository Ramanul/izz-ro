"""Proxy-ul local: client → gate (20129) → OmniRoute (20128) → provider.

Rute proprii: GET /healthz, /guard/status (JSON), /guard/dashboard (HTML),
/v1/models (din registry). Tot ce e POST /v1/* trece prin pipeline-ul de siguranță:
auth → estimare → redactare → guard (buget) → fallback → forward cu streaming →
evidența consumului + alerte.

DRY_RUN=true (spec secțiunea 29): pipeline-ul rulează complet, nimic nu pleacă în
rețea, răspunsul e simulat cu trace-ul deciziei și usage-ul ESTIMATED.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ai_gateway import classify as classify_mod
from ai_gateway import redact as redact_mod
from ai_gateway.dashboard import render_dashboard_html, render_status_text
from ai_gateway.estimate import estimate_request
from ai_gateway.router import NO_FREE_PROVIDER

HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
              "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length"}


class GatewayApp:
    """Ține toate piesele împreună; handler-ul HTTP nu decide nimic singur."""

    def __init__(self, settings, registry, guard, router, store):
        self.settings = settings
        self.registry = registry
        self.guard = guard
        self.router = router
        self.store = store

    # ---- pipeline-ul unei cereri de chat --------------------------------------------
    def handle_chat(self, headers, body: bytes) -> tuple[int, dict, str, dict]:
        """Întoarce (status, payload_răspuns, content_type, meta_trace). Nu atinge rețea."""
        try:
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return 400, {"error": {"message": "body nu e JSON valid"}}, "application/json", {}

        model_str = str(payload.get("model") or "")
        override = headers.get("X-Task-Class") or None
        if payload.get("metadata") and isinstance(payload["metadata"], dict):
            override = override or payload["metadata"].get("task_class")
        task_class = classify_mod.classify(payload, override=override)
        estimate = estimate_request(payload, self.settings.default_output_tokens)

        if self.settings.redact_secrets:
            payload, redacted_hits = redact_mod.redact_payload(payload, self.settings.env_values)
        else:
            redacted_hits = []

        model, resolve_reason = self.router.resolve_model(model_str)
        plan = self.router.build_plan(model, model_str, estimate, task_class)
        trace_lines = plan.trace.as_lines()

        if redacted_hits:
            plan.trace.add("payload", "REDACTED", ",".join(redacted_hits))
            trace_lines = plan.trace.as_lines()

        if plan.no_free_provider:
            return 429, {
                "error": {
                    "message": NO_FREE_PROVIDER,
                    "type": "free_quota_guard",
                    "detail": "Niciun provider free disponibil; sistemul NU trimite spre "
                              "provider plătit (spec secțiunile 17, 30).",
                    "trace": trace_lines,
                }
            }, "application/json", {"plan": plan}

        if self.settings.dry_run:
            return 200, self._dry_run_response(plan, estimate, payload), "application/json", \
                {"plan": plan}

        return 0, {"_forward": payload, "_target": plan.target}, "", {"plan": plan}

    def _dry_run_response(self, plan, estimate, payload) -> dict:
        stream = bool(payload.get("stream"))
        return {
            "id": "guard-dry-run",
            "object": "chat.completion",
            "model": plan.target,
            "dry_run": True,
            "decision": {
                "task_class": plan.task_class,
                "target": plan.target,
                "no_free_provider": plan.no_free_provider,
                "trace": plan.trace.as_lines(),
                "estimated_input_tokens": estimate.input_tokens,
                "estimated_output_tokens": estimate.output_tokens,
            },
            "choices": [{
                "index": 0,
                "message": {"role": "assistant",
                            "content": f"[DRY_RUN] nimic trimis. Țintă: {plan.target or '—'}. "
                                       f"Trace: {'; '.join(plan.trace.as_lines())}"},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": estimate.input_tokens,
                "completion_tokens": estimate.output_tokens,
                "total_tokens": estimate.total_tokens,
                "estimated": True,
                "note": "valori estimate de guard, nu de provider",
            },
            "stream": stream,
        }

    # ---- evidența după răspuns -------------------------------------------------------
    def record_from_usage(self, plan, usage: dict | None, estimated_tokens: int = 0) -> None:
        if not plan.provider:
            return
        prompt = int((usage or {}).get("prompt_tokens") or 0)
        completion = int((usage or {}).get("completion_tokens") or 0)
        estimated = usage is None
        if estimated:
            prompt, completion = estimated_tokens, 0
        details = (usage or {}).get("prompt_tokens_details") or {}
        self.guard.record_usage(
            plan.provider, plan.quota_group, plan.target.partition("/")[2] if plan.target else "",
            input_tokens=prompt, output_tokens=completion,
            cached_tokens=int(details.get("cached_tokens") or 0), estimated=estimated,
        )


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = "ai_gateway/0.1"

    @property
    def app(self) -> GatewayApp:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args) -> None:  # liniște pe stdout; erorile merg în stderr
        pass

    # ---- GET -----------------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 (API http.server)
        path = self.path.split("?")[0]
        if path == "/healthz":
            self._send_json(200, {"ok": True, "dry_run": self.app.settings.dry_run,
                                  "free_only": self.app.settings.global_free_only})
        elif path == "/guard/status":
            self._send_json(200, self._status_payload())
        elif path == "/guard/dashboard":
            html = render_dashboard_html(self.app.router.status_rows(),
                                         self.app.store.recent_alerts())
            self._send_raw(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/v1/models":
            self._send_json(200, {"object": "list", "data": [
                {"id": f"{p.name}/{m.id}", "object": "model", "owned_by": p.name}
                for p in self.app.registry.providers.values() if p.enabled
                for m in p.models]})
        else:
            self._send_json(404, {"error": {"message": f"rută necunoscută: {path}"}})

    def _status_payload(self) -> dict:
        rows = []
        for row in self.app.router.status_rows():
            row = dict(row)
            row["used"] = row["used"].as_dict()  # Totals → JSON-abil
            rows.append(row)
        return {
            "free_only": self.app.settings.global_free_only,
            "openai_free_only": self.app.settings.openai_free_only,
            "dry_run": self.app.settings.dry_run,
            "allow_caution": self.app.settings.allow_caution,
            "allow_auto": self.app.settings.allow_auto,
            "upstream": self.app.settings.upstream_base,
            "providers": rows,
            "alerts": self.app.store.recent_alerts(10),
        }

    # ---- POST -----------------------------------------------------------------------
    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]
        if not path.startswith("/v1/"):
            self._send_json(404, {"error": {"message": f"POST permis doar pe /v1/*: {path}"}})
            return
        if not self._authorized():
            self._send_json(401, {"error": {"message": "GATEWAY_API_KEY lipsă sau greșită"}})
            return

        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""

        if path != "/v1/chat/completions":
            self._forward_raw(path, body)
            return

        status, payload, content_type, meta = self.app.handle_chat(self.headers, body)
        plan = meta.get("plan")

        if status != 0:  # răspuns construit local (429 / 400 / dry-run)
            if status == 200 and plan is not None and self.app.settings.dry_run:
                self.app.record_from_usage(plan, usage=None,
                                           estimated_tokens=int(
                                               payload["usage"]["total_tokens"]))
            self._send_json(status, payload)
            return

        self._forward_chat(path, payload, plan)

    # ---- trimiteri upstream -----------------------------------------------------------
    def _forward_chat(self, path: str, payload: dict, plan) -> None:
        target_payload = payload.get("_forward", payload)
        if plan.target and not plan.passthrough:
            target_payload = {**target_payload, "model": plan.target}
        data = json.dumps(target_payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.app.settings.upstream_base + path, data=data, method="POST",
            headers={k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP},
        )
        request.add_header("Content-Type", "application/json")
        try:
            upstream = urllib.request.urlopen(request, timeout=600)
        except urllib.error.HTTPError as exc:
            self._relay_upstream_error(exc, plan)
            return
        except (urllib.error.URLError, OSError) as exc:
            self._send_json(502, {"error": {"message": f"OmniRoute inaccesibil: {exc}",
                                            "hint": f"pornește OmniRoute pe "
                                                    f"{self.app.settings.upstream_base}"}})
            return
        with upstream:
            content_type = upstream.headers.get("Content-Type", "application/json")
            is_stream = "text/event-stream" in content_type
            self.send_response(upstream.status)
            self.send_header("Content-Type", content_type)
            self.send_header("X-FreeGuard-Provider", plan.provider or "passthrough")
            self.send_header("X-FreeGuard-Decision", plan.decision_header)
            self.end_headers()
            if is_stream:
                seen = self._stream_back(upstream)
                self.app.record_from_usage(plan, usage=None, estimated_tokens=seen // 4)
            else:
                buffered = upstream.read()
                self.wfile.write(buffered)
                self._record_exact(buffered, plan)

    def _stream_back(self, upstream) -> int:
        """Passthrough SSE; numără octeții de date pentru estimare (marcată ESTIMATED)."""
        seen = 0
        while True:
            chunk = upstream.read(4096)
            if not chunk:
                break
            seen += len(chunk)
            self.wfile.write(chunk)
            self.wfile.flush()
        return seen

    def _record_exact(self, buffered: bytes, plan) -> None:
        try:
            parsed = json.loads(buffered.decode("utf-8"))
            self.app.record_from_usage(plan, usage=parsed.get("usage"))
        except (ValueError, UnicodeDecodeError):
            self.app.record_from_usage(plan, usage=None,
                                       estimated_tokens=len(buffered) // 4)

    def _relay_upstream_error(self, exc: urllib.error.HTTPError, plan) -> None:
        body = exc.read()
        self.send_response(exc.code)
        self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
        if plan is not None:
            self.send_header("X-FreeGuard-Provider", plan.provider or "passthrough")
            self.send_header("X-FreeGuard-Decision", plan.decision_header)
        self.end_headers()
        self.wfile.write(body)

    def _forward_raw(self, path: str, body: bytes) -> None:
        request = urllib.request.Request(
            self.app.settings.upstream_base + path, data=body or None,
            headers={k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP},
        )
        try:
            upstream = urllib.request.urlopen(request, timeout=600)
        except urllib.error.HTTPError as exc:
            self._relay_upstream_error(exc, None)
            return
        except (urllib.error.URLError, OSError) as exc:
            self._send_json(502, {"error": {"message": f"OmniRoute inaccesibil: {exc}"}})
            return
        with upstream:
            self.send_response(upstream.status)
            self.send_header("Content-Type",
                             upstream.headers.get("Content-Type", "application/json"))
            self.end_headers()
            self.wfile.write(upstream.read())

    # ---- utilitare --------------------------------------------------------------------
    def _authorized(self) -> bool:
        expected = self.app.settings.gateway_api_key
        if not expected:
            return True
        got = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        return got == expected

    def _send_json(self, status: int, payload: dict) -> None:
        self._send_raw(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

    def _send_raw(self, status: int, data: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def make_server(app: GatewayApp) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((app.settings.host, app.settings.port), GatewayHandler)
    server.daemon_threads = True
    server.app = app  # type: ignore[attr-defined]
    return server


def status_text(app: GatewayApp) -> str:
    return render_status_text(app.router.status_rows(), app.store.recent_alerts(),
                              app.settings)
