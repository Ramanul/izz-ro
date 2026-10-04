# Colaborare Arena ↔ PC prin Git

GitHub este punctul comun de predare între Arena și PC. Această cale sincronizează codul și fișierele versionate; nu cere SSH, runner local sau publicare pe `izz.ro`.

## Preia ramura curentă pe PC (PowerShell)

Pentru predarea curentă, ramura Arena este `arena/01a10896-izz-ro`:

```powershell
git fetch origin
git switch --track origin/arena/01a10896-izz-ro
```

Dacă ramura există deja local:

```powershell
git switch arena/01a10896-izz-ro
git pull --ff-only
```

Verifică ce ai preluat:

```powershell
git status --short --branch
git log -1 --oneline
```

Nu schimba ramuri peste modificări locale necomise și nu împinge direct pe ramura unei alte sesiuni.

## Trimite o schimbare locală înapoi

Lucrează pe o ramură proprie, comite doar fișierele intenționate, apoi împinge ramura și transmite numele ei plus SHA-ul commitului. Schimbările intră în proiect prin review/PR; nu se editează `main` direct.

Nu comite tokenuri, chei, configurații locale sau alte date private. `handoff/` poate păstra notițe de predare, dar nu se folosește pentru secrete.
