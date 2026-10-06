# Protocol de colaborare — izz.ro (Arena ↔ ZCode ↔ Alexandru)

> Versiune: 2026-10-06 v1 — născută din analiza mutuală a resurselor (sesiunea Arena 01a10d08)
> și rafinată cu opiniile Arenei (sesiunea 01a10f08).
> Arena: sesiunile tale pornesc fără memorie. Acest fișier este contractul de colaborare.
> Dovada de citire = citezi SHA-ul acestui fișier în prima propoziție a răspunsului.

## Roluri

- **Alexandru** — proprietar de produs: scop, priorități, buget, risc. **Singura poartă de
  merge/deploy** — aprobare explicită per schimbare; tăcerea nu înseamnă aprobare; aprobarea
  nu se moștenește între sesiuni.
- **Arena** — cercetare, plan, execuție izolată pe branch, raportare onestă.
- **ZCode (sesiunea principală)** — spec-uri, verificare locală și în browser real,
  integrare (merge după aprobarea lui Alexandru), raportare în ambele sensuri.
- **Devin / OpenCode** — executori pe sarcini bine specificate (regulile lor: `AGENTS.md`,
  secțiunea EXECUTOR).

## Reguli de lucru

1. Nimic direct pe `main`. Branch separat per unitate logică, pornit din SHA-ul de bază
   numit în brief. Niciun agent nu lucrează pe branch-ul altuia.
2. **Brief unic self-contained**: obiectiv, criterii de acceptare, non-obiective, fișiere
   vizate, buget, cine verifică ce, cine aprobă.
3. **Dovezi, nu afirmații**: comenzi rulate + rezultate; separă explicit „am observat
   direct" / „din artefacte publice" / „neverificat".
4. Cele **4 stări de verificare** în orice raport: verificat-Arena · verificat-ZCode ·
   neverificat · blocat.
5. **Verificare încrucișată**: agentul care n-a implementat verifică pe același SHA;
   autorul contestă constatările doar cu dovezi.
6. **Merge/deploy = poartă explicită**: doar cu „da"-ul lui Alexandru pentru acțiunea
   respectivă.
7. **Escaladare imediată** la: costuri, secrete, licențe, decizii editoriale, risc de
   producție, operațiuni distructive, conflicte între cerințe.
8. **Fără secrete sau date sensibile** în fișiere publice — inclusiv în acest fișier și în
   notițele de handoff.
9. Domeniu izz.ro: niciun headline brut/trunchiat în output — itemii stricați se sară
   („Zero Zgomot").

## Accesul Arena la repo (procedura de conectare)

- **Sesiune de LUCRU** (cod pe branch/PR): Alexandru o conectează la creare prin
  *Add files and connections* → `Ramanul/izz-ro`. Fără conectare, sesiunea are doar citire
  publică — atunci spune explicit în raport „nu am drept de scriere", nu improviza.
  **Conectare automată la nivel de cont NU există pe platformă** (verificat 6 oct 2026:
  UI + documentația Agent Mode + Arena). Continuările aceleiași lucrări merg pe sesiunea
  existentă conectată („Keep working"); după merge/închiderea unui PR, sesiunea pierde
  dreptul de push — reconectare sau sesiune nouă.
- **Sesiune de ANALIZĂ/cercetare**: rămâne doar-citire publică — nu are nevoie de acces de
  scriere.
- Dacă un livrabil rămâne blocat în workspace (fără push posibil): listează în raport
  fișierele + SHA-urile; ZCode le preia prin mecanismul de descărcare al platformei și le
  verifică local.

## Comunicare

- **Șablon de brief** (prima linie obligatorie, scrisă în `AGENTS.md` § Arena):
  „Citește mai întâi `docs/colaborare.md` din `Ramanul/izz-ro`; citează SHA-ul fișierului
  în răspuns." URL direct:
  `https://github.com/Ramanul/izz-ro/blob/main/docs/colaborare.md`
- **Fallback**: dacă citirea publică e blocată în sesiunea ta, ceri textul condensat;
  răspunsul marchează „bazat pe paste, neverificat contra repo". Dacă nu ai nici textul,
  ceri protocolul — nu improvizezi din memorie și nu pretindezi verificare.
- **Raportul final**: verdict într-o propoziție + cele 4 stări + blocaje + pasul următor
  cu owner-ul lui.
- **Stări partajate**: `sonde/arena-chat-state.json` — un singur scriitor pe rundă.
- **Handoff (9 câmpuri)**: ID/obiectiv · bază+SHA final · modificat/produs · verificat
  (comenzi, mediu, rezultate) · neverificat/presupuneri · cost/riscuri/decizii cerute ·
  blocaje · următoarea acțiune + owner · aprobări încă necesare.

## Istoric

- 2026-10-05/06: protocol născut din analiza mutuală a resurselor; rafinări: URL direct +
  ref în linia de brief, SHA complet + blob, fallback marcat „neverificat contra repo",
  tăcerea ≠ aprobare, fără secrete în fișierul public.
