# Predare — reguli de sinteză + marcaj AI · 17 august 2026

> Sesiune întreruptă la cerere. Preia altă sesiune. Documentul e scris ca să nu fie nevoie
> de contextul meu: tot ce trebuie știut e aici, inclusiv ce am lăsat neverificat.

## AVERTISMENT — starea reală

**Cod modificat în 5 fișiere. Suita de teste: 934 trec, 2 pică, 8 xfailed, în 644s.**

**Cele 2 picate NU au legătură cu modificările mele:** ambele din
`tests/test_workflow_mistral_pr_gate.py` (`test_cu_modificari_steagul_e_true`,
`test_fara_modificari_steagul_e_false`), pică pe o comandă `git rev-parse` care întoarce 1
într-un director temporar — `warning: You appear to have cloned an empty repository`. Subiectul
lor e o poartă de verificare pe GitHub, fără nicio atingere de șabloane sau randare.
**NU am verificat dacă picau și înainte de modificările mele** (sesiunea a fost oprită); cauza
e însă vizibil de mediu, nu de cod.

**Ce se poate afirma acum:** sintaxa șabloanelor e **validă** — testele de randare au rulat
printre cele 934 care trec, iar o eroare de Jinja le-ar fi picat. Etichetă: **verificat local**.

**Ce rămâne NEVERIFICAT:** că marcajul apare efectiv pe pagină, pe articolele potrivite. Niciun
test nu verifică `ai-mark` — e element nou, n-are cine să-l acopere. **De randat și privit.**

### Capcană de citit înainte de a te speria de trasee
Erorile afișează căi `D:\claude desktop\izz\...`, iar în locul liniilor de cod apare `???`.
**`D:\claude desktop` NU EXISTĂ** (verificat). Sunt resturi de cache de compilare (`__pycache__`)
rămase de pe vremea când proiectul stătea pe D:. Singura copie reală e pe C: și modificările sunt
în ea (verificat prin hash și prin căutarea `ai-mark` în fișier). Dacă deranjează, se șterg
folderele `__pycache__`.

---

## 1. Ce am modificat (nerulat)

| Fișier | Ce am făcut |
|---|---|
| `generator/render.py` | flag nou `a["ai_generat"]`, lângă `anunt_fara_corp` (~linia 540) |
| `templates/_card.html` | `<span class="ai-mark">Generat automat</span>` în `<div class="meta">` |
| `templates/index.html` | același marcaj pe lead-feature |
| `templates/article.html` | marcaj în `meta` + `<p class="ai-note">` cu dezvăluirea completă |
| `static/styles.css` | `.ai-mark` (după `.badge.c`) și `.ai-note` (după `.official-note`) |

**Fișiere noi, complet nerulate în producție:**
- `generator/verifica_sinteza.py` — verificări mecanice (citate / cifre / rezervă). Nu e apelat
  de nimeni încă. Import-ul nu e wired în `process.py`.
- `tools/masoara_sinteza.py` — **rulat, dar nu funcționează pentru scopul lui** (vezi §3.1).

**Documente:** `REGULI-SINTEZA.md` (8 secțiuni, normativ) — scris integral, e baza pentru tot.

### Logica marcajului, ca să nu fie rescrisă greșit
```python
a["ai_generat"] = a.get("processed_by") not in ("official", "fallback")
```
`official` = titlul instituției publicat exact (`process.py:301`). `fallback` = providerul
lipsește, se copiază `original_title` (`process.py:378`). **Niciunul nu atinge modelul**, deci
un marcaj pus pe ele ar fi o afirmație falsă.

---

## 2. Ce NU am apucat

1. **Wiring-ul verificărilor în `process.py`** — neînceput. Modulul există, nu-l apelează nimeni.
2. **Prompturile (felia 3)** — neatinse. `SYSTEM_B/USER_B`, `SYSTEM_C/USER_C`,
   `SYSTEM_C_BATCH/USER_C_BATCH`, `SYSTEM_BATCH/USER_BATCH` în `process.py:15-74`.
   Planul era o constantă comună interpolată în toate patru, ca să nu devieze una de alta.
3. **`TITLE_MAX_WORDS` (felia 4)** — `config.py:230` are 22, prompturile cer 6-16. Nealiniate.
4. ~~**`pytest`** — nu știu dacă suita e verde.~~ **REZOLVAT** după scrierea predării: suita
   a terminat în 644s, 934 trec / 2 pică / 8 xfailed. Detaliile și cele două picate, în
   avertismentul de sus. Durează ~11 minute, deci se pornește în fundal, nu în prim-plan.
5. **Pictograma UE** — nedescărcată. Descărcarea de fișiere cere confirmarea lui Alexandru.

---

## 3. Descoperiri măsurate — NU le re-cerceta

