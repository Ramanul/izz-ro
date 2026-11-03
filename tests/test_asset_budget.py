"""Deployment limits apply to the complete tree, including its census report."""
import json
from pathlib import Path

import pytest

from tools import asset_budget


@pytest.mark.parametrize(
    ("count", "expected", "message"),
    [(17000, 0, None), (17001, 1, "safety budget exceeded"),
     (20000, 1, "safety budget exceeded"), (20001, 1, "provider ceiling exceeded")],
)
def test_complete_tree_limits(tmp_path, monkeypatch, capsys, count, expected, message):
    # Enumerate a real file repeatedly to exercise counting without creating 20k inodes.
    page = tmp_path / "article.html"
    page.write_text("full article", encoding="utf-8")
    monkeypatch.setattr(Path, "rglob", lambda self, pattern: iter([page] * (count - 1)))
    assert asset_budget.main(["--output-dir", str(tmp_path), "--enforce"]) == expected
    report = json.loads((tmp_path / "asset_budget.json").read_text(encoding="utf-8"))
    assert report["total"] == count
    if message:
        assert message in capsys.readouterr().out


def test_report_count_is_idempotent_and_includes_search(tmp_path):
    (tmp_path / "index.html").write_text("article", encoding="utf-8")
    search = tmp_path / "pagefind"
    search.mkdir()
    (search / "index.pf_fragment").write_bytes(b"search")
    for _ in range(2):
        assert asset_budget.main(["--output-dir", str(tmp_path), "--enforce"]) == 0
        report = json.loads((tmp_path / "asset_budget.json").read_text(encoding="utf-8"))
        assert report["total"] == 3
        assert sum(report["by_extension"].values()) == 3


@pytest.mark.parametrize("extra,expected", [(0, 0), (1, 1)])
def test_file_size_boundary(tmp_path, extra, expected):
    with (tmp_path / "long-article.html").open("wb") as stream:
        stream.truncate(asset_budget.MAX_FILE_BYTES + extra)
    assert asset_budget.main(["--output-dir", str(tmp_path), "--enforce"]) == expected
    # Telemetry remains nonblocking for callers that did not request enforcement.
    assert asset_budget.main(["--output-dir", str(tmp_path)]) == 0


def test_missing_output_cannot_deploy(tmp_path):
    missing = str(tmp_path / "missing")
    assert asset_budget.main(["--output-dir", missing, "--enforce"]) == 1
    assert asset_budget.main(["--output-dir", missing]) == 0


def test_deployment_guard_is_blocking_before_upload():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/deploy-worker.yml").read_text(encoding="utf-8")
    command = "python tools/asset_budget.py --output-dir output --enforce"
    assert command in workflow
    assert workflow.index("--render-only") < workflow.index(command) < workflow.index("wrangler@")
    assert "||" not in workflow.split(command, 1)[1].splitlines()[0]
    assert "environment: production" in workflow
