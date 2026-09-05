# Regimul regulilor — închidere audit unificat

> **Status: HARDENED, audit closure 2026-09-05.** Acest document nu mai este o listă de lucruri „de făcut”; este registrul de reconciliere dintre auditul din 2026-08-29 și implementarea verificabilă din ramura `audit-unified-hardening-2026-09-05`.
>
> Principiul păstrat: nicio regulă nouă fără gardă identificată; regulile condiționate sunt L1 prin hook, iar istoricul și măsurătorile vechi rămân în L2 (`specs/`).

## 1. Matrice de închidere K1–K14

| ID | Problemă din audit | Închidere | Mecanism / dovadă |
|---|---|---|---|
| K1 | regula §16.3 spunea că remote nu poate verifica live | **închis** | `CLAUDE.md §16.3` declară explicit izz.ro/www ca hosturi ce pot fi blocate de proxy și Worker origin ca rută de verificare; `build.yml` folosește Worker origin |
| K2 | documentația istorică indica vechiul cron | **închis** | cadența canonică este `13 * * * *` + poartă 105 min; `CLAUDE.md §17` este sursa operațională |
| K3 | `§N` ambigu între documente | **închis** | `CLAUDE.md` definește namespace-ul: §N necalificat = `CLAUDE.md`; `REGULI-SINTEZA.md §N` este explicit când se referă la normativul de conținut |
| K4 | 22 vs. 6–16 cuvinte | **închis** | 6–16 = ținta editorială; `TITLE_MAX_WORDS = 22` = safety ceiling; decizia este în `REGULI-SINTEZA.md §6` și repetată concis în `CLAUDE.md §7` |
| K5 | trei canale de coordonare concurente | **închis** | canal unic = `handoff/` din workspace + `specs/STATE.md`; issue #83 și jurnalele TASKS nu mai sunt canal normativ; `tools/log_slice.py` generează aceeași regulă |
| K6 | allowlist promisă nu exista | **închis** | `.claude/settings.json` conține `pytest`, `ruff`, `git fetch`, `git pull` și testul de closure verifică prezența lor prin mecanismul existent |
| K7 | relația `COORD-DASHBOARD.md`/`log_slice.py` era inversată | **închis** | harta din `CLAUDE.md §21` spune „generat de `tools/log_slice.py`”; scriptul este generatorul autoritar |
| K8 | `/audit` trimitea la baseline mort | **închis** | `.claude/commands/audit.md` trimite la `specs/masuratori-frontend.md` → secțiunea `Baseline` |
| K9 | `/slice` atribuia clustering-ul lui §10 | **închis** | `.claude/commands/slice.md` separă clustering `§7` de synthesis/legal/deploy `§10` |
| K10 | anti-data-loss nu se aplica managerului Claude | **închis** | `.claude/settings.json` blochează `git restore`, `git checkout --`, `git stash`, `git clean`, `git reset`; regula de rol rămâne și în `AGENTS.md` |
| K11 | dashboard stătut prezentat drept măsurătoare curentă | **închis** | snapshot-ul este marcat explicit istoric; `CLAUDE.md §19` califică benchmark-ul cu `n=3, iulie 2026` și interzice folosirea lui ca benchmark curent |
| K12 | `REVIEW.md` descria regim încheiat | **închis** | „Lansare soft” este marcată etapă încheiată; textul operațional indică regimul actual (~2h automat, ~12 min manual) |
| K13 | mandat duplicat fără gardă | **închis** | `session-start.sh` extrage mandatul din `CLAUDE.md` cu `awk`; nu mai conține o copie hardcodata; testul de closure verifică acest contract |
| K14 | 13 reguli pierdute fără semnal | **închis structural** | contractul canonic este compactat; L1 este cablat în `PostToolUse`; gărzi CI verifică fapte/plafoane; protecții PreToolUse blochează fișierele critice; reguli noi trebuie să aibă gardă identificată |

## 2. F4 / L1 — stare finală

`PostToolUse` este cablat în `.claude/settings.json` pentru `Edit|Write|Bash` și rulează `.claude/hooks/reguli-l1.sh`.

Catalogul L1 actual:
- `13-frontend` → `templates/`, `static/styles.css`, `generator/render.py`.
- `18-imagini` → uneltele/fișierele media aferente.

Regula este livrată mecanic o singură dată pe sesiune prin `hookSpecificOutput.additionalContext`. Supraîncărcarea pe `Bash` este acceptată deliberat: un fals pozitiv mic este preferat unei reguli ratate. Limita este documentată în cod.

## 3. Gărzi mecanice

Există acum trei familii de gărzi:

1. **Integritate a regulilor:** `tests/test_reguli.py` verifică plafoane, bugetul de pornire, TTL, secțiuni, căi, cron și harta root.
2. **Siguranță de publicare:** `tools/grounding_gate.py` este blocking pentru `citat_inventat` și `cifra_straina`; `generator/raport_copiere.py` scrie dovada tranzitorie fără textul sursei.
3. **Siguranță de execuție:** `.claude/hooks/deny-protected-edits.sh` protejează fișierele control-plane; `.claude/settings.json` blochează operațiile git distructive și aprobările au allowlist explicit.

## 4. Ordinea de release

`build.yml` impune ordinea:

`pipeline → grounding gate → media best-effort → QA blocking → commit → IndexNow send → mirror/release probe`.

`QA check` și grounding gate sunt înainte de commit; astfel un corpus invalid nu poate fi publicat de această cale.

Release probe folosește ca fallback originea Workers `https://izz-ro.andifreelancer2.workers.dev`, nu vechiul `izz-ro.pages.dev`.

## 5. Ce rămâne în afara controlului repo-ului

Acestea nu sunt declarate „rezolvate” de codul repo-ului:
- branch protection / required status checks la nivelul setărilor GitHub, dacă nu sunt deja configurate de owner;
- WAF/proxy și DNS/Cloudflare extern repo-ului;
- exercițiul operațional de restore/takedown și redacția efectivă umană;
- verificarea live pe `izz.ro` din sesiuni unde proxy-ul blochează domeniul.

Ele sunt controale de platformă/operare, nu pot fi transformate în fapte printr-un commit în acest repository.

## 6. Criteriul de închidere

Auditul unificat este considerat **închis în repo** când:
- K1–K14 au un status explicit de mai sus;
- driftul factual relevant are test automat sau sursă canonică;
- L1 este cablat și condițional, nu duplicat la fiecare tură;
- operațiile destructive și fișierele control-plane sunt protejate;
- gate-urile de grounding și QA sunt blocking înainte de commit;
- CI-ul pentru HEAD-ul ramurii trece.

Ultimul punct este o proprietate a rulării CI, nu o presupunere din existența fișierelor. Un audit „închis” nu înseamnă „site live confirmat” pe hosturile pe care proxy-ul le blochează.

## 4. Poarta umană pentru sintezele C — comutator, nu stare permanentă (2026-09-05)

`IZZ_REQUIRE_HUMAN_GATE` nu mai e hardcoded `true` în `build.yml`. Este o **variabilă de
repo GitHub**, armabilă fără atingere de cod: Settings → Secrets and variables → Actions →
Variables → `IZZ_REQUIRE_HUMAN_GATE` = `true`. Default `false`, din același motiv pentru
care există detecția de tăcere: poartă mereu pornită + proprietar care nu operează YAML
zilnic = site înghețat tăcut, cel mai rău mod de eșec din matrice. Comutatorul aparține
proprietarului; când e armată, poarta rămâne fail-closed (orice valoare necunoscută
oprește pipeline-ul — `generator/moderation.py::_human_gate_required`).
