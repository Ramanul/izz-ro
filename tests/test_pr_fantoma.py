"""Garda: PR-uri deja pe main nu stau în STATE.md ## Open fără adnotarea (merged).

Port din #236 / #244. Necesită fetch-depth: 0 în tests.yml.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PR_REF = re.compile(r"#(\d+)")
PR_MERGED_ANNOT = re.compile(r"#(\d+)[^#\n]*\bmerged\b", re.I)
MERGE_COMMIT = re.compile(r"Merge pull request #(\d+)")


def sectiune_open(state_md: str) -> str:
    m = re.search(r"^## Open\s*$", state_md, re.M)
    if not m:
        return ""
    rest = state_md[m.end():]
    m2 = re.search(r"^## ", rest, re.M)
    return rest[:m2.start()] if m2 else rest


def pr_uri_mentionate(bloc: str) -> set[int]:
    return {int(n) for n in PR_REF.findall(bloc)}


def pr_uri_adnotate_merged(bloc: str) -> set[int]:
    return {int(n) for n in PR_MERGED_ANNOT.findall(bloc)}


def pr_uri_mergeuite_pe_main() -> set[int]:
    """PR-uri cu commit de merge pe main.

    În CI (checkout pe branch-ul PR) ref-ul local `main` lipsește adesea.
    Încercăm origin/main, apoi main, apoi --all.
    """
    for args in (
        ["git", "log", "origin/main", "--grep=Merge pull request #", "--format=%s"],
        ["git", "log", "main", "--grep=Merge pull request #", "--format=%s"],
        ["git", "log", "--all", "--grep=Merge pull request #", "--format=%s"],
    ):
        iesire = subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, check=False,
        )
        if iesire.returncode == 0:
            return {int(n) for n in MERGE_COMMIT.findall(iesire.stdout)}
    raise RuntimeError(
        "nu pot citi istoricul de merge — verifică fetch-depth: 0 în tests.yml"
    )


def incalcari_pr_fantoma(state_md: str, mergeuite: set[int]) -> list[str]:
    bloc = sectiune_open(state_md)
    if not bloc:
        return ["STATE.md nu are secțiunea ## Open"]
    fantome = sorted((pr_uri_mentionate(bloc) & mergeuite) - pr_uri_adnotate_merged(bloc))
    return [
        f"#{n} e deja merge-uit pe main, dar stă în ## Open fără adnotarea (merged)"
        for n in fantome
    ]


def test_niciun_pr_fantoma_in_state_open():
    state = (ROOT / "specs" / "STATE.md").read_text(encoding="utf-8")
    incalcari = incalcari_pr_fantoma(state, pr_uri_mergeuite_pe_main())
    assert not incalcari, "\n".join(incalcari)


def test_garda_pr_fantoma_pica_pe_pr_deja_mergeuit():
    state = "## Open\n\n- ceva despre #99\n\n## Standing\n"
    assert incalcari_pr_fantoma(state, {99})


def test_garda_pr_fantoma_accepta_adnotarea_merged():
    state = "## Open\n\n- **F4 (#99, merged).**\n\n## Standing\n"
    assert not incalcari_pr_fantoma(state, {99})


def test_garda_pr_fantoma_ignora_pr_neintegrat():
    state = "## Open\n\n- PR-uri deschise: #50 #60\n\n## Standing\n"
    assert not incalcari_pr_fantoma(state, {99})
