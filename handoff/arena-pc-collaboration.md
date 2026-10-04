# Colaborare Arena ↔ PC local

**Scop:** Arena lucrează prin GitHub; PC-ul local preia și verifică ramurile prin Git. Pentru rulări locale controlate, GitHub Actions poate trimite numai două sarcini fixe către un runner Windows înregistrat. Acest document nu oferă un shell/SSH arbitrar.

## A. Canalul Git — disponibil imediat

GitHub este punctul comun de predare; nu se sincronizează directoare locale prin SSH.

### PC-ul preia o ramură Arena

Din clonarea locală a repo-ului:

```powershell
git fetch origin --prune
git branch --remotes --list 'origin/arena/*'
git switch --track origin/arena/<ramura>
git pull --ff-only
```

Dacă ramura există deja local, folosește `git switch <ramura>` și apoi `git pull --ff-only`. Înainte de schimbare, verifică `git status --short --branch`; nu suprascrie modificări locale.

Trimite înapoi o schimbare locală pe o ramură proprie și printr-un PR. Nu edita `main` direct și nu împinge simultan pe ramura de lucru a altei sesiuni. Pentru predare, comunică numele ramurii, SHA-ul commitului și ce a fost verificat. `handoff/` și PR-ul păstrează contextul în repo; nu pune aici tokenuri, chei sau date private ale PC-ului.

## B. Runner Windows — execuție locală limitată

Workflow-ul este `.github/workflows/local-pc-runner.yml`. El oferă doar:

- `proof`: creează un fișier de probă în checkout-ul temporar al runnerului și îl încarcă drept artifact GitHub cu retenție de o zi;
- `tests`: creează un mediu virtual temporar, instalează dependențele repo-ului și rulează Ruff + `pytest tests/`.

Workflow-ul este numai `workflow_dispatch`, verifică `main`, cere confirmarea `confirm_local_execution=true` și variabila de repo `LOCAL_RUNNER_ENABLED=true`, apoi trece prin environment-ul `local-runner`. Nu acceptă comenzi, scripturi sau căi de fișiere ca input. Nu pornește aplicații desktop și nu oferă SSH interactiv.

**Important — repo public:** GitHub avertizează că runner-ele self-hosted nu sunt recomandate pentru repo-uri publice, deoarece codul neîncrezut executat pe runner poate compromite mașina. Acest workflow nu rulează la PR/push și este blocat pe `main`, dar aceste protecții nu elimină riscul dacă se schimbă ulterior workflow-urile sau accesul repo-ului. Folosește-l doar dacă accepți riscul, numai cu utilizatori de încredere care pot declanșa workflow-uri, și ideal pe un cont Windows separat, fără drepturi de administrator și fără date/secrete personale. Vezi [recomandările GitHub pentru securizarea runner-elor](https://docs.github.com/en/actions/reference/security/secure-use).

### Activare — o singură dată, de către proprietar pe GitHub și Windows

1. Aterizează workflow-ul pe `main` prin review-ul obișnuit.
2. În **Settings → Environments**, creează `local-runner`, cere aprobarea proprietarului ca reviewer și restrânge deploy-urile la ramura `main`.
3. În **Settings → Secrets and variables → Actions → Variables**, adaugă `LOCAL_RUNNER_ENABLED=true` abia după ce protecțiile environment-ului sunt configurate.
4. În **Settings → Actions → Runners → New self-hosted runner**, alege Windows x64 și urmează instrucțiunile generate de GitHub. Adaugă label-ul `izz-ro-local`; workflow-ul cere exact acel label. Rulează inițial `run.cmd` interactiv, sub un cont Windows standard. Nu instala runner-ul ca serviciu persistent decât dacă accepți explicit execuția continuă pe PC.
5. Tokenul de înregistrare este temporar, folosit numai local la configurare, și **nu trebuie trimis în chat, comis în Git sau salvat în workflow**. Instrucțiunile GitHub îl generează în pagina runner-ului; expiră după o oră ([documentația de instalare](https://docs.github.com/actions/hosting-your-own-runners/adding-self-hosted-runners)).
6. Din **Actions → local-pc-runner → Run workflow**, selectează `main`, `proof` (prima probă) și bifează confirmarea. Environment-ul trebuie aprobat. Artifactul `local-runner-proof-<run-id>` confirmă că jobul a rulat pe PC.

După activare, Arena poate porni aceleași sarcini prin GitHub CLI/API, fără să primească tokenul de înregistrare:

```powershell
gh workflow run local-pc-runner.yml --ref main -f task=proof -f confirm_local_execution=true
gh run list --workflow local-pc-runner.yml --limit 1
```

După ce ai identificat ID-ul execuției:

```powershell
gh run watch <run-id>
gh run download <run-id> --name local-runner-proof-<run-id>
```

Runner-ul își folosește propriul director `_work` și un checkout separat de clonarea ta obișnuită. Fișierul de probă este ignorat de Git și nu este comis automat. Artifactul dovedește execuția locală și poate fi citit în GitHub Actions; pentru schimbări de cod, folosește canalul Git din secțiunea A.

Dacă runner-ul nu este încă înregistrat sau online, jobul va aștepta un runner cu label-ul cerut. Pentru dezactivare, elimină `LOCAL_RUNNER_ENABLED`, dezactivează/șterge runner-ul din **Settings → Actions → Runners** și oprește procesul local.
