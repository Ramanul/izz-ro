# metrics.csv — jurnal de munca si consum

`specs/metrics.csv` = CSV append-only, o linie per slice verificat. Scriu **ambele conturi**.

| coloana | ce inseamna |
|---|---|
| `date` | ziua, `YYYY-MM-DD`, pusa automat |
| `account` | `A`, `B` sau `owner` — cine a facut slice-ul |
| `slice` | numele slice-ului, kebab-case (ex. `impact-first-120`) |
| `approach` | `solo` (contul singur), `agent` (subagenti), `ci` (GitHub Actions), `devin`/`oc`/`jules` (executori externi) |
| `executor_branch` | branch-ul executorului, daca a fost unul; gol altfel |
| `diff_lines` | linii schimbate, din `git diff --stat` |
| `duration_min` | optional |
| `tokens_k` | tokeni **estimati** de raportor, in mii — ordin de marime, nu factura |
| `notes` | ce s-a livrat, in cuvinte; escapat impotriva injectiei de formule |

**Regula de delegare** (de revizuit dupa ~20 de randuri, cand datele sunt semnificative):
delegam implementarea estimata la peste ~5k tokeni; sub atat, overheadul de spec + review
depaseste economia.

**Adaugare:**
```
python tools/log_slice.py --account B --slice nume-slice --approach solo \
    --diff-lines 42 --tokens-k 15 --notes "ce s-a livrat"
```

**Raport** (regenereaza `COORD-DASHBOARD.md`, vizibil pe GitHub pentru amandoi):
```
python tools/log_slice.py --report
```
