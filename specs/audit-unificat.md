# Auditul unificat — verificare, corectare, aplicare (2026-09-11)

> Sursa auditata: `IZZ_ro_AUDIT_UNIFICAT_20260905.xlsx` (9 foi, 36 de mecanisme, 23 de
> categorii strategice, 12 actiuni in PLAN UNIFICAT), primit de la proprietar.
> Rezultatul aplicarii traieste in `specs/audit-unificat.tsv` + `tools/audit_matrice.py`,
> nu in acest document: documentul explica DE CE arata asa.

## 1. Ce s-a verificat mecanic

Toate cifrele de mai jos sunt recalculate din datele registrului, nu citite din foaia
`Dashboard`. Comanda: `python tools/audit_matrice.py raport`.

| Agregat | Excel 2026-09-05 | Registru 2026-09-11 | De ce difera |
|---|---|---|---|
| mecanisme inventariate | 36 | 44 | 7 lipseau din inventar (§3) + garda de redirectare (§2.1b) |
| mecanisme vii | 36 (implicit) | 43 | unul era fantoma (§2.1) |
| cu autoritate de blocare | 19 „reala" | 18 `efectiva` + 6 `conditionata` | autoritatea conditionata de branch protection e separata, nu declarata reala |
| fara autoritate | 17 | 19 | reclasificare + mecanismele adaugate |
| bypass documentat | 8 | 7 | #22 feedcheck a primit cron, deci nu mai e ocolibil prin omisiune |
| eroziune > 2 | 1 | **0** | acel 1 era chiar fantoma |
| risc >= 3 | 5 | 2 | #17, #34 remediate intre timp; #32 inexistent |

Baza de verificare, rulata local pe 2026-09-11 cu istoric complet: `python -m pytest tests/ -q`
-> **1586 trecute**, 1 sarit, 8 xfailed; `python -m ruff check .` -> curat; `git status` gol si
dupa suita. (La deschiderea lucrarii erau 1542; diferenta sunt testele adaugate aici.)

## 2. Trei defecte structurale ale registrului Excel

### 2.1 Un mecanism inventariat care nu exista — FANTOMA (#32)

Randul 32, `ramanul-triage-blockers`, era inventariat ca:
`Tip: Audit` · `Locatie: .github/workflows/` · `Poate bloca: Da` · `Autoritate reala: Da` ·
`Fail-closed` · `Stare: Activa CU EROZIUNE DOCUMENTATA` · `Nivel eroziune: 4` (cel mai mare
din tot inventarul) · `Prioritate: Ridicata`. Din el deriva **actiunea P0 #5** din PLAN
UNIFICAT.

Masurat pe 2026-09-11:

- `e1c8fbe2515cb86881ae4ae0f40d1146324a818c` este capul unei **ramuri**, nu un workflow.
- `git merge-base --is-ancestor e1c8fbe2… origin/main` -> **fals**: nemergeuit in `main`.
- `git show --stat` -> **un singur commit, 14 linii in `generator/util.py`**.
- Nu exista niciun workflow de triaj in `.github/workflows/`.
- `specs/registru.tsv` il consemneaza deja `masurat-fals` in **IZZ-0266, pe 2026-09-02** —
  cu trei zile INAINTE de audit — cu mentiunea explicita „NEmergeuit (main intact, verificat)".

Deci auditul a inventariat o ramura respinsa drept poarta activa fail-closed pe productie,
i-a atribuit cea mai mare eroziune din matrice si a derivat din ea un P0. Consecintele
cascadeaza in agregatele publicate: `Eroziune > 2: 1` era chiar fantoma (real pe sistemul
viu: **0**), iar din cele doua randuri P0 unul nu exista.

Ironia utila: README-ul auditului isi scrie singur principiul incalcat — *„Existenta unui
tool nu echivaleaza cu autoritate de blocare"* — iar foaia `Failure modes` isi defineste
singura modul de esec produs: *„Stale rule: regula ramane, dar nu mai corespunde sistemului"*.

