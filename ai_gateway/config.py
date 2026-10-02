"""Configurare din .env (parser standard, fără dependențe) + validări de siguranță.

Spec: secțiunile 12, 13, 14, 29, 30. Valabile la import-ul Settings.load():
- GLOBAL_FREE_ONLY=true interzice ALLOW_AUTO=true (auto-ul ar putea alege un provider
  pe care registry-ul nu l-a verificat — nu se poate garanta $0).
- OPENAI_FREE_ONLY=false e respins cât timp GLOBAL_FREE_ONLY=true.
- OpenAI nu devine disponibil niciodată doar pentru că există cheie: cere explicit
  OPENAI_COMPLIMENTARY_CONFIRMED=true și un plafon zilnic oficial > 0 (secțiunea 3).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REDACTED = "[REDACTED]"


def parse_env_file(path: Path) -> dict[str, str]:
    """Parser .env minimal: KEY=VALUE, comentarii #, spații tăiate, ghilimele luate ca atare."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'\"")
        if key:
            values[key] = val
    return values


@dataclass
class Settings:
    # rețea (secțiunea 12: doar localhost)
    host: str = "127.0.0.1"
    port: int = 20129
    upstream_base: str = "http://127.0.0.1:20128"  # OmniRoute
    gateway_api_key: str = ""  # dacă e setată, clientul trebuie să trimită Bearer <cheie>

    # siguranță globală (secțiunile 2, 17, 30)
    global_free_only: bool = True
    openai_free_only: bool = True
    allow_caution: bool = False  # CAUTION e opt-in (secțiunea 11)
    allow_auto: bool = False  # model „auto"/necunoscut: interzis implicit
    redact_secrets: bool = True
    dry_run: bool = False  # secțiunea 29

    # OpenAI complimentary (secțiunile 3, 5, 14, 32)
    openai_confirmed: bool = False  # utilizatorul confirmă eligibilitatea + data sharing activ
    openai_limit_group_1m: int = 0  # plafonul OFICIAL zilnic, tokeni — 0 = oferta neconfirmată
    openai_limit_group_10m: int = 0
    openai_safety_margin: float = 0.20  # secțiunea 5: 20% implicit, configurabil

    # estimare (secțiunea 15)
    default_output_tokens: int = 2048

    # căi
    env_path: Path = field(default_factory=lambda: Path(".env"))
    db_path: Path = field(default_factory=lambda: Path("ai_gateway_data/usage.sqlite3"))

    # valorile din .env, pentru redactare (secțiunea 24: valorile .env nu pleacă niciodată)
    env_values: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        env_path = env_file or Path(".env")
        file_values = parse_env_file(env_path)

        def get(name: str, default: str = "") -> str:
            return os.environ.get(name, file_values.get(name, default))

        def flag(name: str, default: bool) -> bool:
            raw = get(name, "1" if default else "0").strip().lower()
            if raw in ("1", "true", "yes", "on", "da"):
                return True
            if raw in ("0", "false", "no", "off", "nu"):
                return False
            return default

        s = cls(
            host=get("GATEWAY_HOST", "127.0.0.1"),
            port=int(get("GATEWAY_PORT", "20129")),
            upstream_base=get("OMNIROUTE_BASE_URL", "http://127.0.0.1:20128").rstrip("/"),
            gateway_api_key=get("GATEWAY_API_KEY"),
            global_free_only=flag("GLOBAL_FREE_ONLY", True),
            openai_free_only=flag("OPENAI_FREE_ONLY", True),
            allow_caution=flag("ALLOW_CAUTION", False),
            allow_auto=flag("ALLOW_AUTO", False),
            redact_secrets=flag("REDACT_SECRETS", True),
            dry_run=flag("DRY_RUN", False),
            openai_confirmed=flag("OPENAI_COMPLIMENTARY_CONFIRMED", False),
            openai_limit_group_1m=int(get("OPENAI_LIMIT_GROUP_1M", "0") or "0"),
            openai_limit_group_10m=int(get("OPENAI_LIMIT_GROUP_10M", "0") or "0"),
            openai_safety_margin=max(0.0, min(0.9, float(get("OPENAI_SAFETY_MARGIN", "0.2")))),
            default_output_tokens=int(get("GATEWAY_DEFAULT_OUTPUT_TOKENS", "2048")),
            env_path=env_path,
            db_path=Path(get("GATEWAY_DB_PATH", "ai_gateway_data/usage.sqlite3")),
            env_values={**file_values, **{k: v for k, v in os.environ.items() if k in file_values}},
        )
        s.validate()
        return s

    def validate(self) -> None:
        errors: list[str] = []
        if self.global_free_only and self.allow_auto:
            errors.append(
                "GLOBAL_FREE_ONLY=true interzice ALLOW_AUTO=true: modelul „auto” lasă OmniRoute "
                "să aleagă orice provider, deci $0 nu mai poate fi garantat. Folosește modele "
                "explicite „provider/model” sau stabilește în OmniRoute un combo free-only."
            )
        if self.global_free_only and not self.openai_free_only:
            errors.append(
                "GLOBAL_FREE_ONLY=true interzice OPENAI_FREE_ONLY=false: OpenAI facturează "
                "peste plafonul complimentary (docs oficiale), deci nu poate fi tratat ca free."
            )
        if self.openai_confirmed and self.openai_limit_group_1m <= 0 and self.openai_limit_group_10m <= 0:
            errors.append(
                "OPENAI_COMPLIMENTARY_CONFIRMED=true cere cel puțin un plafon oficial > 0 "
                "(OPENAI_LIMIT_GROUP_1M / OPENAI_LIMIT_GROUP_10M). Fără plafon, guard-ul nu "
                "poate opri cererile ÎNAINTE de limită — și OpenAI facturează depășirea integral."
            )
        if self.openai_limit_group_1m < 0 or self.openai_limit_group_10m < 0:
            errors.append("Plafonele OpenAI nu pot fi negative.")
        if self.host not in ("127.0.0.1", "localhost", "::1"):
            errors.append(
                f"GATEWAY_HOST={self.host!r} nu e localhost. Gate-ul e un instrument personal; "
                "expunerea pe rețea e interzisă (spec secțiunea 12)."
            )
        if errors:
            raise ValueError("Configurație respinsă:\n- " + "\n- ".join(errors))
