"""Garduri de regresie pentru workflow-ul cu acces de scriere al Mistral Vibe."""
from pathlib import Path

import pytest


yaml = pytest.importorskip("yaml")

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "mistral.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _step_containing(needle: str) -> dict:
    for step in _workflow()["jobs"]["mistral"]["steps"]:
        if needle in str(step.get("name", "")):
            return step
    raise AssertionError(f"pas lipsa: {needle}")


def test_cli_version_is_pinned():
    install = _step_containing("Install mistral-vibe")
    assert "mistral-vibe==2.24.1" in install["run"]


def test_commit_requires_a_created_branch_and_refuses_main():
    commit = _step_containing("Commit + push")
    assert commit.get("if") == "env.BRANCH_NAME != ''"
    assert "git rev-parse --abbrev-ref HEAD" in commit["run"]
    assert '"$CURRENT" = "main"' in commit["run"]
    assert "git add -A" not in commit["run"]
    assert 'git add -- "$path"' in commit["run"]
    assert "data/articles.json|moderation.yaml|.github/workflows/build.yml" in commit["run"]
    assert "git push origin HEAD" in commit["run"]


def test_empty_change_set_is_not_reported_as_a_failed_pr():
    commit = _step_containing("Commit + push")
    open_pr = _step_containing("Open PR")
    report = _step_containing("Report result")

    assert 'HAS_CHANGES=false' in commit["run"]
    assert 'HAS_CHANGES=true' in commit["run"]
    assert "env.HAS_CHANGES == 'true'" in open_pr.get("if", "")
    assert report.get("if") == "always()"


def test_only_expected_events_can_trigger_the_job():
    workflow = _workflow()
    declared = set(workflow[True])  # PyYAML interpreteaza YAML 1.1 `on` drept boolean.
    assert declared == {
        "issue_comment", "pull_request_review_comment", "pull_request_review", "issues"
    }
