---
name: Arena task
about: Sarcină pentru agentul Arena (executor pe branch, PR fără merge)
title: "[arena] "
labels: ""
---

<!-- Primul pas obligatoriu: citește docs/colaborare.md din repo și citează SHA-ul fișierului în răspuns. -->

## Obiectiv

<!-- Ce trebuie livrat, în 2-4 rânduri. -->

## Criterii de acceptanță

- [ ]

## Constrângeri

- Branch nou din `origin/main`; un task = un branch = un PR.
- Nu comita pe `main`, nu face merge, nu publica nimic.
- Actualizează `handoff/stare-lucrari.md` înainte de a cere review.
- După merge/close al PR-ului, sesiunea nu mai poate face push (event-based, zero grace) — nu porni lucru nou în ea.

## Verificare

<!-- Comenzile care demonstrează că merge (ex: python -m generator.main --dry-run). -->
