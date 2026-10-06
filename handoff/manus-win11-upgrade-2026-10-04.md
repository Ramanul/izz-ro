# Handoff pentru Manus — upgrade Windows 11 pe Hyper-V „ZCode-VM" (4 oct 2026, ~15:10)

## Scopul (mandatul lui Alexandru)
Update la Windows 11 pe VM-ul Hyper-V „ZCode-VM" (acum Win10 Pro 22H2, build 19045), cu
**cea mai compatibilă versiune** și **păstrarea tuturor setărilor** (ZCode 3.14.4 instalat,
credentials, autologon, cont local) ⇒ upgrade **in-place**, NU clean install. Lucru **fără
capturi de ecran** — totul prin PowerShell Direct. Host: ASUS X99 + Xeon E5-2673 v4
(Broadwell, hardware NESUPORTAT oficial de Win11), 16 GB RAM, Hyper-V activ.

## Credențiale + acces
- PS Direct: `Invoke-Command -VMName ZCode-VM -Credential Alexandru`
  (cont local, grup Administrators). Parola NU se scrie în repo public —
  redactată 6 oct (intrase în clar prin PR #458).
- VM-ul rulează acum (nu o opri decât dacă procedura cere explicit).

## Config VM (setat și VERIFICAT azi)
- RAM: startup 6 GB, memorie dinamică min 2 GB / max 6 GB (verificat prin Get-VM,
  NU prin Get-VMMemory — pe acest host Get-VMMemory întoarce proprietăți goale, capcană cunoscută).
- 12 vCPU (din 40 fire logice).
- Gen 2, **Secure Boot ON** cu template „MicrosoftWindows" (boot-ul Win10 verificat OK după activare).
- **vTPM activ** (Set-VMKeyProtector + Enable-VMTPM); în guest: TpmPresent/Ready/Enabled = True.
- **Checkpoint „pre-win11-upgrade"** creat (ProductionOnly) — PUNCT DE ROLLBACK, nu-l șterge.
- Discul host: C: are ~210 GB liberi. Guest C:: ~52 GB liberi.

## Ce s-a făcut până acum (cu rezultate)

1. **ISO 26H2 local = INTERZIS.** `C:\Users\cw_26\VirtualBox VMs\Win11.iso` (8,86 GB, build 26300)
   e confirmat incompatibil cu X99 (moarte identică pe VirtualBox, Hyper-V și cu taste fizice —
   sesiunile anterioare). Microsoft servește acum DOAR 26H2 consumer — 24H2/25H2 retrase.

2. **ISO construit via UUPDump** (cea mai compatibilă variantă rămasă): update
   `cb4d2d02-8aae-40ba-94cb-02ac6bb0742e` („Windows 11, version 25H2" 26200.9550, x64, ro-ro,
   professional). Capcane rezolvate pe drum:
   - `get.php` prin **GET** întoarce doar lista de URL-uri aria2; bundle-ul real vine prin **POST**
     cu `autodl=2&aria2=2` → `uup_download_windows.cmd` (POST: 200 archive/zip).
   - orchestratorul descarcă `uup-converter-wimlib.7z` + `7zr.exe`, apoi UUP-urile (aria2),
     apoi convertește (wimlib, LZX).
   - Rezultat: `C:\Users\cw_26\uup-25h2\build\26100.1.240331-1435.GE_RELEASE_CLIENTPRO_OEMRET_X64FRE_RO-RO.ISO`
     (4,47 GB) = **Windows 11 Pro, build 10.0.26100.8972, ro-ro** (24H2 fully patched, verificat
     cu `dism /Get-WimInfo`). Numele zice 26100 pentru că 25H2 = media de bază 24H2; flip-ul la
     25H2 vine ulterior prin enablement package în Windows Update (mic, fără fază WinPE).
   - Log complet al construirii: `C:\Users\cw_26\uup-25h2\build\download.log`.

3. **ISO copiat în guest**: `C:\Users\Alexandru\Win11_25H2.iso` (4,17 GB, verificat) via
   `Copy-Item -ToSession`.

4. **Registry pregătit în guest** (ambele setate, VERIFICATE):
   - `HKLM\SYSTEM\MoSetup` → `AllowUpgradesWithUnsupportedTPMOrCPU` = 1 (DWORD)
   - `HKLM\SYSTEM\Setup\LabConfig` → BypassTPMCheck/BypassCPUCheck/BypassSecureBootCheck/
     BypassRAMCheck/BypassStorageCheck = 1 (DWORD)

5. **Lansările upgrade-ului — 4 încercări, toate eșuate înainte de staging:**
   - (a) Start-Process direct prin PS Direct → niciun proces (nu s-a lansat deloc).
   - (b) schtasks ca **SYSTEM** + `setup.exe /auto upgrade /quiet /dynamicupdate disable` →
     procese au apărut, apoi moarte; BlueBox: **0xC1900200** (cerințe hardware — scanarea refuză
     CPU-ul deși cheia MoSetup există; known issue pe hardware nesuportat).
   - (c) schtasks SYSTEM + `/product server` → **0xC190010E** LaunchProcessInSession
     (= EULA neacceptată — confirmat pe web; fix = `/accepteula`).
   - (d) schtasks interactiv `/IT /RL HIGHEST` + `/product server` → tot **0xC190010A/0xC190010E**.
   - (e) ULTIMA lansare (14:52–15:05): schtasks SYSTEM cu linia completă
     `E:\setup.exe /auto upgrade /quiet /accepteula /dynamicupdate disable /product server`
     → 3 procese „setup" vii, **fără staging**, BlueBox neschimbat de la 14:43 (ultima eroare
     **0xC190010A**). Verificat la 15:10: upgrade-ul NU pornește efectiv.

