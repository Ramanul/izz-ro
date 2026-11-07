# Audit de încredere și remediere — 7 noiembrie 2026

## Spec de lucru

**Cerut:** verificarea pe GitHub a semnalelor unui audit extern despre izz.ro și remedierea problemelor dovedite.
**Bază:** `cc5bb0c556d316bae0321ee4a374f2d82d02537b`; ramură de lucru `arena/7ea08ce6-izz-ro`.
**Non-obiective:** deploy, modificarea DNS/WAF, rescrierea stării editoriale, inventarea unei corecții istorice fără dovadă examinată, reauditarea generală SEO deja acoperită în repo.

### Ipoteze și criterii de acceptare

1. Un răspuns AI model B fără titlu/rezumat valid nu trebuie să publice titlul brut sau „Detalii pe sursa.”; itemul se amână, iar intrarea rămâne nemodificată. Teste pe câmp lipsă, gol și neșir.
2. O sinteză care inversează explicit rezultatul unui penalty față de o sursă univocă este o problemă blocantă de grounding. Sursa ambiguă, două penalty-uri distincte și formulările fără obiectul explicit nu se blochează heuristic. Teste pozitive/negative și integrare în raportul care alimentează defer-ul.
3. Prima pagină nu prezintă date invalide/lipsă drept proaspete și nu numește „azi” o listă de știri mai vechi. Când nu există știri proaspete, spune aceasta explicit. Manifestul public expune data celui mai nou articol, separat de data randării; sondele o verifică.
4. Jurnalul de corecții se derivă din catalogul aprobat, inclusiv retrageri, nu dintr-o propoziție statică. Catalogul gol rămâne gol; textul aprobat este autoescaped. Teste fără înregistrări și cu înregistrări sintetice.
5. Paginile publice nu promit înscrierea la un newsletter inexistent. Politica descrie doar colectarea activă; istoricul declarațiilor nu se rescrie.
6. Sonda publică distinge conținut verificat, challenge anti-bot, eroare HTTP și rețea necunoscută. 403 fără dovadă de challenge nu este „site sănătos”, 500 nu este bot-block benign, iar 200 cu interstițiu nu este conținut. Monitorul și verificarea post-deploy folosesc aceeași clasificare. Nu se schimbă cronurile și nu se activează workflow-uri dezactivate de proprietar.
7. Identitatea editorială deja publică și codul public sunt ușor de găsit din subsol; nu se inventează date despre operator.

**Verificare:** teste de regresie, ruff, suita Python, teste Node, randare completă din stare necălătorită prin fixture, QA, HTML/accessibility static, inspectare browser dacă mediul permite. Stările „reparat în cod”, „verificat local” și „confirmat pe live” se raportează separat.

## Rezultate și limite (7 noiembrie 2026)

### Cele patru semnale externe

| Semnal | Ce s-a putut verifica | Verdict |
|---|---|---|
| `izz.ro` răspunde 403 | Sandbox-ul nu are egress TLS către `izz.ro`/Worker (`SSL_ERROR_SYSCALL`); jobul GitHub `deploy-worker` 42374044743 are toate etapele verzi, inclusiv verificarea release-ului pe Worker. Monitorul, detecția-tăcere și smoke-live sunt `disabled_manually` din 30 octombrie. | 403-ul live nu e reprodus aici. Codul nu mai tratează orice non-200 drept benign: challenge dovedit = neconcludent, 5xx/conținut înghețat = eroare. WAF/DNS nu au fost atinse. |
| Operator neconfirmat | `content/pages/despre.md` numește operatorul: Alexandru Nicolae Stanciu, persoană fizică, România, `contact@izz.ro`. Subsolul trimite acum la `/despre/` și la codul public. | Identitate editorială publică și găsită din footer; identitatea civilă nu a fost verificată independent. |
| Index oprit la 10 iulie 2026 | `main` a avansat la `b14a1077` (7 nov, 13:17 UTC); build 42374907337 = success; mirror `ramanul.github.io` are `build.json` generat 7 nov 13:18, 6360 articole. Starea locală are publicații până la 7 nov 06:06 UTC. | Ipoteza „repo/publicare oprite în iulie” e falsă pe GitHub. Indexul Google și conținutul servit live nu au fost măsurate din acest mediu. |
| Contradicție Mbappé/penalty/Maroc | În copia istorică `5ab99d68` (`.arena/articles-2026-07-10.json`), itemii 159/161/168 (C) spun „ratat”, itemul 148 (B) spune „transformat”. În starea curentă nu mai există acești itemi; subarborele `sport` al oglinzii (10.772 intrări, netrunchiat) nu conține paginile de penalty Mbappé căutate. | Contradicție internă istorică confirmată. Adevărul extern (TVR/Opta) nu a fost verificat; nu s-a inventat o corecție editorială. Garda nouă blochează inversarea explicită față de o sursă univocă. |

