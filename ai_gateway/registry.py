"""Registry-ul de provideri și modele — date configurabile, nu cod (spec secțiunea 10).

Sursa datelor: `registry.yaml` din pachet. Fiecare provider poartă:
- tos_status: SAFE | CAUTION | UNVERIFIED | NOT_ALLOWED (spec secțiunea 11);
- billing_possible: poate produs VREODATĂ cost? —OpenAI da (depășire facturată),
  restul providerilor free resping cererile peste plafon, nu facturează;
- quota: tip (daily|monthly|one_time|rolling_window|rate_limit_only), plafon oficial,
  grup de cotă (modelele OpenAI dintr-un grup împart plafonul), reset UTC.

Registrarul NU decide ce e „cel mai bun model" hardcodat: calitățile per clasă de
task și prioritățile stau în YAML și se pot schimba fără atingerea codului.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

TOS_SAFE = "SAFE"
TOS_CAUTION = "CAUTION"
TOS_UNVERIFIED = "UNVERIFIED"
TOS_NOT_ALLOWED = "NOT_ALLOWED"
TOS_LEVELS = {TOS_NOT_ALLOWED: 0, TOS_UNVERIFIED: 1, TOS_CAUTION: 2, TOS_SAFE: 3}

QUOTA_TYPES = ("daily", "monthly", "one_time", "rolling_window", "rate_limit_only")

TASK_CLASSES = ("simple", "coding", "reasoning", "large_context", "search", "agentic")


@dataclass
class Model:
    id: str
    provider: str
    quality: dict[str, int] = field(default_factory=dict)
    context: int = 8192
    quota_group: str = ""  # gol = grupul implicit al providerului
    priority: int = 50  # mai mic = ales mai devreme la calitate egală
    default_output_tokens: int = 0

    def quality_for(self, task_class: str) -> int:
        return int(self.quality.get(task_class, self.quality.get("coding", 3)))


@dataclass
class Provider:
    name: str
    tos_status: str
    billing_possible: bool
    enabled: bool
    quota_type: str
    official_limit: int  # tokeni; 0 pentru rate_limit_only sau neconfirmat
    api_key_env: str
    base_url: str = ""
    reset: str = ""
    docs: str = ""
    source: str = ""
    notes: str = ""
    fallback_priority: int = 900
    window_seconds: int = 86400  # doar pentru rolling_window
    models: list[Model] = field(default_factory=list)

    @property
    def verified_free(self) -> bool:
        """Free real și fără risc de facturare: billing imposibil + ToS Safe/Caution."""
        return not self.billing_possible and self.tos_status in (TOS_SAFE, TOS_CAUTION)


def _models_from(raw: dict, provider_name: str) -> list[Model]:
    return [
        Model(
            id=str(m["id"]),
            provider=provider_name,
            quality={k: int(v) for k, v in (m.get("quality") or {}).items()},
            context=int(m.get("context", 8192)),
            quota_group=str(m.get("quota_group", "")),
            priority=int(m.get("priority", 50)),
            default_output_tokens=int(m.get("default_output_tokens", 0)),
        )
        for m in raw.get("models", [])
    ]


class Registry:
    """Încarcă și validează registry.yaml; expune căutări folosite de router/guard."""

    def __init__(self, data: dict, settings=None):
        self.settings = settings
        self.providers: dict[str, Provider] = {}
        for name, raw in (data.get("providers") or {}).items():
            quota = raw.get("quota") or {}
            p = Provider(
                name=name,
                tos_status=str(raw.get("tos_status", TOS_UNVERIFIED)).upper(),
                billing_possible=bool(raw.get("billing_possible", False)),
                enabled=bool(raw.get("enabled", False)),
                quota_type=str(quota.get("type", "rate_limit_only")),
                official_limit=int(quota.get("official_limit", 0) or 0),
                api_key_env=str(raw.get("api_key_env", "")),
                base_url=str(raw.get("base_url", "")),
                reset=str(quota.get("reset", "")),
                docs=str(raw.get("docs", "")),
                source=str(raw.get("source", "")),
                notes=str(raw.get("notes", "")),
                fallback_priority=int(raw.get("fallback_priority", 900)),
                window_seconds=int(quota.get("window_seconds", 86400)),
                models=_models_from(raw, name),
            )
            if p.quota_type not in QUOTA_TYPES:
                raise ValueError(f"provider {name}: quota.type invalid: {p.quota_type}")
            if p.tos_status not in TOS_LEVELS:
                raise ValueError(f"provider {name}: tos_status invalid: {p.tos_status}")
            self.providers[name] = p

        # câte un plafon pentru fiecare grup de cotă OpenAI (spec secțiunea 3: grupurile
        # au plafon comun, deci limita aparține grupului, nu modelului)
        self.group_limits: dict[str, int] = dict(data.get("group_limits") or {})

    @classmethod
    def load(cls, path: Path | None = None, settings=None) -> "Registry":
        yaml_path = path or (Path(__file__).parent / "registry.yaml")
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        return cls(data, settings)

    def model(self, model_id: str) -> Model | None:
        """Acceptă „provider/model" sau id simplu (unic)."""
        if "/" in model_id:
            provider_name, _, bare = model_id.partition("/")
            provider = self.providers.get(provider_name)
            if provider:
                for m in provider.models:
                    if m.id == bare:
                        return m
            return None
        found = [m for p in self.providers.values() for m in p.models if m.id == model_id]
        return found[0] if len(found) == 1 else None

    def provider_of(self, model: Model) -> Provider:
        return self.providers[model.provider]

    def api_key(self, provider: Provider, env: dict[str, str] | None = None) -> str:
        source = env if env is not None else os.environ
        return str(source.get(provider.api_key_env, "") or "")

    def available_providers(self, env: dict[str, str] | None = None) -> list[Provider]:
        """Provideri care pot fi folosiți ACUM (spec secțiunea 11): ToS permis, activat,
        cheie prezentă, CAUTION doar opt-in, UNVERIFIED/NOT_ALLOWED niciodată."""
        settings = self.settings
        out = []
        for p in self.providers.values():
            if p.tos_status == TOS_NOT_ALLOWED:
                continue
            if p.tos_status == TOS_UNVERIFIED:
                continue
            if p.tos_status == TOS_CAUTION and not (settings and settings.allow_caution):
                continue
            if not p.enabled:
                continue
            if p.api_key_env and not self.api_key(p, env):
                continue
            out.append(p)
        return out

    def openai_group_limit(self, group: str, settings) -> int:
        """Plafonul oficial al grupului: env (dacă > 0) > registry; 0 = neconfirmat."""
        key = {"1m": "openai_limit_group_1m", "10m": "openai_limit_group_10m"}.get(group)
        if key and settings is not None:
            value = int(getattr(settings, key))
            if value > 0:
                return value
        return int(self.group_limits.get(group, 0))
