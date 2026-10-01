# Decizie în așteptarea proprietarului: arhiva SEO („20 zile → 404")

Data: 2026-10-01 · Context: audit Codex (P0.3) + analize ZCode din aceeași zi · **Necesită decizia lui Alexandru — nu se execută fără „da"**

## Problema

`ARTICLE_TTL_DAYS = 20` (config.py) → articolele ies din `output/` după ~20 de zile → URL-urile
indexate de Google ajung la 404. E o decizie de capacitate (plafonul Workers Free de 20.000
fișiere/versiune; live 1 oct: 17.122 fișiere, marjă ~2.900). Arhiva veche NU se pierde: istoricul
git o păstrează integral, iar `tools/arhiva.py` o poate reconstrui — dar Google nu vede git.

## Variante

### A. Păstrăm fereastra de 20 de zile (status quo) — RECOMANDAT ACUM
- Cost: zero. Sitemap-ul scoate URL-urile expirate, Google le deindexează natural.
- Pentru un agregator de știri, articolele >3 săptămâni au trafic organic negligible;
  conținutul util dinspre primării/anunțuri intră prin pipeline-ul dedicat, nu prin arhivă.
- Ce ar infirma alegerea: Search Console cu trafic organic semnificativ pe articole de 20+ zile
  (de verificat lunar, 5 minute).
- Reversibilitate: trecerea la varianta B rămâne posibilă oricând; nimic nu se pierde între timp
  (git ține tot).

### B. Arhivă permanentă în două straturi (propunerea Codex)
- Strat activ (0–20 zile) pe Workers Assets + strat arhivă (>20 zile) pe R2 (sau alt origin).
- Cost real: activare R2 pe cont (serviciu nou), worker routing pe `if active / if archive`,
  un proces de export lunar (~3.000 articole/lună × ~10 KB HTML ≈ 30 MB/lună — R2 Free 10 GB
  acoperă ani întregi), plus mentenanță. Efort estimat: 1-2 zile de lucru agent + decizie de
  activare serviciu.
- Beneficiu: zero 404-uri pe URL-uri indexate; „arhivă permanentă" ca promisiune de produs.
- Când ar merita: dacă IZZ își asumă poziționarea „arhivă de presă locală" ca produs, nu doar
  flux de știri.

### C. Intermediar (fără servicii noi): redirecționarea articolelor expirate
- La expirare, în loc de 404: 301 spre pagina de categorie/căutare. Cod: moderat în render.
- Dezavantaj: 301-urile spre conținut diferit sunt semnal SEO slab; Cloudflare limită ~2.000
  reguli statice (acum: 40 folosite). Nu recomand decât dacă Search Console arată durere reală.

## Recomandarea mea

**A acum + verificare lunară în Search Console** (poate fi automatizată cândva printr-un task
programat care întreabă numărul de impresii pe URL-uri expirate). B rămâne pe foaia de drum ca
proiect dedicat, declanșat de un motiv de business, nu de teama teoretică de 404.

## Ce am făcut diseară din restul auditului Codex (fără decizii așteptate)

- ✅ P0.1 — probă atomică izz.ro în deploy (best-effort, `90e089173b`)
- ✅ P0.2 — smoke-live imediat după deploy, cron rămas watchdog (`1292beff94`)
- ✅ P1.4 — deploy-failover.yml din infra/**, cu sonde și alertă (`0dc5ccd040`); repo = live
  (semnături identice, zero drift)
- ✅ P1.6 — gardă buget redirecte în deploy (live: 40 redirecturi active / plafon ~2.000)
- ⏸️ NU pornit diseară (motive): arhiva R2 (decizia de mai sus); monitor extern 1-5 min
  (serviciu extern nou — cere acordul tău, propus UptimeRobot gratuit); Monitor Local
  multi-ingest (proiect mare, pe foaia de drum); detector CSP-bootstrap (valoare mică acum);
  human gate (decizie editorială, implicit-off e alegere documentată în cod).
