# Accesul tehnic real la `main` — ce apără §5.4 și ce nu

**Măsurat:** 2026-09-06, sesiune Claude Code web, repo `Ramanul/izz-ro`.

**De ce există:** §5.4 din `CLAUDE.md` e scrisă ca imperativ absolut — „nu face niciodată merge".
Un imperativ absolut se citește ca gardă. Fișierul ăsta separă ce e gardă de ce e disciplină, cu
comanda care a produs fiecare verdict.

## 1. Ce s-a măsurat, cu ce comandă

| întrebare | comandă | verdict |
|---|---|---|
| identitatea GitHub a sesiunii | `mcp__github__get_me` | `Ramanul` — **chiar proprietarul repo-ului** |
| ce refuză deny-list-ul | citirea `.claude/settings.json` | 5 comenzi git distructive: `restore`, `checkout --`, `stash`, `clean`, `reset` |
| ce vede hook-ul PreToolUse | matcher-ul din același fișier | `Edit`, `Write`, `Bash` — **niciun tool MCP** |
| există vreo gardă de merge | `grep -rniE "merge_pull_request|enable_pr_auto_merge|git merge|auto-merge" .claude/ tests/ tools/` | **zero rezultate** |
| acoperă testele §5 | `tests/test_reguli.py`, docstring | „aici stau doar regulile care se pot NUMARA" — §5 nu e printre ele |

Nu există separare de identitate între rolul „executor" și rolul „proprietar": e același token.
§5.1 descrie o distincție de proces, nu una tehnică.

## 2. Căile deschise către `main`, numite

Niciuna nu trece prin vreo gardă. Ordinea e de la cea mai probabilă la cea mai puțin probabilă:

1. `mcp__github__merge_pull_request` — merge direct, un apel.
2. `mcp__github__enable_pr_auto_merge` — exact ce §5.4 interzice pe nume; nimic nu-l refuză.
3. `mcp__github__push_files` sau `mcp__github__create_or_update_file` cu `branch: main` — scriu în
   `main` **fără branch și fără PR**, deci ocolesc §5.3, nu doar §5.4.
4. `git push origin main` din Bash — trece prin hook, dar hook-ul compară căi de fișier, nu
   comenzi git; `main` nu e o cale de fișier.

Punctul 3 e cel mai tăcut: nu lasă în urmă nici măcar un PR care să poată fi observat ulterior.

## 3. De ce hook-ul nu ajută aici

`.claude/hooks/deny_protected_edits.py` are un model de amenințare complet diferit: apără
**fișiere** de **scrieri**. Un merge nu e o scriere de fișier și nu ajunge la Bash. Cele două
modele nu se suprapun deloc — nu e o scăpare de implementare, e o suprafață pe care nimeni nu a
acoperit-o.

Efect secundar măsurat de **două ori** în aceeași sesiune, deci recurent, nu accidental:

- `cat .claude/settings.json 2>/dev/null` — refuzat;
- `python -c "...json.load(open('data/articles.json'))..." 2>&1` — refuzat, deși e o citire pură.

Cauza e aceeași în ambele: `2>` și `2>&1` conțin `>`, iar garda potrivește pe subșir. Comentariul
din gardă acceptă explicit prețul — falsul blocant costă o decizie umană, falsul permis costă un
fișier de control rescris. E o alegere, nu un bug. Consecința practică, de reținut: **orice
citire a unui fișier protejat trebuie scrisă fără nicio redirectare**, inclusiv `2>/dev/null`.

## 4. Cicatricea

`IZZ-0140` (2026-07-13, `anulat`): două sesiuni cu cron autonom au făcut merge în paralel, iar
munca pe GA + security headers a trebuit refăcută. §5.4 s-a scris **după** pierdere.

Regula nu e prudență teoretică. E ce a rămas în picioare după un incident real — și e susținută
exclusiv de faptul că modelul o citește și alege s-o respecte.

## 5. Ce se poate cabla și ce nu

| cale | refuzabilă mecanic? | unde |
|---|---|---|
| `git push origin main`, `git merge` | da | lista `deny` din `.claude/settings.json` |
| uneltele MCP GitHub de scriere | da | aceeași listă, cu numele complet al uneltei |
| merge din interfața web GitHub | nu, din sesiune | branch protection sau ruleset — acțiune de proprietar |

Primele două cer o schimbare în `.claude/settings.json`, care e el însuși protejat de hook. Asta
e deliberat: ca gaura să se închidă, schimbarea trebuie să treacă prin revizuire, nu prin
sesiune. A o aplica ocolind garda ar fi exact comportamentul pe care fișierul ăsta îl
documentează ca risc.

### Patch-ul de aplicat — decis de proprietar 2026-09-06

Aleasă e **varianta îngustă**: se refuză exact cele două unelte care fac merge, nimic altceva.
Fluxul normal — push pe branch de lucru, deschidere de PR — rămâne neatins.

În `deny` din `.claude/settings.json`, după `"Bash(git reset:*)"`:

```json
      "mcp__github__merge_pull_request",
      "mcp__github__enable_pr_auto_merge"
```

**Se aplică împreună cu editarea din `CLAUDE.md` §5.4: `MERGE-GUARD = absent` devine `partial`.**
Cele două sunt o pereche atomică — garda recalculează starea la fiecare rulare, deci oricare
singură face CI roșu. Asta e comportamentul dorit, nu un efect secundar.

Respinse deliberat, cu motivul:

- `push_files` / `create_or_update_file` — ar închide și scrisul direct în `main` fără PR, dar
  blochează și scrierile legitime prin MCP într-un branch de lucru. Cost prea mare pentru cât
  acoperă.
- Branch protection — ar apăra repo-ul, nu doar sesiunile, dar nu se poate verifica din `tests/`,
  deci `MERGE-GUARD` ar rămâne `absent` fără ca asta să mai fie adevărat. Rămâne opțiune separată.

**Cine aplică:** proprietarul, manual. O sesiune nu poate: hook-ul refuză `Edit` pe fișier —
măsurat, nu presupus („DENY: direct agent edit blocked for protected control-plane file"). Există
o cale de ocolire — `mcp__github__create_or_update_file`, chiar una dintre cele patru din §2 — și
**nu se folosește**. La fel, nu se scrie un `tools/aplica_*.py` care să facă schimbarea printr-un
nivel de indirectare: hook-ul potrivește pe textul comenzii, deci un asemenea script ar dezarma
garda permanent, pentru orice sesiune viitoare, nu doar pentru asta.

## 6. Trimiterile greșite găsite pe drum

`.claude/agents/pipeline-runner.md` și `.claude/agents/README.md` citau §5.4 drept regula
„verifică rulând". Regula aia e §0. Reparate în aceeași felie.

Garda de secțiuni din `tests/test_reguli.py` nu le putea prinde: ea verifică dacă §5 există, nu
dacă sub-punctul `.4` e regula despre care vorbește textul. Garda de sub-punct adăugată acum
prinde sub-punctul **inexistent** (`§5.99`), nu sub-punctul **existent folosit pentru altă
regulă**. Al doilea caz cere judecată, ca §7 și §16 — limita e reală și declarată, nu o scăpare.