Ce SUPRAVIETUIESTE din P0 #5: actiunea („logheaza articolele aruncate si motivele") era
utila si a fost implementata — `generator/jurnal_triage.py` -> `data/triage_log.jsonl`.
Premisa era gresita, remediul nu. Nu se sterge nimic retroactiv din cauza asta.

Randul ramane in registru marcat `stare=absent`, deliberat: sters, s-ar reinventaria la
urmatorul audit. `tests/test_audit_matrice.py::test_fantoma_ramane_consemnata_ca_absenta`
il tine acolo.

### 2.1b A DOUA fantoma, gasita aplicand auditul — de data asta pe un control de securitate

Aceeasi clasa de defect ca §2.1, dar in cod, nu in registru. `guard._gazda_interna` isi
declara explicit golul si numeste compensarea:

> „un domeniu public care REZOLVA catre o adresa interna trece de aici; ala e treaba lui
> `fetch._deschizator_sigur`, care verifica fiecare salt de redirectare, acolo unde cererea
> chiar se face."

Masurat pe 2026-09-11: `grep -rn deschizator_sigur` peste tot repo-ul returna **o singura
aparitie — chiar citarea de mai sus**. Functia nu exista. Nu exista nici opener, nici
`HTTPRedirectHandler`, nici `allow_redirects`, nici `max_redirect` in `fetch.py`, iar
`urllib.request.urlopen` urmeaza redirecturile IMPLICIT.

Calea reala, nu ipotetica: `_parse_sitemap_news` valideaza cu `url_ostil` `<loc>`-ul unui
sitemap TERT (fetch.py, pasul de garda), apoi `_fetch_meta_description` cere acel URL si ii
pune raspunsul in `description`, adica in corpusul publicabil.

Demonstrat in ambele directii pe un server local (`tests/test_fetch_redirect_ssrf.py`):

| Stare | `_fetch_meta_description(url care redirecteaza spre intern)` |
|---|---|
| inainte (opener implicit) | `'continut-intern-care-nu-trebuie-sa-iasa'` |
| dupa (`_deschide` + `_RedirectVerificat`) | `''` |

Inchis prin implementarea chiar a functiei pe care documentatia o promitea. Trei decizii de
proiectare, fiecare cu motivul ei:

- **Cusatura e `fetch._deschide`, nu `urllib.request.install_opener`.** A doua varianta ar fi
  cerut zero modificari in teste, dar muta starea GLOBALA a lui `urllib` pentru tot procesul,
  inclusiv pentru `tools/`. Am platit 11 editari mecanice in teste ca sa nu las o capcana.
- **Garda apara SALTURILE, nu cererea initiala.** URL-ul de plecare ramane treaba lui
  `url_ostil`, aplicat de apelant; dublarea verificarii ar fi mutat-o in locul gresit.
- **Un test de invariant** (`test_nicio_iesire_in_retea_nu_ocoleste_cusatura`) pica daca reapare
  un `urllib.request.urlopen(` direct in `fetch.py` — altfel golul se reintroduce exact cum a
  aparut prima data.

O premisa verificata, nu presupusa: `url_ostil` respinge orice nu incepe cu `http`/`https`,
deci un `Location: /pagina` relativ ar fi omorat tacit orice sursa care redirecteaza relativ.
Masurat: `urllib` rezolva `Location` fata de URL-ul cererii INAINTE de `redirect_request`,
deci garda vede mereu un URL absolut. Premisa e tinuta sub test.

**Ce NU rezolva, spus pe fata:** ramane verificare lexicala. Un domeniu public al carui DNS
rezolva DIRECT catre o adresa interna, fara redirect, trece in continuare — pentru asta ar
trebui validare la nivel de socket. S-a inchis golul „redirect catre intern", nu clasa SSRF.

### 2.2 Agregate nereproductibile

