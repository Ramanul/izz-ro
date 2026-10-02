# SPEC — audit-gratuit: scanere externe gratuite pe site-ul LIVE

**Data:** 2026-10-02 · **Cerere proprietar:** „implementează în pași logici absolut tot ce e
full gratuit" (după analiza din aceeași zi: site-uri de analiză gratuite potrivite izz.ro).

## Scop

Complementul post-deploy pe care `specs/masuratori-frontend.md` îl cere explicit: măsurătorile
locale (`tools/audit.sh` — Lighthouse + pa11y pe `output/` local) rămân poarta de dinainte de
commit; aici se adaugă privirea pe LIVE, săptămânal, cu rapoarte.

## Premise verificate înainte de implementare

- scanerele alese sunt keyless sau cu cheie gratuită fără facturare: PSI (25.000 apeluri/zi cu
  cheie gratuită), Mozilla Observatory v2, SSL Labs (rate limit), W3C Nu + CSS (volum mic,
  politicos — esantion ≤11 URL), lychee (binar în Actions), IndexNow — [FAPT, docurile lor]
- esantionul e mic prin construcție (≤10 articole + home) ca să nu încălcheme validatorii publici
- origin de rezervă dacă anti-bot-ul blochează sondele din datacenter: `ORIGIN_DEFAULT` în
  `tools/audit_gratuit.py`, la fel ca sondele existente
- contractul din `specs/resurse-gratuite.md` §6 („nicio resursă gratuită fără nevoie + ce se
  dezactivează"): UN singur workflow nou, UN singur script, zero dashboard-uri noi; rapoartele
  cad în artifact 90 zile + job summary, nu în servicii externe
- **IndexNow există deja** — `generator/config.py:459` (cheie), `render.py:1104` (fișier root),
  `tools/indexnow_submit.py` (anunță URL-urile noi la fiecare rulare): NU se dublează; prima
  propunere din analiza de dimineață era o duplicare, retrasă

## Autorizat (fișiere atinse)

1. `.github/workflows/audit-gratuit.yml` — nou — program luni 03:23 UTC + manual
2. `tools/audit_gratuit.py` — nou — 8 subcomenzi, doar biblioteca standard
3. `tests/test_audit_gratuit.py` — nou — gardă workflow ↔ script + anti-duplicare IndexNow
4. `specs/STATE.md`, `.gitignore`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` — minim

## Ce NU acoperă

- calitatea conținutului (există `editorial-quality.yml`), uptime (watchdog + `monitor.yml`),
  Search Console (pasul manual lunar al proprietarului), analytics (GA4 + Clarity + CF Web Analytics)
- baseline-ul live se stabilește la PRIMA rulare; comparațiile încep de a doua

## Verificare

- local: `python -m ruff check tools/audit_gratuit.py` + `python -m pytest tests/test_audit_gratuit.py -q`
- local: fiecare subcomandă rulată contra LIVE/origin, JSON-uri în `reports/` (dovadă în PR)
- CI: `python -m pytest tests/ -q` verde pe PR; prima rulare programată confirmă pe LIVE
- *În ce condiții greșesc:* dacă PSI/Observatory/SSL Labs schimbă API-urile sau limitele, sau
  dacă repo-ul devine privat — raportul va arăta ESUAT/SARIT pe sursa respectivă, nu tăcere.
