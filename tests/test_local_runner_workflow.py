"""Security contract for the manually gated local Windows runner workflow."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "local-pc-runner.yml"


def test_local_runner_is_manual_main_only_and_opt_in() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    trigger_section = text.split("\npermissions:", maxsplit=1)[0]
    top_level_triggers = re.findall(r"(?m)^  ([a-z_]+):$", trigger_section)

    assert top_level_triggers == ["workflow_dispatch"]
    assert "refs/heads/main" in text
    assert "confirm_local_execution" in text
    assert "LOCAL_RUNNER_ENABLED" in text
    assert "name: local-runner" in text
    assert "runs-on: [self-hosted, Windows, X64, izz-ro-local]" in text
    assert "permissions: {}" in text
    assert "persist-credentials: false" in text
    assert "ref: main" in text


def test_local_runner_has_only_fixed_tasks_and_ignores_proof_files() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    input_section = text.split("    inputs:", maxsplit=1)[1].split(
        "\npermissions:", maxsplit=1
    )[0]

    assert re.search(
        r"(?ms)^      task:\n.*?^        options:\n          - proof\n          - tests\n",
        input_section,
    )
    assert not re.search(r"(?m)^\s+(command|script|shell|path):", input_section)
    assert "handoff/.local-runner-proof/" in (ROOT / ".gitignore").read_text(
        encoding="utf-8"
    )
