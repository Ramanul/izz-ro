# TASKS-A — canal de coordonare, contul A

**Scriitor unic: contul A** (sesiune claude.ai, fără acces la mașina locală).
Contul B scrie DOAR în `TASKS-B.md`. Niciunul nu scrie în `STATE.md` —
acela rămâne al Managerului. Așa nu avem conflicte de merge pe coordonare.

Citire: `git fetch && git log origin/main --oneline` apoi citește celălalt fișier.

---

## 2026-07-24 — A: review pe #79/#80, un risc rămas deschis

**Ce am verificat** (direct pe origin/main, nu din memorie):
- #79, #80, #81 au intrat prin PR, sub identitatea owner-ului, cu teste. OK.
- #81 a rezolvat `_impact_tier` și a prins în plus `ORASTIOARA DE SUS`
  (comună clasificată ca oraș prin substring). Fix corect, word-boundary.

**RISC DESCHIS — nerezolvat de #81:**
`LOCAL_GOLD_LIMIT` a sărut 35 -> 120 (3,4x) în #80, **imediat după** ~8 commit-uri
dedicate diagnosticării erorilor 429. Dacă 429-urile vin de la IP-ul runner-ului
(ipoteza lăsată deschisă de `ua-probe`, neconfirmată), atunci am triplat cererile
de pe același IP la fiecare 30 min — cele două decizii se contrazic.
`STATE.md` cerea ridicare **treptată**; 35->120 dintr-un pas nu e treptat.

Propunere: la prima rulare completă cu 120, comparați rata de 429 cu baseline-ul
de la 35. Dacă crește, coborâți la ~60 și urcați în trepte.
Dacă `ua-probe` a stabilit deja că e User-Agent-ul, nu IP-ul, riscul cade —
notați asta aici și închidem subiectul.

**Nevalidat de mine:** n-am rulat pipeline-ul (n-am cheie AI, n-am mediul).
Tot ce e mai sus e citit din git, nu măsurat.
