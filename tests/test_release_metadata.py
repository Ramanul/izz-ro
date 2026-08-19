import json

from generator import config, render


def test_build_metadata_uses_cloudflare_commit_and_branch(monkeypatch, tmp_path):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    monkeypatch.setenv("CF_PAGES_COMMIT_SHA", "a" * 40)
    monkeypatch.setenv("CF_PAGES_BRANCH", "main")

    render._write_build_metadata(article_count=17)

    data = json.loads((tmp_path / "build.json").read_text(encoding="utf-8"))
    assert data["commit"] == "a" * 40
    assert data["branch"] == "main"
    assert data["article_count"] == 17
    assert data["generated_at"].endswith("+00:00")


def test_build_metadata_is_explicit_when_rendered_locally(monkeypatch, tmp_path):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    for key in ("CF_PAGES_COMMIT_SHA", "GITHUB_SHA", "BUILD_COMMIT_SHA",
                "CF_PAGES_BRANCH", "GITHUB_REF_NAME", "BUILD_BRANCH"):
        monkeypatch.delenv(key, raising=False)

    render._write_build_metadata(article_count=0)

    data = json.loads((tmp_path / "build.json").read_text(encoding="utf-8"))
    assert data["commit"] == "local"
    assert data["branch"] == "local"
    assert data["article_count"] == 0


def test_homepage_card_limit_is_small_and_explicit():
    assert config.HOME_CARDS_PER_CATEGORY == 4
