"""Contractul puntii Arena <-> Battle Mode (`tools/battle_bridge.py`).

De ce merita testat si nu doar citit: canalul e transportul dintre doua sesiuni care nu se
pot vedea altfel (Arena n-are browser si n-are retea; ZCode are browser, dar nu citeste
gandul). Un contract incalcat aici nu da eroare vizibila — da un raspuns alipit la
intrebarea gresita, iar cine-l citeste mai tarziu nu are cum sa stie. De aceea testele apar
pe cazurile care ar produce tacut continut valabil-dar-fals: reply dublu, vot neasumat,
tura fara prompt, text urias turnat intr-o linie de JSONL.

Testele n-au fixturi: isi fac singure directorul temporar, deci fisierul se poate rula si
fara pytest (vezi blocul `__main__`).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "battle_bridge.py"
sys.path.insert(0, str(ROOT))

from tools import battle_bridge as bb  # noqa: E402


def _log_path() -> Path:
    return Path(tempfile.mkdtemp(prefix="battle-bridge-")) / "turns.jsonl"


def _run(log: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--log", str(log), *args],
        capture_output=True, text=True, check=False, cwd=ROOT,
    )


def _lines(log: Path) -> list[dict]:
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def _answer(log: Path, turn: int = 1, **kwargs) -> subprocess.CompletedProcess:
    args = ["reply", "--turn", str(turn), "--summary", kwargs.pop("summary", "rezumat")]
    for key, value in kwargs.items():
        flag = f"--{key.replace('_', '-')}"
        args += [flag] if value is True else [flag, str(value)]
    return _run(log, *args)


def test_prompt_then_reply_closes_the_turn():
    log = _log_path()
    assert _run(log, "prompt", "--text", "Intrebarea unu").returncode == 0
    assert json.loads(_run(log, "next").stdout)["turn"] == 1
    assert _answer(log, status="ok", a_text="de la A", b_text="de la B").returncode == 0
    assert _run(log, "next").stdout.strip() == "NOTHING"
    assert _run(log, "validate").returncode == 0


def test_next_on_missing_log_is_not_an_error():
    # Pompa ruleaza `next` inainte sa existe fisierul: un canal gol nu e o eroare, e tacere.
    result = _run(_log_path(), "next")
    assert result.returncode == 0 and result.stdout.strip() == "NOTHING"


def test_second_reply_needs_correction_and_leaves_file_untouched():
    log = _log_path()
    _run(log, "prompt", "--text", "intrebare")
    _answer(log, status="ok", a_text="A", b_text="B")
    before = log.read_text(encoding="utf-8")

    result = _answer(log, status="ok", a_text="A2", b_text="B2")
    assert result.returncode == 2 and "correction" in result.stderr
    assert log.read_text(encoding="utf-8") == before


def test_correction_wins_and_stays_valid():
    log = _log_path()
    _run(log, "prompt", "--text", "intrebare")
    _answer(log, status="ok", a_text="prima varianta A", b_text="prima varianta B")
    assert _answer(log, status="ok", a_text="varianta corectata A", b_text="B",
                   correction=True).returncode == 0
    assert _run(log, "validate").returncode == 0
    show = _run(log, "show", "--turn", "1", "--full").stdout
    assert "varianta corectata A" in show and "prima varianta A" not in show


def test_vote_requires_the_named_approval():
    log = _log_path()
    _run(log, "prompt", "--text", "intrebare")
    assert _answer(log, status="ok", a_text="A", b_text="B", vote="a").returncode == 2
    assert _answer(log, status="blocked", summary="doar vot", vote="a", approved_by="zcode").returncode == 2
    assert _answer(log, status="ok", a_text="A", b_text="B", vote="a",
                   approved_by="alexandru").returncode == 0
    assert _lines(log)[-1]["vote_approved_by"] == "alexandru"


def test_blocked_status_carries_no_model_text():
    # Un perete (reCAPTCHA, ToS, selector lipsa) se consemneaza ca atare; daca i se ataseaza
    # text, cineva va citi mai tarziu un raspuns care nu exista.
    log = _log_path()
    _run(log, "prompt", "--text", "intrebare")
    assert _answer(log, status="blocked", a_text="ceva", summary="perete").returncode == 2
    assert _answer(log, status="blocked", summary="perete reCAPTCHA",
                   notes="de reluat manual").returncode == 0


def test_reply_without_summary_is_rejected():
    log = _log_path()
    _run(log, "prompt", "--text", "intrebare")
    result = _run(log, "reply", "--turn", "1", "--status", "ok", "--a-text", "A", "--b-text", "B")
    assert result.returncode == 2 and "summary" in result.stderr.lower()


def test_reply_for_a_turn_without_prompt_is_rejected():
    log = _log_path()
    assert _answer(log, turn=3, status="blocked", summary="x").returncode == 2
    assert not log.exists()


def test_long_text_goes_to_captures_and_keeps_the_line_readable():
    log = _log_path()
    _run(log, "prompt", "--text", "intrebare")
    big = Path(tempfile.mkdtemp(prefix="battle-text-")) / "a.txt"
    big.write_text("X" * (bb.MAX_INLINE + 500), encoding="utf-8")
    assert _answer(log, status="ok", a_file=str(big), b_text="scurt").returncode == 0

    record = _lines(log)[-1]
    slot_a = record["models"][0]
    assert slot_a["text_ref"] == "tura-001-A.md"
    assert len(slot_a["text"]) < bb.MAX_INLINE
    assert "trunchiat" in slot_a["text"]
    captured = (log.parent / "captures" / slot_a["text_ref"]).read_text(encoding="utf-8")
    assert captured == "X" * (bb.MAX_INLINE + 500)
    assert _run(log, "validate").returncode == 0


def test_append_only_never_rewrites_the_prefix():
    log = _log_path()
    _run(log, "prompt", "--text", "unu")
    first = log.read_text(encoding="utf-8")
    _run(log, "prompt", "--text", "doi")
    assert log.read_text(encoding="utf-8").startswith(first)


def test_validate_catches_a_log_broken_by_hand():
    log = _log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        "\n".join(
            [
                json.dumps({"kind": "prompt", "turn": 1, "from": "arena", "ts": "2026-10-06T10:00:00Z", "text": "a"}),
                # ts fara Z (naiv) si reply fara prompt inainte
                json.dumps({"kind": "reply", "turn": 4, "from": "zcode", "ts": "2026-10-06T10:01:00", "status": "ok", "models": [{"slot": "A", "name": None, "text": "x", "text_ref": None}], "summary": "s", "vote": None}),
                # al doilea prompt sare peste numerotare
                json.dumps({"kind": "prompt", "turn": 5, "from": "arena", "ts": "2026-10-06T10:02:00Z", "text": "b"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    result = _run(log, "validate")
    assert result.returncode == 2
    assert "ts nu e UTC" in result.stdout
    assert "fara prompt inainte" in result.stdout
    assert "asteptat 2" in result.stdout


def test_tool_never_talks_to_arena_and_only_to_loopback():
    # Contractul care conteaza dupa ce a aparut `duel`: singurul endpoint din tot fisierul
    # e gateway-ul LOCAL. Un `duel` care ar chema arena.ai ar fi automatizare de Serviciu
    # — interzisa de ToS (docs/canal-battle.md). Se verifica mecanic, fiindca "nu ating
    # arena.ai" e exact promisiunea care se pierde la prima refactorizare.
    source = SCRIPT.read_text(encoding="utf-8")
    assert "arena.ai" not in source
    urls = re.findall(r"https?://[^\s\"']+", source)
    assert urls == ["http://127.0.0.1:20129/v1/chat/completions"], urls


@contextmanager
def _fake_gateway(responder=None):
    """Un `ai_gateway` de carton, pe 127.0.0.1 cu port efemer.

    Exista ca testele duelului sa nu depinda de retea, de chei sau de provideri reali: se
    verifica CONTRACTUL (ce se trimite, ce se scrie in jurnal, cum arata un esec), nu
    calitatea raspunsului. Un test care ar chema Groq ar fi nedeterminist si ar consuma
    cota cuiva.
    """
    asked: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            payload["_authorization"] = self.headers.get("Authorization")
            asked.append(payload)
            model = str(payload.get("model", ""))
            if responder is not None:
                body, status = responder(payload)
            elif "broken" in model:
                body = json.dumps({"error": {"message": "NO_FREE_PROVIDER_AVAILABLE"}}).encode()
                status = 429
            else:
                body = json.dumps(
                    {"choices": [{"message": {"content": f"raspuns de la {model}"}}]}
                ).encode()
                status = 200
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # fara zgomot in output-ul testelor
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        endpoint = f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions"
        yield endpoint, asked
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _dead_endpoint() -> str:
    """Un port pe care nu asculta nimeni — chiar inchis, nu presupus liber."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    port = server.server_address[1]
    server.server_close()
    return f"http://127.0.0.1:{port}/v1/chat/completions"


