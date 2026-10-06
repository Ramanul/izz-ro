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
import subprocess
import sys
import tempfile
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


def test_tool_stays_offline():
    # Contractul de baza al puntii: nu atinge reteaua. Se verifica mecanic, fiindca "nu
    # importa urllib" e exact genul de promisiune care se pierde la o refactorizare.
    source = SCRIPT.read_text(encoding="utf-8")
    for token in ("urllib", "socket", "http.client", "requests"):
        assert token not in source, token


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
