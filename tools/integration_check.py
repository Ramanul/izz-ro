#!/usr/bin/env python3
"""Poarta locală de integrare pentru IZZ.ro.

Rulează validările necesare după schimbări în ingestie, geo-atribuire, datasetul hărții
sau randare. Scriptul nu descarcă surse și nu cheamă provideri AI; este repetabil pe
un checkout local cu dependențele proiectului instalate.

Utilizare:
    python tools/integration_check.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "static" / "harta-stiri" / "data" / "map.json"


class IntegrationFailure(RuntimeError):
    """Eroare de contract între componentele proiectului."""


def run(label: str, *command: str) -> None:
    print(f"\n=== {label} ===", flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False, timeout=1800)
    if completed.returncode:
        joined = " ".join(command)
        raise IntegrationFailure(f"{label} a eșuat (cod {completed.returncode}): {joined}")


def article_by_slug(articles: list[dict], slug: str) -> dict | None:
    """Articolul de regresie, sau `None` daca a iesit din fereastra de continut.

    Recuperat cu o modificare fata de `7749e192`: acolo absenta arunca `IntegrationFailure`.
    Articolele de regresie sunt insa continut real, care se roteste — dupa cateva zile ies din
    dataset si poarta ar fi picat pe o „regresie" inexistenta. Un esec fals repetat antreneaza
    exact reflexul de a ignora poarta. Absenta se RAPORTEAZA, nu se pedepseste.
    """
    return next((item for item in articles if item.get("slug") == slug), None)


def _verifica_atribuire(articles: list[dict], slug: str, judet: str, localitate: str, eticheta: str) -> bool:
    """`True` daca s-a putut verifica; `False` daca articolul nu mai e in dataset."""
    article = article_by_slug(articles, slug)
    if article is None:
        print(f"   (sarit) {eticheta}: articolul a ieșit din fereastra de conținut")
        return False
    if (article.get("county"), article.get("locality")) != (judet, localitate):
        raise IntegrationFailure(
            f"Regresie {eticheta}: articolul trebuie să fie în {judet} / {localitate}, "
            f"nu {article.get('county')} / {article.get('locality')}."
        )
    print(f"   OK {eticheta}: {judet} / {localitate}")
    return True


def assert_geo_regressions() -> None:
    print("\n=== regresii geo publicate ===", flush=True)
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    articles = data.get("articles") or []

    # Ploiesti e cazul care a justificat regula „anuntul oficial ramane in judetul institutiei"
    # din `build_harta_data.py`: teaserul zice „FC Petrolul Ploiesti si Rapid Bucuresti", iar
    # inainte de 2026-08-20 articolul ajungea pe harta in BUCURESTI.
    _verifica_atribuire(
        articles,
        "restrictii-de-circulatie-in-zona-stadionului-ilie-oana-vineri-21-august-2026",
        "PRAHOVA", "PLOIESTI", "Ploiești / stadionul Ilie Oană",
    )
    _verifica_atribuire(
        articles,
        "furnizarea-apei-potabile-va-fi-oprita-temporar-in-otelu-rosu",
        "CARAS-SEVERIN", "OTELU ROSU", "Oțelu Roșu",
    )

    too_long = [
        item for item in articles
        if item.get("source", "").startswith("pl_") and len((item.get("title") or "").strip()) > 110
    ]
    if too_long:
        raise IntegrationFailure(
            f"{len(too_long)} titluri oficiale din hartă depășesc limita de afișare de 110 caractere."
        )

    print("OK: atribuirile de regresie și titlurile oficiale din hartă respectă contractele.")


def _map_without_generated_at(data: dict) -> dict:
    """Normalizează metadata volatilă înainte de comparația datasetului generat."""
    normalized = dict(data)
    normalized.pop("generated_at", None)
    return normalized


def assert_regenerated_map_is_committed() -> None:
    print("\n=== dataset hartă sincronizat ===", flush=True)
    path = str(MAP_PATH.relative_to(ROOT))
    committed = json.loads(
        subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=ROOT, text=True)
    )
    regenerated = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    if _map_without_generated_at(committed) != _map_without_generated_at(regenerated):
        raise IntegrationFailure(
            "Regenerarea hărții a schimbat conținutul semantic al map.json. "
            "Revizuiți și comiteți datasetul regenerat."
        )
    print("OK: map.json este sincronizat semantic; timestampul de generare este volatil.")


def main() -> int:
    original_map = MAP_PATH.read_text(encoding="utf-8")
    map_regenerated = False
    try:
        run("lint", sys.executable, "-m", "ruff", "check", ".")
        run("teste unitare și de regresie", sys.executable, "-m", "pytest", "tests/", "-q")
        run("regenerare dataset hartă", sys.executable, "tools/build_harta_data.py")
        map_regenerated = True
        assert_regenerated_map_is_committed()
        assert_geo_regressions()
        run("randare statică", sys.executable, "-m", "generator.main", "--render-only")
        run("integritate HTML", sys.executable, "tools/html_check.py")
        run("calitate editorială", sys.executable, "tools/qa_check.py")
    except IntegrationFailure as error:
        print(f"\nFAIL: {error}", file=sys.stderr)
        return 1
    finally:
        # Generatorul actual înscrie un timestamp la fiecare rulare. Când conținutul
        # semantic a trecut comparația, restaurăm exact versiunea inițială ca scriptul
        # de verificare să nu lase un checkout curat modificat doar de metadata volatilă.
        if (
            map_regenerated
            and _map_without_generated_at(json.loads(original_map))
            == _map_without_generated_at(json.loads(MAP_PATH.read_text(encoding="utf-8")))
        ):
            MAP_PATH.write_text(original_map, encoding="utf-8")

    print("\nOK: toate controalele de integrare au trecut.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