### Remedieri aplicate

- `process_single`: titlu/rezumat lipsă, gol sau neșir → item amânat, fără titlu brut și fără „Detalii pe sursa.”.
- `home_fresh` + `render`: dată lipsă/invalidă/viitoare nu e proaspătă; hero/briefing/selecție editorială doar din fereastra de 72h; empty-state explicit; `build.json` expune `latest_article`.
- `verifica_sinteza` + `raport_copiere`: `rezultat_penalty_inversat` blocant în gate/defer, conservator la surse ambigue și penalty-uri distincte.
- `tools/public_probe.py`: clasificare comună (conținut / challenge / eroare / necunoscut) + prospețimea articolului; folosită de `monitor.yml`, `deploy-worker.yml` și `verify_release.py`.
- Jurnalul de corecții se randează din catalogul aprobat (`templates/_corrections_journal.html`), inclusiv retrageri; catalogul gol rămâne gol, textul e autoescaped.
- Contact/privacy: promisiunile newsletter/Brevo/double opt-in au fost înlocuite cu RSS și absența formularului; footer cu operator și cod public.
- Frontend: separatorul de card folosește culoare AA (135 erori pa11y → 0 local); `tools/audit.sh` și workflow-ul de comparație nu mai aleg paginarea `/ai/2/` (noindex) ca articol de referință.

### Verificare locală

- `ruff check .` = curat; `pytest -q` = **3186 passed, 4 skipped, 8 xfailed**; `node --test infra/*.test.mjs` = 7/7.
- Render complet din stare: 11.099 fișiere, 6496 articole în manifest; QA = OK (avertisment preexistent: 17% duplicate eveniment); `html_check` = 7679 pagini, 0 legături/active/alt-uri rupte.
- Browser local (Chromium 133, Lighthouse 13.4.1, pa11y 10.0.0): home Perf 91 / A11y 100 / Best 100 / SEO 100; articol Perf 97 / A11y 100 / Best 100 / SEO 100; pa11y home = 0 erori. Mobile/desktop: footer operator + cod public, fără formular newsletter, jurnal de corecții gol, fără erori de consolă.
- CI `editorial-frontend-audit` pe PR #555 (3 rulări/revizie): before home 91/100/100/100, articol 96/100/100/100, pa11y 135; after primul head home 91/96/100/100, articol 97/96/100/100, pa11y 0. Regresia A11y 100→96 era `link-in-text-block` pe linkurile noi din footer; sublinierea explicită din `.foot-note a` o repară (local 100/100).
- `public_probe` pe output-ul local = OK, ultimul articol 7 nov 06:06 UTC.

### Limite și pași rămași

- Nu există dovadă live din acest sandbox pentru 403, indexare Google sau challenge-ul real; nu s-au modificat WAF/DNS/cron și nu s-au reactivat workflow-uri dezactivate de proprietar.
- Comparația frontend before/after pe 3 rulări rămâne de citit din CI la PR; cifrele de mai sus sunt locale, pe un singur esantion.
- O corecție istorică Mbappé cere dovadă externă examinată și decizie editorială; până atunci contradicția rămâne documentată, nu „rezolvată” prin rescrierea stării.
