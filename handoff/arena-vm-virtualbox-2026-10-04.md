# Brief pentru Arena — Windows 11 în VirtualBox „ZCode-VM" (4 oct 2026)

## Scopul (de ce există VM-ul ăsta)
ZCode (aplicația de agenți) trebuie să ruleze ÎN INTERIORUL unui VM Windows, ca agentul să aibă
cursor propriu separat de cel al lui Alexandru pe host. VM: VirtualBox 7.2.20, „ZCode-VM",
Windows11_64, EFI, 8 vCPU, 8 GB RAM, disc 80 GB VDI, TPM 2.0. Host: ASUS X99 + Xeon E5 v4,
16 GB RAM, **Hyper-V activ pe host** (VirtualBox rulează în modul „native API", lent — confirmat
în status bar: Paravirtualization Interface: Hyper-V). Cont local VM: Alexandru / parola e în
memoria proiectului (virtualbox-zcode-vm-2026-10-03.md), nu o repetez aici.

## Tot ce am încercat azi (cronologic, cu rezultate)
1. VM pornit → `BdsDxe: No bootable option or device was found`. Disc ATAȘAT (SATA-0-0 =
   ZCode-VM.vdi, „locked write"), boot order dvd→disk.
2. Boot Manager EFI → intrarea „UEFI VBOX HARDDISK VB04cb1ac4" vizibilă; boot direct pe ea →
   dialoguri VirtualBox „The virtual machine failed to boot".
3. EFI File Explorer → Boot From File → partiția ESP „EFI," (HD(2,GPT,F47C192A-1FDF-461F-85CB-
   55E5A1A200BF)) listată **GOLĂ**.
4. Boot din ISO Win11 ro-ro (CCCOMA_X64FRE, montat pe SATA-1-0). Shift+F10 în Setup → cmd
   Administrator (X:\sources>). Layout guest = Romanian Standard: `:` = Shift+0x34, `\` =
   AltGr+0x2B, `/` = 0x35, 0x27 = „ș". (Maparea am testat-o cu probe echo, e confirmată.)
5. diskpart: `list disk` → Disk 0, 80 GB, Online, GPT*. `list vol` → **Volume 3 C „Windows"
   NTFS 79 GB Healthy; Volume 4 WINRE NTFS 300 MB; Volume 5 EFI FAT32 100 MB — toate Healthy**.
6. `dir C:\` → „File Not Found" — **rădăcina e GOALĂ**. `dir S:\` (ESP) → gol.
   `dir C:\Windows\Boot\EFI` → „The system cannot find the path specified".
7. `bcdboot C:\Windows /s S: /f UEFI` → **„Failure when attempting to copy boot files"** (sursa
   lipsește). ⇒ **Concluzie: discul e partiționat+formatat dar niciodată populat cu Windows.**
   „Instalarea terminată" de 3 oct NU e pe discul ăsta. (Suspect: sesiunea de 3 oct a instalat
   în VM-ul Hyper-V „ZCode-VM on SAN" — fereastra vmconnect există deschisă pe host — sau
   discul a fost recreat între timp.)
8. Re-rulat rețeta care a „câștigat" 3 oct: `VBoxManage unattended install ZCode-VM --iso=
   "C:\Users\cw_26\VirtualBox VMs\Win11.iso" --user=Alexandru --password=... --full-user-name=
   "Alexandru Stanciu" --time-zone=Europe/Bucharest` (FĂRĂ --locale; ro-RO dădea E_INVALIDARG).
   Pornit VM + injecție Enter la poarta „press any key" (scancode 1c 9c).
9. **Boot loop înghețat:** BdsDxe „failed to load Boot0002 UEFI VBOX HARDDISK ... : Not Found",
   spinner peste logo, ECRAN NEMODIFICAT 30 min (PNG constant), proces VM ardând CPU (~3 nuclee).
   ⇒ diagnostic: NVRAM-ul EFI păstra ordinea veche (disc primul), intra în buclă disc-gol↔DVD.
10. **Fix aplicat:** VM oprit, procese VirtualBoxVM zombie ucise, **ZCode-VM.nvram ȘTERS**
    (EFI reconstruiește ordinea: DVD primul), repornit + spam Enter pe poartă. Acum: spinner
    WinPE ANIMAT (PNG variază), aștept Setup-ul unattended. [ÎN DESFĂȘURARE la scrierea brief-ului]

## Întrebările pentru Arena
a. Există un drum MAI FIABIL decât unattended pentru Win11 în VirtualBox 7.2.20 cu Hyper-V pe
   host? (downgrade VirtualBox 7.0.x? dezactivare Hyper-V? — dar Hyper-V e folosit de alt VM,
   „ZCode-VM on SAN" — întreb pe cine deranjează dezactivarea)
b. După instalare: cel mai scurt drum la „ZCode funcțional în VM": Guest Additions → guestcontrol
   → winget install ZhipuAI.ZCode + copiere credentials din host (~/.zcode/v2/credentials.json).
   Veziți capcane cunoscute (credentials rotation dacă host+guest folosesc același token?)
c. Tastatura injectată (keyboardputscancode) moare după tranziții de stare în guest (firmware→
   setup, diskpart ocupat) — e bug cunoscut? fix?
d. Instalarea unattended de 3 oct a „confirmat desktop" dar discul e gol azi — ce s-a putut
   întâmpla? (2 mecanisme candidate: alt VM / disc recreat. Cum le disting post-factum?)

## Constrainte
$0 buget; host-ul rămâne utilizabil de Alexandru în timpul instalărilor; nu se stresează pași
care îi mișcă cursorul (preferință: scancodes + screenshotpng din hipervisor, invizibile).

---
*Scriere: sesiunea ZCode din izz-ro, 4 oct 2026, în timp ce instalarea unattended curge.*