## Starea exactă acum (verificat 15:10)
- VM Running, vTPM True, checkpoint „pre-win11-upgrade" prezent.
- Guest: 3 procese `setup` vii (probabil stub-uri blocate), FĂRĂ `C:\$WINDOWS.~BT`, fără staging.
- Loguri cheie în guest: `C:\Windows\Logs\MoSetup\BlueBox.log` (blue-box upgrade),
  `C:\Windows\Logs\MoSetup\UpdateAgent.log`, `C:\Windows\Panther\`.

## Instrucțiuni pentru continuare (în ordine)

1. **Curățenie**: oprește task-ul și procesele blocate, apoi șterge staging-ul dacă apare:
   `schtasks /End /TN Win11Upgrade; taskkill /F /IM setup.exe /IM setuphost.exe /IM setupprep.exe`
   + `Remove-Item C:\$WINDOWS.~BT -Recurse -Force` (dacă există).
2. **Citește `BlueBox.log` după fiecare încercare** — fiecare eroare are cod clar; decodați codul
   înainte de retry (0xC190010E=EULA, 0xC1900200=cerințe HW, 0xC190010A=nedecodat încă).
3. **Relansei task-ul**: `schtasks /Run /TN Win11Upgrade` (task-ul „Win11Upgrade" există, SYSTEM,
   bat-ul curent: `C:\Users\Alexandru\upgrade.bat`). Așteaptă 2-3 min și verifică procese +
   apariția `C:\$WINDOWS.~BT`.
4. Dacă tot moare înainte de staging: **încearcă `E:\sources\setupprep.exe` direct** cu
   `/auto upgrade /quiet /accepteula /dynamicupdate disable /SkipSystemRequirementScans`
   (flag care sare peste scanarea de cerințe; verifică disponibilitatea cu `/arglist`).
5. Când staging-ul crește: lasă-l în pace 10–20 min (faza online) → reporniri automate.
   **PS Direct pică în timpul repornirilor — reconectează după.**
6. **Risc cunoscut în faza offline (SafeOS, WinPE)**: aici a murit 26H2 pe X99. Build-ul 26100
   (24H2) e generativ mai vechi și riscant dar ne-testat pe acest hardware. Dacă VM-ul stă >45 min
   pe spinner în faza offline ⇒ rollback (punctul 8).
7. **Verificare finală**: build 26100 + DisplayVersion 24H2
   (`HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion`), ZCode intact
   (`C:\Users\Alexandru\AppData\Local\Programs\ZCode`), autologon funcțional, PS Direct OK.
8. **Rollback** (dacă VM-ul e bricks): `Restore-VMCheckpoint -VMName ZCode-VM -SnapshotName
   "pre-win11-upgrade"` de pe host. Nu șterge checkpoint-ul până când Alexandru confirmă.
9. **Opțional după succes**: 25H2 prin enablement package în Windows Update (guest),
   mic, fără fază WinPE — cere acordul lui Alexandru înainte.

## Reguli obligatorii
- Un singur automatizator pe VM odată (precedent: conflict Manus vs ZCode).
- Fără capturi de ecran / fără vmconnect — totul PowerShell Direct + schtasks (canale verificate).
- ISO-ul 26H2 de 8,86 GB NU se folosește sub nicio formă.
- Nu modifica configul VM (RAM/CPU/vTPM/Secure Boot) — e calibrat de host (commit host fragil).
- Cod, comenzi, căi în engleză exactă; rapoarte către Alexandru în română.

*Scriere: sesiunea ZCode izz-ro, 4 oct 2026, la cererea explicită a lui Alexandru („stop, dă-i
instrucțiunile lui Manus să continue").*