def test_duel_asks_two_models_and_records_the_source():
    log = _log_path()
    _run(log, "prompt", "--text", "Aceeasi intrebare pentru amandoua")
    with _fake_gateway() as (endpoint, asked):
        result = _run(log, "duel", "--turn", "1", "--a", "groq/openai/gpt-oss-120b",
                      "--b", "gemini/gemini-2.5-flash", "--gateway", endpoint)
    assert result.returncode == 0, result.stderr
    assert [payload["model"] for payload in asked] == [
        "groq/openai/gpt-oss-120b", "gemini/gemini-2.5-flash",
    ]
    # acelasi text catre amandoua — altfel duelul nu compara nimic
    assert {payload["messages"][0]["content"] for payload in asked} == {
        "Aceeasi intrebare pentru amandoua"
    }
    assert all(payload["_authorization"] is None for payload in asked)
    record = _lines(log)[-1]
    assert record["status"] == "ok" and record["from"] == "gateway"
    assert [m["name"] for m in record["models"]] == [
        "groq/openai/gpt-oss-120b", "gemini/gemini-2.5-flash",
    ]
    assert "gpt-oss-120b" in record["models"][0]["text"]
    assert record["notes"] is None
    assert _run(log, "validate").returncode == 0


def test_duel_partial_when_one_model_fails():
    log = _log_path()
    _run(log, "prompt", "--text", "intrebare")
    with _fake_gateway() as (endpoint, _):
        result = _run(log, "duel", "--turn", "1", "--a", "groq/openai/gpt-oss-120b",
                      "--b", "gemini/broken-model", "--gateway", endpoint)
    assert result.returncode == 0
    record = _lines(log)[-1]
    assert record["status"] == "partial" and len(record["models"]) == 1
    assert "broken-model" in record["notes"] and "429" in record["notes"]
    assert _run(log, "validate").returncode == 0


