import json

from generator import config, render

# Toate variabilele din care `_write_build_metadata` compune amprenta release-ului.
# Tinute intr-un singur loc: un nume adaugat in render.py si uitat aici lasa testul
# "randat local" sa citeasca mediul real al masinii si sa treaca din intamplare.
ENV_RELEASE = (
    "WORKERS_CI_COMMIT_SHA", "CF_PAGES_COMMIT_SHA", "GITHUB_SHA", "BUILD_COMMIT_SHA",
    "WORKERS_CI_BRANCH", "CF_PAGES_BRANCH", "GITHUB_REF_NAME", "BUILD_BRANCH",
)


def test_build_metadata_uses_cloudflare_commit_and_branch(monkeypatch, tmp_path):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    for key in ENV_RELEASE:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CF_PAGES_COMMIT_SHA", "a" * 40)
    monkeypatch.setenv("CF_PAGES_BRANCH", "main")

    render._write_build_metadata(article_count=17)

    data = json.loads((tmp_path / "build.json").read_text(encoding="utf-8"))
    assert data["commit"] == "a" * 40
    assert data["branch"] == "main"
    assert data["article_count"] == 17
    assert data["generated_at"].endswith("+00:00")


def test_build_metadata_uses_workers_builds_commit_and_branch(monkeypatch, tmp_path):
    """Workers Builds injecteaza ALTE nume decat Pages -- vezi #211.

    Fara asta, dupa migrare `commit` ramane "local" la fiecare build de productie si
    `tools/verify_release.py` compara SHA-ul asteptat cu literalul "local": sonda nu
    mai poate deveni verde, iar daca ar deveni, ar fi verde pe nimic.
    """
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    for key in ENV_RELEASE:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("WORKERS_CI_COMMIT_SHA", "b" * 40)
    monkeypatch.setenv("WORKERS_CI_BRANCH", "main")

    render._write_build_metadata(article_count=5)

    data = json.loads((tmp_path / "build.json").read_text(encoding="utf-8"))
    assert data["commit"] == "b" * 40
    assert data["branch"] == "main"


def test_build_metadata_prefers_workers_over_pages_during_migration(monkeypatch, tmp_path):
    """Cazul NEGATIV: cu ambele familii setate, castiga gazda curenta (Workers).

    O garda care nu poate pica e mai rea decat niciuna (IZZ-0177): fara asertiunea
    asta, o ordine inversata a lanturilor ar trece neobservata cat timp doar una din
    variabile e setata in CI.
    """
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    for key in ENV_RELEASE:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CF_PAGES_COMMIT_SHA", "a" * 40)
    monkeypatch.setenv("CF_PAGES_BRANCH", "pages")
    monkeypatch.setenv("WORKERS_CI_COMMIT_SHA", "b" * 40)
    monkeypatch.setenv("WORKERS_CI_BRANCH", "workers")

    render._write_build_metadata(article_count=1)

    data = json.loads((tmp_path / "build.json").read_text(encoding="utf-8"))
    assert data["commit"] == "b" * 40, "Workers Builds e gazda curenta, are prioritate"
    assert data["branch"] == "workers"


def test_build_metadata_is_explicit_when_rendered_locally(monkeypatch, tmp_path):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    for key in ENV_RELEASE:
        monkeypatch.delenv(key, raising=False)

    render._write_build_metadata(article_count=0)

    data = json.loads((tmp_path / "build.json").read_text(encoding="utf-8"))
    assert data["commit"] == "local"
    assert data["branch"] == "local"
    assert data["article_count"] == 0


def test_homepage_card_limit_is_small_and_explicit():
    assert config.HOME_CARDS_PER_CATEGORY == 4
