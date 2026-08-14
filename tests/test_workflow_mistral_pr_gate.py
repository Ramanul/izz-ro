"""Pasul „Open PR" din .github/workflows/mistral.yml nu are voie sa ruleze fara push.

Incidentul concret (rularea 31788232683, 14 aug, issue #175): `vibe` a rulat curat si a decis,
corect, ca n-are ce schimba. Pasul de commit a intrat pe ramura `git diff --cached --quiet`,
a scris un `::notice::` si a facut `exit 0` — care iese din PAS, nu din job. Ramura nu a ajuns
niciodata pe remote, dar `Open PR` avea `if: env.BRANCH_NAME != ''`, deci a rulat oricum:

    pull request create failed: GraphQL: ... No commits between main and
    mistral/issue-175-1786699753, Head ref must be a branch (createPullRequest)

Rezultatul vazut de om: job rosu si „❌ @mistralai a eșuat" pe issue, pentru un rezultat care
era de fapt un succes fara modificari.

Testul NU se uita doar la textul din `if` — RULEAZA scriptul pasului de commit intr-un repo
git temporar, cu remote local, si verifica ce scrie el in `$GITHUB_ENV` pe ambele cai. Asa
prinde si o rescriere a scriptului care pastreaza `if`-ul, dar pierde steagul.
"""
import subprocess
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "mistral.yml"


def _pasi() -> list[dict]:
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return wf["jobs"]["mistral"]["steps"]


def _pas(nume: str) -> dict:
    for p in _pasi():
        if p.get("name") == nume:
            return p
    raise AssertionError(f"pasul {nume!r} nu mai exista in mistral.yml")


def _ruleaza_pasul_de_commit(tmp_path: Path, *, cu_modificari: bool) -> dict[str, str]:
    """Executa scriptul REAL al pasului si intoarce ce a scris in $GITHUB_ENV."""
    remote = tmp_path / "remote.git"
    lucru = tmp_path / "lucru"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(lucru)], check=True)
    for cheie, val in (("user.name", "mistral[bot]"), ("user.email", "mistral@example.invalid")):
        subprocess.run(["git", "-C", str(lucru), "config", cheie, val], check=True)
    (lucru / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(lucru), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(lucru), "commit", "-qm", "seed"], check=True)
    subprocess.run(["git", "-C", str(lucru), "push", "-q", "origin", "HEAD"], check=True)
    subprocess.run(["git", "-C", str(lucru), "checkout", "-qb", "mistral/issue-1-000"], check=True)

    if cu_modificari:
        (lucru / "nou.txt").write_text("ceva\n", encoding="utf-8")

    github_env = tmp_path / "github_env"
    github_env.touch()
    rezultat = subprocess.run(
        ["bash", "-c", _pas("Commit + push changes")["run"]],
        cwd=lucru,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(tmp_path),
             "GITHUB_ENV": str(github_env)},
        capture_output=True,
        text=True,
    )
    assert rezultat.returncode == 0, rezultat.stderr
    return dict(
        linie.split("=", 1)
        for linie in github_env.read_text(encoding="utf-8").splitlines()
        if "=" in linie
    )


def test_fara_modificari_steagul_e_false(tmp_path):
    assert _ruleaza_pasul_de_commit(tmp_path, cu_modificari=False).get("PUSHED") == "false"


def test_cu_modificari_steagul_e_true(tmp_path):
    assert _ruleaza_pasul_de_commit(tmp_path, cu_modificari=True).get("PUSHED") == "true"


def test_open_pr_cere_si_ramura_si_push():
    """Ambele conditii sunt necesare: ramura se creeaza inainte de `vibe`, deci `BRANCH_NAME`
    e setat si atunci cand nu s-a pushat nimic."""
    conditie = _pas("Open PR (from issue/comment)")["if"]
    assert "env.BRANCH_NAME != ''" in conditie
    assert "env.PUSHED == 'true'" in conditie


def test_raportul_nu_anunta_succes_cand_nu_s_a_schimbat_nimic():
    """`job.status` e „success" si cand vibe n-a schimbat nimic — mesajul „vezi commit-urile /
    PR-ul de mai sus" ar trimite omul dupa ceva ce nu exista."""
    raport = _pas("Report result on issue/PR")["run"]
    assert 'PUSHED:-' in raport, "raportul nu mai distinge cazul fara modificari"
    assert raport.index('PUSHED:-') < raport.index("a terminat"), (
        "ramura fara modificari trebuie verificata INAINTEA celei de succes cu commit-uri"
    )
