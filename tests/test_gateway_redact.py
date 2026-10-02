"""Scenariul 12 din spec: redactarea secretelor din contextul transmis (nu local)."""
from __future__ import annotations

from gateway_helpers import build_full  # noqa: F401 (asigură sys.path)
from ai_gateway.redact import redact_payload, redact_text

SECRET_ENV = {"TEST_PASSWORD": "parola-mea-super-secreta-99",
              "CLAUDE_PATH": "/usr/local/bin"}


def test_chei_api_detectate():
    cases = {
        "openai_key": "cheia e sk-proj-ABCDEFGHIJKLMNOPQRSTU1234 folosită ieri",
        "anthropic_key": "sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAA",
        "github_token": "token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ12",
        "github_fine": "github_pat_ABCDEFGHIJKLMNOPQRSTUVWX",
        "aws_access": "AKIAIOSFODNN7EXAMPLE în config",
        "google_key": "AIzaSyA1234567890abcdefghijklmnopqrstuv",
        "slack_token": "xoxb-123456789012-abcdef",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----",
        "database_url": "postgres://user:pass@db.example.com:5432/prod",
        "bearer": "Authorization: Bearer abcdef1234567890abcdef1234567890",
        "kv_assign": "password: 'parola12345'",
        "cloudflare": "cloudflare_api_token = abcdefgh12345678",
    }
    for name, text in cases.items():
        out, found = redact_text(text, SECRET_ENV)
        assert out != text, f"tiparul {name} n-a prins: {text}"
        assert "[REDACTED]" in out and name in found


def test_valori_din_env_detectate():
    out, found = redact_text("conectează-te cu parola-mea-super-secreta-99 la server",
                             SECRET_ENV)
    assert "parola-mea-super-secreta-99" not in out and "env_value" in found
    # valori benigne de mediu NU se redactează (altfel ar distruge contextul)
    out2, _ = redact_text("rulează din /usr/local/bin", SECRET_ENV)
    assert "/usr/local/bin" in out2


def test_redactare_payload_pasteaza_structura():
    payload = {
        "model": "groq/llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Ești un asistent de cod."},
            {"role": "user", "content": "folosește cheia ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ12 "
                                        "și parola-mea-super-secreta-99"},
            {"role": "user", "content": [{"type": "text",
                                          "text": "DATABASE_URL=postgres://user:pass"
                                                  "@db.example.com:5432/prod"}]},
        ],
        "tools": [{"type": "function", "function": {"name": "edit_file",
                                                    "description": "editează un fișier"}}],
    }
    out, found = redact_payload(payload, SECRET_ENV)
    joined = str(out)
    assert "ghp_" not in joined and "parola-mea-super-secreta-99" not in joined
    assert "postgres://" not in joined
    assert "Ești un asistent de cod." in out["messages"][0]["content"]  # restul intact
    assert out["messages"][1]["content"].count("[REDACTED]") == 2
    assert out["tools"][0]["function"]["name"] == "edit_file"  # uneltele rămân funcționale
    assert {"github_token", "env_value", "database_url"} <= set(found)


def test_payload_original_nu_e_modificat():
    payload = {"messages": [{"role": "user", "content": "cheie sk-proj-ABCDEFGHIJKLMNOPQRSTU1"}]}
    original = str(payload)
    redact_payload(payload, {})
    assert str(payload) == original  # redacția atinge DOAR contextul trimis, nu fișierele
