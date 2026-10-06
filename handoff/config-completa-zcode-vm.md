# Configurația completă — VM Hyper-V „ZCode-VM" (4 oct 2026, 15:50)

> Document de referință, scris din citiri reale de config (comenzi rulate), nu din memorie.
> Complement la: `handoff/manus-win11-upgrade-2026-10-04.md` (continuarea upgrade-ului Win11).

## 1. Identitate și scop
- **VM Hyper-V „ZCode-VM"** pe host-ul local (ASUS X99, Xeon E5-2673 v4, 20 nuclee/40 fire, 16 GB RAM, Windows Pro SKU 48).
- Scop: mașină virtuală în care rulează ZCode (aplicația de agenți) cu **cursor propriu**, separat de cursorul lui Alexandru pe host, cu 2 monitoare fizice.

## 2. Hardware virtual (verificat prin Get-VM, 15:50)
| Setare | Valoare |
|---|---|
| Generație | 2 (UEFI) |
| vCPU | 12 (din 40 fire logice) |
| RAM la pornire | 6 GB |
| RAM minim / maxim (dinamic) | 2 GB / 6 GB |
| Memorie dinamică | Activată |
| Tip checkpoint | ProductionOnly |
| Pornire automată host | StartIfRunning |
| Oprire automată host | Save |
| Secure Boot | **On**, template `MicrosoftWindows` |
| vTPM | **Activ** (cheie locală; guest vede TPM present+ready) |
| Rețea | „Default Switch" (NAT) |
| DVD | gol (fără ISO atașat) |

## 3. Stocare
- Disc: `C:\Users\cw_26\Hyper-V\ZCode-VM_6C117067-E2C8-47FD-BD65-E3601674A96B.avhdx`
- **Atenție: discul activ e AVHDX (disc diferențial)** — există datorită checkpoint-ului
  „pre-win11-upgrade". Capacitate totală 80 GB, ocupat pe host 18,8 GB.
- Checkpoint-uri existente: „Automatic Checkpoint" (11:48) și **„pre-win11-upgrade" (13:31)**
  = punctul de rollback pentru upgrade-ul Win11. Nu se șterg fără acordul lui Alexandru.
- Guest C: liber: ~49 GB.

## 4. Sistemul din guest
- **Windows 10 Pro 22H2, build 19045**, limba română.
- Cont local: **Alexandru**, parola `Alexandru2026` (grup Administrators).
- **Autologon permanent**: `HKLM\...\Winlogon` → AutoAdminLogon=1, DefaultUserName=Alexandru,
  DefaultDomainName=ZCode-VM, DefaultPassword stocat (reparat 4 oct seara — cel din instalare
  era cu contor și se epuizase; simptom: VM pornită, dar nimeni logat).
- ZCode **3.14.4** per-user: `C:\Users\Alexandru\AppData\Local\Programs\ZCode\ZCode.exe`
  (starea contului Z.ai: deconectat — buton „Connect"; fluxul pregătit = „Use API key",
  vezi secțiunea 6).
- winget ABSENT în guest (instalări doar prin installer direct).
- Chrome instalat (4 oct, de Manus).

## 5. Canale de lucru (care merg / care nu merg)
| Canal | Stare |
|---|---|
| **PowerShell Direct** (`Invoke-Command -VMName ZCode-VM -Credential Alexandru`) | ✅ canalul standard — comenzi + copiere fișiere (`Copy-Item -ToSession`), fără capturi |
| **schtasks + .bat intermediar** | ✅ obligatoriu pentru lansări în sesiunea interactivă (PS Direct pornește GUI-uri în sesiunea 0, invizibile) |
| VMConnect | ✅ pe **sesiune de bază** — „Enhanced Session Mode" a fost **dezactivat pe host** (`Set-VMHost -EnableEnhancedSessionMode $false`, 4 oct) pentru că cerea Remote Desktop (închis în guest) și respingea parola corectă |
| Start-Process GUI prin PS Direct | ❌ pornește în sesiunea 0 — nu se vede pe desktop |
| schtasks remote (`/S ZCode-VM`) | ❌ „network path not found" (SMB/RPC blocat) |

## 6. Scripturi și task-uri planificate în guest
- `C:\Users\Alexandru\launch-zcode.bat` + task **„LaunchZCode"** — pornește ZCode în sesiunea
  interactivă. Declanșarea automată a fost **dezarmată** (programat pe 01/01/2020); se rulează
  manual: `schtasks /Run /TN LaunchZCode`.
- `C:\Users\Alexandru\upgrade.bat` + task **„Win11Upgrade"** — linia de upgrade Win11
  (`setup.exe /auto upgrade /quiet /accepteula /dynamicupdate disable /product server`).
  Tot pe 01/01/2020 (dezarmat); rulează manual cu `schtasks /Run /TN Win11Upgrade`.
- Kit conectare cont ZCode: `host-cred.json` (cheia API), `paste-key.ps1`, `click.ps1`
  (fluxul vizual „Connect → Use API key → paste").
- Registry upgrade: `HKLM\SYSTEM\MoSetup\AllowUpgradesWithUnsupportedTPMOrCPU=1` +
  `HKLM\SYSTEM\Setup\LabConfig\Bypass{TPM,CPU,SecureBoot,RAM,Storage}Check=1`.

## 7. Upgrade Win11 — stadiu (oprit la cererea lui Alexandru, predat lui Manus)
- ISO construit local via UUPDump: `C:\Users\cw_26\uup-25h2\build\26100.1.240331-1435.GE_RELEASE_
  CLIENTPRO_OEMRET_X64FRE_RO-RO.ISO` = **Win11 Pro 24H2, build 26100.8972, ro-ro** (4,47 GB),
  copiat în guest ca `C:\Users\Alexandru\Win11_25H2.iso`.
- 4 încercări de lansare eșuate înainte de staging — coduri + pași următori în
  `handoff/manus-win11-upgrade-2026-10-04.md` (0xC1900200 cerințe HW, 0xC190010E EULA,
  0xC190010A nedecodat; următoarea armă: `setupprep.exe /SkipSystemRequirementScans`).
- ISO-ul local 26H2 (8,86 GB) = INTERZIS pe acest hardware (confirmat de 3 căi).

## 8. Capcane cunoscute (documentate azi)
1. `Get-VMMemory` întoarce proprietăți goale pe acest host — verificările de RAM se fac prin `Get-VM`.
2. PS Direct pornește GUI-uri în sesiunea 0 — folosește schtasks+.bat pentru ce trebuie văzut.
3. Quoting-ul /TR în schtasks strică comenzile cu citate — mereu .bat intermediar, fără citate
   interioare dacă calea are spații evitate.
4. Autologon din unattend era cu contor — epuizabil; acum e permanent (DefaultPassword în registry).
5. Stop-VM pe Win10 cu update-uri în așteptare = „Se lucrează la actualizări" la închidere/pornire —
   nu se forțează, durează câteva minute.
6. Un singur automatizator pe VM odată (Manus vs ZCode — conflict documentat 4 oct).
7. Host-ul are commit fragil (16 GB RAM) — nu crește RAM-ul VM-ului peste 6 GB fără diagnostic.

*Scris: sesiunea ZCode izz-ro, 4 oct 2026, 15:50, la cererea lui Alexandru („scriem configurația
completă a VM").*
