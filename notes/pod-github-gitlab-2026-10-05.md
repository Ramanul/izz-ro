# Pod GitHub ↔ GitLab — procedură de aplicat de pe stația ta

> Cerut 2026-10-05. Scris de agent în sesiunea Arena, branch `arena/01a108b3-izz-ro`.
> **Nicio comandă de aici nu rulează de aici:** sandbox-ul Arena are egress permis doar
> spre `github.com` și `api.github.com`, deci tot ce atinge gitlab.com se execută pe
> calculatorul tău, în terminalul tău.

## De ce direcția contează (tier-uri GitLab)

- **Push mirroring** pe GitLab (ce e pe GitLab → se trimite în GitHub) = **gratuit**.
- **Pull mirroring** pe GitLab (GitHub → se trage în GitLab) = **Premium**.
- GitHub nu are mirroring nativ deloc — se face cu un Actions workflow.
- Push-ul de Actions e gratuit → de-aia, dacă vrei ca **GitHub să rămână stăpânul**, folosești
  varianta din secțiunea 4, nu pe cea din 3.

Pentru izz-ro: GitHub rămâne sursa de adevăr (31 de workflow-uri în `.github/workflows/`:
pipeline, deploy-worker, deploy-failover, feedcheck, trafic, codeql, semgrep, recovery-drill).
GitLab = oglindă / CI secundar, nu loc de lucru. Mirror-ul copiază **doar refs git**
(branch-uri + tag-uri): issues, PR-uri, wiki și attachment-uri nu se copiază.

---

## Varianta 3 — gratuită, dar inversează rolurile: lucrezi pe GitLab, GitHub e oglinda

1. **GitLab:** New project → Blank project, nume `izz-ro`, Private, **fără** README inițial.
   Notezi URL-ul: `https://gitlab.com/<user>/izz-ro.git`.
2. **GitHub:** creezi repo-ul gol `izz-ro-mirror` (fără README, fără license).
3. **GitHub:** Settings → Developer settings → **Fine-grained PAT**:
   - Repository access: *Only select repositories* → `Ramanul/izz-ro-mirror`
   - Permissions: **Contents: Read and write** (restul „No permissions")
   - Expiration: 90 zile. Dacă se scurge cheia, pierzi doar oglinda.
4. **GitLab:** Settings → Repository → **Mirroring repositories** → Add new:
   - Git repository URL: `https://github.com/<user>/izz-ro-mirror.git`
   - Mirror direction: **Push**
   - Authentication method: Password · Username: `token` · Parola: PAT-ul de la 3
   - „Keep local files in sync": bifat (oglindește și ștergerile de branch)
   - Butunul **Mirror repository now** → citești jurnalul de sub rand: „succeeded" = podul mers.
5. De acolo încolo: un `git push` pe GitLab apare pe GitHub în câteva secunde, fără cron,
   fără server, fără mașina ta pornită.

---

## Varianta 4 — recomandată pentru izz-ro: GitHub stăpân, GitLab oglindă (Actions, gratuit)

### 4.1 Pe GitLab — ținta + cheia care poate scrie

1. New project → `izz-ro-mirror`, Private, fără README.
2. Settings → Repository → **Deploy keys** → Add deploy key:
   - Title: `github-actions-oglinda`
   - Key: public-ul generat de tine (`ssh-keygen -t ed25519 -f oglinda -N ""`)
   - **Grant write permissions** bifat.
3. Cheia privată (`oglinda`) o duci pe GitHub la Settings → Secrets and variables →
   Actions → New repository secret, nume `GITLAB_SSH_KEY`.

### 4.2 În acest repo — `.github/workflows/oglinda-gitlab.yml`

```yaml
name: oglinda-gitlab

# Oglindește main + tag-uri pe GitLab după fiecare push. Gratuit, fără tier.
on:
  push:
    branches: [main]
    tags: ["v*"]
  workflow_dispatch:

jobs:
  impinge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Impinge pe GitLab
        env:
          KEY: ${{ secrets.GITLAB_SSH_KEY }}
        run: |
          set -euo pipefail
          mkdir -p ~/.ssh && chmod 700 ~/.ssh
          printf '%s\n' "$KEY" > ~/.ssh/id_ed25519 && chmod 600 ~/.ssh/id_ed25519
          ssh-keyscan -t ed25519 gitlab.com >> ~/.ssh/known_hosts
          git config user.name  "oglinda-bot"
          git config user.email "oglinda@users.noreply.github.com"
          git remote add oglinda ssh://git@gitlab.com/<user>/izz-ro-mirror.git
          # --force pe branch, NU --mirror: --mirror ar șterge pe GitLab tot ce
          # nu există în sursă (ramuri de experiment, backup-uri).
          git push --force oglinda "HEAD:refs/heads/main"
          git push --force --tags oglinda
```

Înlocuiești `<user>`. Trigger-ul `workflow_dispatch` îți dă buton de „rulează acum" pentru
test.

### 4.3 Test

```bash
git ls-remote ssh://git@gitlab.com/<user>/izz-ro-mirror.git | head
git ls-remote https://github.com/Ramanul/izz-ro.git refs/heads/main
# hash-urile de pe main trebuie să fie identice
```

## Dezlipire (rollback)

- Variables → Workflows → dezactivezi `oglinda-gitlab.yml` (sau ștergi fișierul);
- revoke pe deploy key / PAT;
- repo-ul de pe GitLab îl **arhivezi**, nu-l ștergi — rămâne backup citibil.

---

## Ce nu rezolvă niciun pod (limitări de platformă, nu de git)

- în panoul de connection al Arena există **un singur provider: GitHub**; un al doilea
  repo nu poate fi atașat pe aceeași sesiune;
- rețeaua din sandbox nu vede GitLab/Bitbucket/Hugging Face (permet only `github.com`,
  `api.github.com`) — deci un `git clone` din altă parte nu poate fi dat de agent;
  se face de pe stație sau prin import GitHub;
- după ce PR-ul e fuzat/închis, sesiunea nu mai poate împinge;
- branch protejat (`main` al tău, cu review gates) respinge force-push, deci pe
  țintă folosești un branch neprotejat;
- tokenurile și parolele nu se lipesc în chat: nu se cer și nu se stochează.

## Note de surse (verificate 2026-10-05)

- Push mirror gratuit / pull mirror Premium: docs GitLab `user/project/repository/mirror`
  + forum.gitlab.com/t/132370, /t/115774.
- Rețeta clasică `git clone --mirror` + `git push --mirror` și capcana „șterge pe țintă":
  reddit r/git „is there a way to consistently mirror one repo to another".
- `repo-sync/github-sync@v2` pentru pull dintr-un repo terț în GitHub;
  `2pisoftware/git-mirror-action` pentru push spre Bitbucket/CodeCommit.
- Bloguri care încurcă tier-ul (zic că push cere abonament): dev.to/brunorobert —
  nu te lua după ele.