Registrul contine **zero formule** (verificat cu `openpyxl`, `data_only=False`). Fiecare
cifra din `Dashboard` e o constanta scrisa de mana. Doua consecinte masurate:

- Coloana `Prioritate` contine si `Ridicata`, si `Ridicată`. Numarate ca valori distincte,
  deci `Dashboard: Prioritate P0 = 1` cand randurile marcate erau **2** (#2 si #32).
- `Fail-open / fail-closed` are o a treia valoare, `Fail-closed la hold` (#11), intr-un camp
  altfel binar.

Remediu: vocabularele din `tools/audit_matrice.py` sunt **inchise si ASCII fara diacritice**,
exact ca sa nu mai poata exista doua ortografii ale aceleiasi valori; agregatele se calculeaza.

### 2.3 Coloane care nu masoara nimic

Din 66 de coloane, **25 sunt complet goale pe toate cele 36 de randuri** — intre ele TOATE
cele opt sub-coloane de eroziune (`Eroziune – acoperire` … `Eroziune – orbire`), adica exact
axa pe care foaia `Eroziune` o defineste in detaliu. Scorul agregat `Nivel eroziune (0–5)`
e introdus direct, fara derivare din cele opt dimensiuni, deci nefalsificabil.

Doua perechi de coloane sunt identice pe toate randurile:

- `Poate bloca?` ≡ `Autoritate reala?` — coloana care trebuia sa prinda exact distinctia din
  README (*„Un monitor nu este automat un gate"*) nu prinde nimic.
- `Risc (0–5)` ≡ `Scor risc reconciliat (0–5)` — „reconcilierea" nu a schimbat niciun scor.

Si patru contradictii directe intre coloane si propriul verdict textual: #25 CodeQL, #26
Semgrep, #30 mutanti/echivalenta, #34 containment erau marcate `Autoritate reala: Da` SI
`Fail-open`, iar verdictul lor spunea in text contrariul („devine autoritate reala numai
daca este required in CI/branch protection").

Remediu: `autoritate` are acum trei valori — `efectiva` / `conditionata` / `niciuna` — iar
`conditionata` cere numirea conditiei. Verificatorul respinge `autoritate=efectiva` cu
`esec=deschis`, si `poate_bloca=nu` cu autoritate nenula.

## 3. Fapte schimbate intre 2026-09-05 si 2026-09-11

Auditul a fost corect la data lui pe punctele de mai jos; nu mai este.

| Mecanism | Ce spunea auditul | Ce e masurat acum |
|---|---|---|
| #17 audit titluri | „POST-publicare; publicarea de azi nu e blocata de auditul de maine" | `tools/qa_check.py` importa `title_quality_audit` si pica build-ul pe contract; QA e blocant inainte de commit |
| #22 feedcheck | „Manual; surse moarte tacute" | are cron zilnic (`17 5 * * *`) |
| #34 containment | „Procedural, nu sandbox/hard deny; P0" | `PreToolUse` hard deny real pe control-plane, cu teste |
| #2 grounding | „Nu exista dovada mecanica; ramane P0" | `tools/grounding_gate.py` blocheaza citat inventat si cifra straina, fail-closed, inainte de QA si commit |
| teste | „168 teste locale" | 1542 trecute, 3 sarite, 8 xfailed (2026-09-11) |

Sapte mecanisme lipseau cu totul din inventar si au fost adaugate: #37 grounding gate,
#38 detectie de tacere, #39 jurnal de triaj, #40 exercitiu de recuperare, #41 garda de
integritate a regulilor, #42 garda de PR nelistat, #43 jurnal de takedown.

## 4. Starea celor 12 actiuni din PLAN UNIFICAT

| # | Actiune | Stare | Dovada |
|---|---|---|---|
| 1 | AI grounding blocant | **inchis pe subsetul determinist** | `tools/grounding_gate.py`, pas dedicat in `build.yml` |
| 2 | Ordine QA + required checks | **inchis in repo; partial pe platforma** | ordinea `pipeline -> grounding -> QA -> commit` e in `build.yml`; `main` e `protected: true`, dar LISTA de required checks nu e citibila din sesiune |
| 3 | Moderation fail-closed | **inchis** | `ModerationConfigCorrupt` pe config lipsa/invalid; `tests/test_moderation_config.py` |
| 4 | Containment agenti | **inchis** | `.claude/hooks/deny_protected_edits.py` + `tests/test_agent_protected_edits.py` |
| 5 | Triage blockers | **fara obiect** (premisa fantoma, §2.1); partea utila livrata | `generator/jurnal_triage.py` |
| 6 | Stale release detection | **inchis** | `EXPECTED_COMMIT` + `tools/verify_release.py`; `detectie-tacere.yml` orar |
| 7 | Determinism render | **partial** | garda pe sursa exista; comparatia comportamentala 2x (~50 min) nu incape in CI si ramane manuala |
| 8 | Takedown / similaritate text | **partial** | takedown-urile se aplica pe orice cale; pragul de similaritate nu are corpus de calibrare |
| 9 | Feedcheck + corpus adversarial | **inchis pe redirect/SSRF** | feedcheck programat; `tests/test_fetch_redirect_ssrf.py` (18 cazuri) + garda implementata (§2.1b). Poisoning de continut ramane in `guard._CORPUS_OSTIL` |
| 10 | Observabilitate + tacere | **inchis** | `detectie-tacere.yml` + `tools/detectie_tacere.py` |
| 11 | Edge/WAF drift | **partial** | `specs/snapshot-edge.md` exista ca baseline; comparatia e manuala |
| 12 | Recovery drill | **inchis in repo** | `.github/workflows/recovery-drill.yml`; exercitiul operational ramane la proprietar |

## 5. Ce ramane deschis, si de ce nu l-am inchis

- **Lista de required status checks pe `main`.** Limita e declarata prin experimentele care au
  esuat, nu din impresie (2026-09-11, autentificat ca `Ramanul`, `GET /user` da 200):

  | Comanda | Rezultat |
  |---|---|
  | `GET /repos/Ramanul/izz-ro/branches/main/protection` | **403** `Resource not accessible by integration` |
  | `GET …/branches/main/protection/required_status_checks` | **403** idem |
  | GraphQL `branchProtectionRules` | **403** — GraphQL e blocat pentru sesiunile Claude Code |
  | `GET /repos/Ramanul/izz-ro/rulesets` | **200 — lista goala** |

  Ultima linie restrange necunoscutul: nu exista niciun ruleset, deci `protected: true` de pe
  `main` vine din branch protection CLASICA, iar ce nu se poate citi e continutul EI.
  De asta #25/#26/#27/#29/#41/#42 sunt `autoritate=conditionata` cu conditia numita, nu
  `efectiva`. Se inchide cu o citire in Settings → Branches de catre proprietar, sau cu un
  token care are `administration:read`; nu cu un commit.
- **Corpusul de calibrare pentru similaritate** (#43) — cere date reale, nu cod; un prag ghicit
  ar incalca disciplina IZZ-0168. Corpusul adversarial de ingestie (#9) e inchis pe axa
  redirect/SSRF (§2.1b); pe axa de poisoning editorial ramane `guard._CORPUS_OSTIL`.
- **Comparatia de determinism 2x** (#30) — ~50 de minute, in afara CI prin constructie.
- **Driftul edge** (#11) — configuratia Cloudflare nu e in repo; ramane control de platforma.

## 6. De ce registrul a devenit TSV + unealta, si nu un Excel mai bun

Defectul comun al §2.1, §2.2 si §2.3 nu e neglijenta, e forma: un registru care nu e legat
mecanic de repo descrie, dupa cateva zile, un sistem care nu mai exista — si nimic nu semnaleaza
momentul in care a incetat sa fie adevarat. Un Excel corectat ar fi fost corect exact o zi.

`tools/audit_matrice.py verifica` iese != 0 daca o dovada nu mai exista pe disc, daca apare o
valoare in afara vocabularului, daca un mecanism e declarat fara autoritate dar cu drept de
blocare, sau daca ceva absent isi pastreaza scorurile. Ruleaza in `pytest`, deci in CI, deci
in fiecare PR — fara atingerea `.github/workflows/`, care e cale de control-plane protejata.

Limita, spusa pe fata: unealta verifica DECLARATIILE registrului si existenta dovezilor. NU
verifica daca un mecanism chiar isi face treaba — aia ramane treaba testelor lui.

## 7. Efect secundar masurat: garda de control-plane refuza citiri

Auditul s-a lovit de propriul obiect. Din primele sase comenzi ale sesiunii, **trei au fost
refuzate de `deny_protected_edits.py`, toate read-only** — `ls`, `grep` si `sed -n` pe
directorul de workflow-uri — pentru ca predicatul garzii e o conjunctie pe toata comanda
(*token protejat oriunde* SI *indicator de scriere oriunde*), iar `2>&1` contine `>`.

Reparat (IZZ-0353) doar clasa care se poate repara **fara sa deschida o ocolire**:
duplicarile de descriptor si `/dev/null` se sterg inainte de cautare, pentru ca nu pot
numi un fisier. Sase teste negative fixeaza granita.

Doua clase de fals pozitiv RAMAN, deliberat:

- **Scriere reala intr-un fisier neprotejat, langa mentiunea unui token protejat** —
  `cat > specs/x.tsv` intr-o comanda care contine textul `moderation.yaml`. Repararea cere
  asocierea redirectului cu tinta lui, iar asta introduce o ocolire verificabila:
  `F=moderation.yaml; echo x > "$F"` ar trece, fiindca tinta sintactica e `"$F"`.
- **Caractere de redirect in text de argument** — sageata `->` intr-o explicatie, sau
  `<noreply@…>` in trailerul unui mesaj de commit. Par inofensive, nu sunt: in bash
  `echo a -> b` chiar scrie in `b`, fiindca `-` inchide cuvantul precedent si `>` deschide
  un redirect. Garda nu parcurge heredoc-uri, deci nu poate sti ca textul e doar text.

Pentru ambele, calea corecta e cea pe care garda o impune deja: scrierea prin unealta de
fisiere, unde calea tinta e neambigua si verificarea e exacta. Costul e o reformulare
ocazionala; alternativa ar fi fost o gaura reala in planul de control.

## 8. A doua constatare din aplicare: testele poluau jurnalul de triaj

Mecanismul #39 (`data/triage_log.jsonl`) e observabilitatea nascuta din actiunea P0 #5 —
locul unde se masoara over-blocking-ul la ingestie. Aplicand registrul s-a vazut ca el
crestea la fiecare rulare LOCALA a suitei.

Masurat prin experiment, nu dedus: 32 de linii inainte de `pytest tests/test_slug_stabil.py`,
34 dupa. Delta exact 2, doua randuri identice pe aceeasi secunda.

Cauza: fixture-ul `ruleaza` cheama `main.run(dry_run=False)` cu `state.STATE_PATH`
redirectionat in `tmp_path`, dar `jurnal_triage.cale()` si-o ia din `config.ROOT`, care nu e
redirectionat. `build.yml` comite fisierul, deci poluarea ajungea in repo. Nu strica niciun
test — se strecoara tocmai in datele pe care se ia decizia editoriala.

Reparat pe clasa, nu pe caz (IZZ-0354): fixture-ul redirectioneaza si jurnalul, iar
`tests/conftest.py` primeste o gardă autouse care, dupa FIECARE test, verifica amprenta
fisierelor de stare comisa (`triage_log`, `takedown_log`, `articles.json`, `feed_cache.json`)
si numeste testul vinovat. Verificata in ambele directii: cu bugul repus, garda da ERROR pe
exact testul care polua; cu fixul, suita trece si arborele de lucru ramane curat.
