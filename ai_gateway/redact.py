"""Redactarea secretelor din contextul transmis modelului (spec secțiunea 24).

Aplicată DOAR payload-ului trimis spre provider, niciodată fișierelor locale.
Tipare acoperite: chei API (OpenAI/Anthropic/GitHub/AWS/Cloudflare), chei private
PEM, DATABASE_URL, atribuiri password=/secret=/token=, plus valorile reale din .env
oricărei variabile — dacă secretul e deja în context, îl scoatem și pe el.
"""
from __future__ import annotations

import re

REDACTED = "[REDACTED]"

# (nume, tipar) — tiparele caută în tot textul mesajului, nu în linii întregi.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("openai_key", re.compile(r"sk-(?!ant-)(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("github_token", re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}")),
    ("github_fine", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("aws_access", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{12,}\b")),
    ("aws_secret", re.compile(r"(?i)aws.{0,20}?['\"][A-Za-z0-9/+=]{32,}['\"]")),
    ("google_key", re.compile(r"AIza[0-9A-Za-z_-]{30,}")),
    ("slack_token", re.compile(r"xox[bpars]-[A-Za-z0-9-]{10,}")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP |DSA )?PRIVATE KEY(?: BLOCK)?-----")),
    ("database_url", re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s'\"]{8,}")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{24,}")),
    ("kv_assign", re.compile(
        r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|"
        r"client[_-]?secret|private[_-]?token)\b\s*[:=]\s*['\"]?[^'\"\s,;}{]{6,}"
    )),
    ("cloudflare", re.compile(r"(?i)cloudflare[_-]?(?:api[_-]?token|key)\s*[:=]\s*\S{6,}")),
]

_MIN_ENV_SECRET_LEN = 8


def _literal(value: str) -> str:
    return re.escape(value)


def build_env_patterns(env_values: dict[str, str]) -> list[re.Pattern[str]]:
    """Valorile .env (și ale env-ului moștenit) devin ele însele secretes de redactat."""
    patterns = []
    for key, value in (env_values or {}).items():
        if not value or len(value) < _MIN_ENV_SECRET_LEN:
            continue
        if any(part in key.upper() for part in ("PATH", "HOME", "USER", "SHELL", "TERM", "LANG", "TZ")):
            continue  # valori de mediu benigne, nu secret — altfel distrugem contextul
        patterns.append(re.compile(_literal(value)))
    return patterns


def redact_text(text: str, env_values: dict[str, str] | None = None) -> tuple[str, list[str]]:
    """Întoarce (text_redactat, lista de ce s-a găsit). Nu modifică nimic local."""
    found: list[str] = []
    out = text
    for name, pattern in PATTERNS:
        def _hit(match: re.Match[str], _name: str = name) -> str:
            if _name not in found:
                found.append(_name)
            return REDACTED
        out = pattern.sub(_hit, out)
    for pattern in build_env_patterns(env_values or {}):
        if pattern.search(out):
            found.append("env_value")
            out = pattern.sub(REDACTED, out)
    return out, found


def redact_payload(payload: dict, env_values: dict[str, str] | None = None) -> tuple[dict, list[str]]:
    """Copie redactată a payload-ului (mesaje + unelte). Cheile structurale rămân intacte."""
    found: list[str] = []
    out = dict(payload)
    new_messages = []
    for message in out.get("messages") or []:
        message = dict(message)
        content = message.get("content")
        if isinstance(content, str):
            clean, hits = redact_text(content, env_values)
            found.extend(hits)
            message["content"] = clean
        elif isinstance(content, list):
            clean_parts = []
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    clean, hits = redact_text(part["text"], env_values)
                    found.extend(hits)
                    part = {**part, "text": clean}
                clean_parts.append(part)
            message["content"] = clean_parts
        new_messages.append(message)
    if new_messages:
        out["messages"] = new_messages
    if out.get("tools"):
        clean, hits = redact_text(_json_dumps(out["tools"]), env_values)
        if hits:
            found.extend(hits)
            try:
                import json

                out["tools"] = json.loads(clean)  # type: ignore[assignment]
            except ValueError:
                out.pop("tools", None)  # unelte corupte de redactare → nu pleacă deloc
    return out, sorted(set(found))


def _json_dumps(value) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)
