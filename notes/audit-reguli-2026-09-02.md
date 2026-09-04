# Audit al fișierelor de reguli — izz.ro (2 septembrie 2026)

> Verificat: `git fetch origin main` + `git diff` pe fișierele-nomenclator de mai jos.
> Citit integral: `CLAUDE.md`, `AGENTS.md`, `REGULI-SINTEZA.md`, `REVIEW.md`,
> `COORD-DASHBOARD.md`, `.claude/reguli/13-frontend.md`, `moderation.yaml` (antet),
> `specs/STATE.md`, `TASKS-MISTRAL.md` (antet), `.coderabbit.yaml`, `.gemini/config.yaml`.
> Auditul complet anterior: `specs/regim-reguli.md`. Nu s-a modificat niciun fișier de reguli.

## 1. Inventar (Unde stă ce)

| Fișier | Rol | Loc |
|---|---|---|
| `CLAUDE.md` (318 linii, ~23,8 KB) | contractul canonic; orice sesiune începe aici | repo, rădăcină |
| `AGENTS.md` | supliment pentru executori non-Claude (Devin, OpenCode, Jules, Mistral); trimite la CLAUDE.md | repo |
| `REGULI-SINTEZA.md` | normativ editorial pentru titluri/rezumate; codul implementează EL documentul | repo |
| `REVIEW.md` | protocolul de review | repo |
| `COORD-DASHBOARD.md` | generat de `tools/log_slice.py` — nu se editează | repo |
| `.claude/reguli/13-frontend.md` | regula L1, livrată de hook `PostToolUse` când atingi front-end | repo |
| `moderation.yaml` | comenzi editoriale ale proprietarului (human-owned) | repo |
| `specs/STATE.md` | starea execuției, se citește la început de sesiune | repo |
| `specs/regim-reguli.md` | auditul complet al regulilor + ce s-a pierdut la tăiere | repo |
| `specs/registru.tsv` + `tools/registru.py` | registru append-only de decizii (anti re-litigare) | repo |
| `TASKS-MISTRAL.md` | coadă + reguli pentru Mistral Vibe (instantaneu din 14 aug) | repo |
| `.coderabbit.yaml`, `.gemini/config.yaml`, `.github/workflows/*` | reguli aplicate de roboți de review/CI | repo |
| `~/.claude/AGENTS.md` (global) | reguli comportamentale la nivel de utilizator (R1-R8, N1-N4, delegare, tabelul de raport) | mașină |
| `~/.vibe/AGENTS.md` | contractul lui Mistral Vibe | mașină |
| `COMUNICARE.md`, `LECTII.md` | referite de regulile globale — **LIPesc** (vezi §3A) | n-audăsit |
| `handoff/PROTOCOL.md`, `handoff/to-A/` | canalul de anunț de la §14 — **LIPesc** aici (vezi §3B) | n-audăsit |

GitHub (`origin/main`) vs local: `CLAUDE.md`, `AGENTS.md`, `REGULI-SINTEZA.md`, `REVIEW.md`,
`COORD-DASHBOARD.md`, `specs/STATE.md` — **identice**. Diferențe existente: branch-ul local
`wip/portare-codex` are comis `.codex/` + două workflow-uri necomise pe main în sens invers
(`origin/main` are `masoara-gazde.yml`, `revizuire.yml`, `.codex/README.md` care lipsesc aici);
modificat local: `.agents/skills/source-command-audit/SKILL.md`, `specs/anomalie-linkuri.md`.

## 2. Relații de armonie (confirmate, nu bănuite)

- **`AGENTS.md` → `CLAUDE.md`: subordonare explicită, zero duplicare.** AGENTS.md adaugă doar
  regulile de rol executor (branch `devin/`·`oc/`, merge interzis, fișiere străine neatinse,
  `data/articles.json` și `moderation.yaml` never-edit) — toate în concordanță cu §14, §14b, §5.
- **`REGULI-SINTEZA.md` ↔ `CLAUDE.md` §7:** „Zero Zgomot / sare itemul stricat" apare identic în
  ambele; documentul de sinteză e declarat normativ, iar codul e cel care urmează.
- **Conflictul 6-16 vs `TITLE_MAX_WORDS=22` e REZOLVAT în REGULI-SINTEZA §6** (decis 29 aug):
  țintă editorială vs plasă de siguranță, straturi diferite, nu contradicție.
- **`REVIEW.md` ↔ `CLAUDE.md` §17:** aceeași cadență (~2h, poartă 105 min, Run workflow ocolește
  poarta) scrisă coerent în ambele.
- **`.claude/reguli/13-frontend.md` ↔ §13:** §13 e doar un pointer, textul trăiește într-un singur
  loc — modelul de referință pentru regulari „plătite la fiecare tură".
- **Global ↔ repo, ierarhie declarată:** `~/.claude/AGENTS.md` enunță singur ordinea de
  precedență (harness > CLAUDE.md global > CLAUDE.md proiect > spec de task).

