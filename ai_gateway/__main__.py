"""CLI: `python -m ai_gateway serve|status|simulate` — comenzile exacte în FREE_AI_SETUP.md."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from ai_gateway import proxy as proxy_mod
from ai_gateway.config import Settings
from ai_gateway.quota_guard import FreeQuotaGuard
from ai_gateway.registry import Registry
from ai_gateway.router import Router
from ai_gateway.estimate import RequestEstimate
from ai_gateway.usage_store import UsageStore


def build_components(settings: Settings) -> tuple:
    registry = Registry.load(settings=settings)
    store = UsageStore(settings.db_path)
    guard = FreeQuotaGuard(registry, settings, store)
    router = Router(registry, settings, guard)
    return registry, store, guard, router


def cmd_serve(args: argparse.Namespace) -> int:
    settings = Settings.load(env_file=Path(args.env) if args.env else None)
    if args.port:
        settings.port = args.port
    registry, store, guard, router = build_components(settings)
    app = proxy_mod.GatewayApp(settings, registry, guard, router, store)
    server = proxy_mod.make_server(app)
    print(f"ai_gateway {settings.host}:{settings.port} → OmniRoute "
          f"{settings.upstream_base} | free_only={settings.global_free_only} "
          f"dry_run={settings.dry_run}", file=sys.stderr)
    print(f"dashboard: http://{settings.host}:{settings.port}/guard/dashboard",
          file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    settings = Settings.load(env_file=Path(args.env) if args.env else None)
    _registry, store, _guard, router = build_components(settings)
    print(proxy_mod.status_text(type("App", (), {
        "settings": settings, "router": router, "store": store})))
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    """Spec secțiunea 29: OpenAI 2.5M cotă → consumat 2.0M → cerere 700K → respins →
    Groq/Gemini/Cerebras ales. Nimic real, magazin în memorie, fără rețea."""
    settings = Settings.load(env_file=Path(args.env) if args.env else None)
    # DB temporar pe disc (sqlite „:memory:" nu merge cu conexiune per operație)
    settings.db_path = Path(tempfile.mkdtemp(prefix="ai_gateway_sim_")) / "usage.sqlite3"
    settings.openai_confirmed = True
    registry, store, guard, router = build_components(settings)
    # chei fictive: simularea exercită logica de cotă și de rutare, nu rețeaua
    os.environ.setdefault("OPENAI_API_KEY", "cheie-de-simulare")
    for provider in registry.providers.values():
        if not provider.billing_possible and provider.enabled and provider.api_key_env:
            os.environ.setdefault(provider.api_key_env, "cheie-de-simulare")
    # scenariul cerut: OpenAI grupul 10m cu plafon oficial 2.5M (tier 1-2)
    openai = registry.providers["openai"]
    model_10m = next(m for m in openai.models if m.quota_group == "10m")
    registry.group_limits["10m"] = 2_500_000
    if args.consume:
        store.record("openai", model_10m.quota_group, model_10m.id,
                     input_tokens=args.consume, output_tokens=0)
    estimate = RequestEstimate(input_tokens=args.input_tokens,
                               output_tokens=args.output_tokens,
                               total=args.input_tokens + args.output_tokens)
    allowed, reason, state = guard.decide(model_10m, estimate)
    plan = router.build_plan(model_10m, f"openai/{model_10m.id}", estimate, "coding")
    out = {
        "scenario": f"openai 10m oficial=2.500.000, safe=2.000.000, consumat={args.consume},"
                    f" cerere={estimate.total}",
        "openai_decision": f"allowed={allowed} reason={reason} "
                           f"remaining={state.remaining}",
        "plan_target": plan.target or "— (NO_FREE_PROVIDER_AVAILABLE)",
        "trace": plan.trace.as_lines(),
        "no_free_provider": plan.no_free_provider,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai_gateway",
                                     description="FreeQuotaGuard în fața OmniRoute")
    sub = parser.add_subparsers(dest="command", required=True)

    p_serve = sub.add_parser("serve", help="pornește gate-ul local")
    p_serve.add_argument("--port", type=int, default=0)
    p_serve.add_argument("--env", default="")
    p_serve.set_defaults(func=cmd_serve)

    p_status = sub.add_parser("status", help="tabelul de cotă în terminal")
    p_status.add_argument("--env", default="")
    p_status.set_defaults(func=cmd_status)

    p_sim = sub.add_parser("simulate", help="scenariu DRY_RUN fără rețea")
    p_sim.add_argument("--input-tokens", type=int, default=700_000)
    p_sim.add_argument("--output-tokens", type=int, default=0)
    p_sim.add_argument("--consume", type=int, default=2_000_000)
    p_sim.add_argument("--env", default="")
    p_sim.set_defaults(func=cmd_simulate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
