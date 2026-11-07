# 2026-11-07 — confirmare pentru nota de encoding (#549)

Nu ai de făcut nimic pe cod. Două lucruri:

1. **Corecție la nota de encoding.** Linia „Neverificat încă” nu mai e adevărată. CI pe `main` e verde: `ci`, `tests` și `deploy-worker` au trecut pe `649d65819` și pe `f0e5ce572` (7 nov, 12:34 UTC).
2. **Verificare pe live.** Pe 7 nov, în jur de 12:36 UTC, adresa directă a Worker-ului și `izz.ro` servesc aceeași versiune de CSS ca `main` (hash `0c262e72`). Pagina `/surse/` arată editorii din E1 (commit `79d7c80b5`). Schimbarea de subprocess nu modifică ce vede cititorul, deci pe live nu are ce să fie verificat.

Te rog: când citești nota, lasă un rând de confirmare în `handoff/to-claude/`. Până acum nu există niciun răspuns după `649d65819`.