## 3. Contrarietăți și goluri (lista cu ce propun, cu ordinea recomandată: întâi ce blochează decizii)

**A. `COMUNICARE.md` și `LECTII.md` — referite, dar nu există. [FAPT]** Regulile globale le citează
de ~20 de ori (R1-R8 trimit la COMUNICARE.md; repo `CLAUDE.md` §0 trimite la `../LECTII.md` L8),
iar `~/.claude/CLAUDE.md` spune că stau „în rădăcina workspace-ului". Nu există nici în repo, nici
în `~/.claude/`, nici în `C:\Users\cw_26\` (căutare până la adâncime 3). Consecință: regulile
globale trimit la justificări („pragurile măsurate, sursele") pe care nicio sesiune de pe mașina
asta nu le poate citi. **Propun:** le cauți pe cealaltă mașină/workspace și le aduci în repo
(ex. `docs/`) sau în `~/.claude/` — ele sunt reguli de comportament, deci locul lor e lângă
`~/.claude/AGENTS.md`. Cost: copy-paste, 2 fișiere. **Ce infirmă concluzia:** dacă fișierele
există pe un mount/cale pe care căutarea mea n-a acoperit-o (rețea, alt drive), atunci doar calea
din reguli e greșită, nu lipsa fișierelor.

**B. `handoff/` — canalul de anunț de la §14 nu există pe mașina asta. [FAPT]** `CLAUDE.md` §14
cere „un fișier nou în `handoff/to-A/` din workspace (format: `handoff/PROTOCOL.md`)". Niciun
`handoff/` pe disc aici. Probabil trăiește în workspace-ul celuilalt cont (pe altă mașină), ceea
ce e intenția — dar o sesiune de aici care face merge nu poate executa literal pasul de anunț.
**Propun:** o linie în §14 care spune pe CE mașină/workspace trăiește `handoff/`, sau un fallback
(„dacă nu ai acces la workspace-ul cu handoff/, anunță în `specs/STATE.md`"). Cost: un rând în
`CLAUDE.md`, care are loc liber (741 octeți din plafon).

**C. Contradicție reală: autonomie pe `main`.** Global: „**Autonomie extinsă (24 iul 2026):** pot
acționa autonom pe `main`". Repo `CLAUDE.md` §14: „**Mandatul autonom din iulie e încheiat**",
rămâne doar §14b (muncă în fundal: draft PR, merge doar proprietarul, un task per declanșare).
Sunt în contradicție directă și decide regula globală de precedență „mai recent și mai specific":
repo-ul e mai specific (izz.ro) și §14b e decizia din 1 aug, ulterioară. **Deci pe izz.ro câștigă
§14/§14b — dar regulile globale nu știu asta și o sesiune care citește doar globalul va acționa
greșit.** **Propun:** o propoziție în `~/.claude/CLAUDE.md` la „Autonomie extinsă": „exceptat
izz.ro, unde mandatul e încheiat (CLAUDE.md §14, §14b)". Cost: un rând. **Ce infirmă:** dacă
Alexandru vrea reactivat mandatul pe izz.ro, atunci se corectează §14, nu globalul.

**D. `TASKS-MISTRAL.md` conține reguli-în-timp care s-au perimat parțial.** Spune „Repo-ul e pe
branch-ul `fix/harta-lista-rezultate`" — instantaneu din 14 aug; astăzi branch-ul curent e
`wip/portare-codex`. Nu e contradicție cu regulile vii (fișierul e coadă, §21 îi dă rol), dar un
executor care-l citește ca adevăr actual ajunge pe branch greșit. **Propun:** nimic de cod — doar
să nu-l cita ca sursă de reguli în spec-uri; regulile lui perene sunt deja duplicate corect în
`AGENTS.md`.

**E. Igienă de registru deschisă (din REGULI-SINTEZA §1.7):** rândul IZZ-0142 a rămas pe `blocat`
deși soluția e livrată (PR #131). Cost: o comandă `tools/registru.py`. Ordinea recomandată mai
sus: A > C > B > D > E — A și C afectează cum acționează orice sesiune, restul sunt cosmetice.

## 4. Ce NU am verificat

- Conținutul integral al celor ~20 de workflow-uri CI (le-am inventariat, nu le-am auditat ca
  reguli comportamentale — ele aplică reguli, nu le spun).
- `.claude/agents/*.md` (5 agenți) și `.claude/commands/` — inventariate; §13/§15 le descriu, dar
  nu le-am citit pe toate cap-coadă.
- `~/.vibe/AGENTS.md` — contractul Mistral, nu există pe mașina asta (session remote).
- `specs/regim-reguli.md` integral (341 linii) — e auditul anterior; presupun că rămâne valabil
  acolo unde nu-l contrazic eu. Încredere generală: **8/10**; scăderea vine din punctele
  neverificate de mai sus și din faptul că „lipsă" în A/B se poate dovedi „cale pe care n-a
  acoperit-o căutarea".