### 3.1 Textul-sursă nu se păstrează. Consecință mare.
Măsurat pe `data/articles.json` (3197 articole): **`original_title` = 0, `description` = 0.**
Cheile existente sunt doar: `ai_cat, category, entities, featured, icon, model, original_link,
processed_by, prompt_version, published, slug, source, source_lang, source_name, src_extra,
teaser, title, url`. Nu există `data/state.json` — `articles.json` E starea.

**Ce înseamnă:** verificările mecanice **nu se pot rula retroactiv** pe arhivă — nu există cu ce
compara. Pot rula **doar la generare**, în `process.py`, cât timp sursa e încă în mână.
Deci `tools/masoara_sinteza.py`, așa cum e scris, nu are ce măsura (a întors `VERIFICATE: 0`).
**De rescris:** verificările se apelează în `process.py` în modul „raportează", iar cifrele vin
din următoarea rulare normală de pipeline — gratis, fiindcă rularea are loc oricum.

### 3.2 Bumparea `PROMPT_VERSION` pare că NU costă nimic — dar verifică
`main.py:185-196`, funcția `upgradable()`, cere `a.get("original_title")` ca să reproceseze un
articol. Cum niciun articol din stare nu are câmpul (§3.1), lista iese **goală întotdeauna**,
deci schimbarea `PROMPT_VERSION` n-ar declanșa reprocesarea celor 2942 de articole.

**[INTERPRETARE, neterminată]** Aparent bun pentru buget, dar înseamnă și că mecanismul de
upgrade e **mort prin construcție**. Docstring-ul de la `main.py:202-207` documentează deja că
articolele oficiale n-au `original_title`; **faptul mai larg — că NICIUN articol nu-l are — nu
e documentat acolo și n-am apucat să verific dacă `original_title` există tranzitoriu în timpul
rulării.** De confirmat înainte de a te baza pe concluzia asta.

### 3.3 Compoziția corpusului
`model`: B = 2718, C = 479. `processed_by`: gemini = 2942, official = 255.
Zero `fallback` în stare acum.

### 3.4 Pictograma UE — aleasă, cu sursă
**„Fully AI-Generated"**, din cele trei. Pagina Comisiei dă ca exemplu explicit *„AI-generated
news summaries"*. Nu „Partially AI-Modified", fiindcă regulile cer reformulare 100%, deci nu e
modificare parțială a textului sursei.
SVG: <https://ec.europa.eu/newsroom/dae/redirection/document/129546> ·
PNG: <https://ec.europa.eu/newsroom/dae/redirection/document/129547>
**Pictograma e OPȚIONALĂ; dezvăluirea în sine e obligatorie.** Deci eticheta text deja pusă e
suficientă pentru conformitate — pictograma e plus.

### 3.5 Temeiul legal, pe scurt
Regulament (UE) 2024/1689, art. 50(4). În vigoare **de la 2 august 2026**. Excepția cere
**ambele**: verificare umană **și** răspundere editorială. izz.ro are doar a doua → marcarea e
obligatorie. Sursa juridică am citit-o prin rezumat de căutare, nu în textul primar —
**de verificat la sursă înainte de a o trata ca normă definitivă.**

### 3.6 Igienă de registru
`IZZ-0142` e pe `blocat` deși PR #131 e `MERGED` (varianta (b) aleasă de proprietar, 4 aug).
Rândul stătut m-a trimis pe pistă greșită. De trecut pe `implementat`.

---

## 4. Decizii care îl așteaptă pe Alexandru

1. **Formularea din `.ai-note`** spune explicit că textul „nu a fost recitit de un editor uman
   înainte de publicare". E adevărat și e exact motivul pentru care excepția nu se aplică, dar
   e o admitere publică. Decizie editorială, nu tehnică.
2. **Descărcarea pictogramei UE** — cere confirmarea lui.
3. **Pragul de respingere** pentru verificările mecanice — de stabilit DUPĂ măsurare, nu ghicit.
   Până atunci ele doar raportează.
4. **Reprocesarea arhivei** (~2091 titluri peste 85 de caractere, întrebarea de la care a pornit
   ziua) — **nu e inclusă în nimic din ce am făcut** și costă bani. Decizie separată.

---

## 5. Context care lipsește altfel

Ziua a pornit de la o cifră pe care am dat-o eu greșit: „85 de caractere, lungimea recomandată".
**Nu e recomandată de nimeni** — nici Google, nici vreun standard, nici codul lui. Verificat:
literatura de jurnalism nu conține recomandări de lungime deloc. Regula care o înlocuiește e
**front-loading** (informația grea în primele 2-3 cuvinte, NN/g), scrisă în `REGULI-SINTEZA.md §1.2`.
**Nu reintroduce un plafon de caractere.**
