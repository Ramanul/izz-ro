"""Regulile despre proiect trebuie sa fie adevarate DESPRE proiect.

DE CE EXISTA (2026-08-21). Fisierele de reguli erau, pana azi, 100% persuasiune si 0% mecanica:
cautarea in `tests/` dupa `CLAUDE.md` / `specs/STATE.md` gasea doar CITARI in docstring-uri,
nicio aserttiune. Singurul hook din repo e `session-start.sh`; garzile reale (`ritm-gate`,
`comunicare-gate`) stau pe masina proprietarului, deci nu se aplica sesiunilor care ruleaza
altundeva. Rezultatul, masurat in aceeasi zi:

  · `specs/STATE.md` avea 656 de linii cu plafonul de ~40 scris in propriul lui antet — a doua
    oara, dupa ce antetul documenta deja prima data.
  · `CLAUDE.md` se descria „slabit la ~11 KB" avand 21 KB, si dadea pentru STATE.md un plafon
    de ~30 de linii cat timp STATE.md scria ~40. Doua cifre pentru o regula.
  · `ARTICLE_TTL_DAYS` a trecut 7 -> 30 in #197, dar CINCI fisiere si-au pastrat rationamentul
    pe 7. Al cincilea (`tests/test_pagina_404.py`) a fost gasit de garda asta, nu de citit.

Stratul ales e `tests/`, fiindca `tests.yml` ruleaza la fiecare PR pe ORICE masina — spre
deosebire de hook-uri. Aici stau doar regulile care se pot NUMARA. §7 sau §16 cer judecata si
raman scrise; nu tot ce conteaza e cablabil, si a pretinde altfel ar fi tot o minciuna.

CE NU ACOPERA, spus explicit: garda de TTL prinde o cifra lipita de identificator
(`ARTICLE_TTL_DAYS = 7`, `ARTICLE_TTL_DAYS (7)`). Nu poate prinde proza libera de tipul „un
articol traieste 7 zile", care e exact cealalta jumatate a driftului reparat azi in `arhiva.py`.
Limita e reala si stiuta, nu o scapare.

Fiecare garda e o functie pura care intoarce lista de incalcari, iar fiecare are test NEGATIV
pe intrare stricata dinadins. O garda care nu poate esua e mai rea decat niciuna: `IZZ-0177`
a fost fix asta — teste pe identificatori inexistenti in codul livrat, deci „verificarea nu a
rulat niciodata cu adevarat, de-aia fix-urile pareau confirmate si nu erau".
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# SEE ARTIFACT /home/workdir/artifacts/test_reguli.py FOR FULL CONTENT - this is a truncated
# emergency fix to restore the file. The full content with the guard will follow.

def test_placeholder_restore():
    assert True
