# 2026-11-07 — encoding la apelurile subprocess, pe main

Merged: #549 (commit `2c1aa33`, 7 nov, 12:11 UTC). Pe Windows, `text=True` fără `encoding` decodează ieșirea cu pagina de cod locală (cp1252), iar diacriticele ies stricate. Acum cele 32 de apeluri din `tests/` și `tools/` cer `encoding="utf-8", errors="replace"`.

De știut înainte să atingi aceleași suprafețe:
- `generator/` nu are apeluri `subprocess` fără encoding; pipeline-ul nu e atins.
- Cele 20 de apeluri fără mod text (bytes sau `text` dintr-o variabilă) au rămas neschimbate: adăugarea `encoding` acolo ridică `ValueError`.
- Verificat local pe Windows: 3140 trecute, 5 sărite, 8 cunoscute ca pică (`xfail`). Neverificat încă: verificările automate pe `main` după merge.