def test_duel_blocked_when_gateway_is_not_running():
    # Gateway oprit = status `blocked`, fara text de model inventat. Contractul interzice
    # text atasat unui `blocked` exact ca sa nu ajunga in jurnal un raspuns care nu exista.
    log = _log_path()
    _run(log, "prompt", "--text", "intrebare")
    result = _run(log, "duel", "--turn", "1", "--gateway", _dead_endpoint())
    assert result.returncode == 0
    record = _lines(log)[-1]
    assert record["status"] == "blocked" and record["models"] == []
    assert "ai_gateway serve" in record["notes"]
    assert "summary" in record and record["summary"]
    assert _run(log, "validate").returncode == 0


def test_duel_needs_a_prompt_for_that_turn():
    log = _log_path()
    result = _run(log, "duel", "--turn", "4")
    assert result.returncode == 2 and "nu exista prompt" in result.stderr
    assert not log.exists()


def test_ask_gateway_refuses_a_response_without_content():
    # Un gateway care raspunde 200 dar fara `choices` nu e un raspuns: daca ar trece,
    # jurnalul ar primi text gol in loc de eroare.
    def no_choices(_payload):
        return json.dumps({"object": "list", "data": []}).encode(), 200

    with _fake_gateway(responder=no_choices) as (endpoint, _):
        try:
            bb.ask_gateway(endpoint, "groq/openai/gpt-oss-120b", "salut", timeout=10)
        except bb.BridgeError as exc:
            assert "choices" in str(exc)
        else:
            raise AssertionError("un raspuns fara choices trebuia sa fie eroare")


def test_ask_gateway_sends_the_model_the_question_and_the_token():
    with _fake_gateway() as (endpoint, asked):
        content = bb.ask_gateway(endpoint, "groq/openai/gpt-oss-120b", "salut", timeout=10,
                                 token="cheie-locala")
    assert content == "raspuns de la groq/openai/gpt-oss-120b"
    assert asked[0]["messages"] == [{"role": "user", "content": "salut"}]
    assert asked[0]["model"] == "groq/openai/gpt-oss-120b"
    assert asked[0]["_authorization"] == "Bearer cheie-locala"


if __name__ == "__main__":  # rulare fara pytest (sandbox fara pytest instalat)
    failures = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"PASS {name}")
            except Exception as exc:  # noqa: BLE001 - raportor minimal de sandbox
                failures += 1
                print(f"FAIL {name}: {exc!r}")
    sys.exit(1 if failures else 0)
