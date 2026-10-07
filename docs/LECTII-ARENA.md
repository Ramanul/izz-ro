# Lecții ARENA — registru separat pentru lecțiile din rundele de verificare Arena

> Separat de `nishiai-apps/docs/LECTII-TESTARE.md` (acela), la propunerea Arenei (7 oct):
> problemele specifice sandbox-ului ei (Linux, egress variabil, api.github.com) nu se
> amestecă cu regulile de testare pe Windows. Scriere: Arena raportează în chat → ZCode
> comite aici. Stările de dovadă = cele din `docs/colaborare.md` (verificat-Arena /
> verificat-ZCode / neverificat / blocat), per afirmație.
>
> Format: ID · declanșator → acțiune · baza afirmației · mecanizabil? · ultima verificare.

## Candidate (deduse de Arena la analiza din 7 oct — NICIODATĂ reproduse ca incidente)

- **AE1 · Scope de mediu** — Când Arena verifică pe Linux un comportament-țintă Windows/Edge/CfT → nu deduce comportamentul runtime din inspecția codului; marchează separat verificat-Arena (inspecție) și cere dovada ZCode pe Windows pentru afirmația de browser. *Bază: limitările sandbox-ului Arenei, constatate 7 oct. Mecanizabil: prin protocol (stări), nu script.*
- **AE2 · Egress** — Când o verificare depinde de o sursă remote → probează hostul necesar, notează rezultatul + SHA-ul conținutului; acces blocat = nu raporta verificare remote reușită. *Bază: egressul ei variază per sesiune (constatat de mai multe ori). Mecanizabil: da, în fluxul ei (probe la început de rundă).*
- **AF1 · Pin imuabil** — Când brief-ul dă SHA prescurtat sau branch → rezolvă SHA-ul complet, citește toate fișierele la acel pin, notează blob SHA-urile; branch-ul mobil nu e dovadă. *Bază: aplicat deja la analiza din 7 oct (fe70806 rezolvat la commit complet, blob-uri citate). Verificat-Arena.*
- **AF2 · Tipul dovezii** — Când se cere E2E/live dar Arena a făcut doar review de sursă → nu numi rezultatul E2E și nu transfera starea verificat-Arena către ZCode; scrie explicit ce pas runtime lipsește. *Bază: clasa de fals-pozitiv din F2, vedere din partea ei. Mecanizabil: prin formatul de raport.*
- **AF3 · Falsificarea rezultatului** — Când se testează o poartă ON/OFF → testează ambele direcții + dovedește că fixture-ul, scriptul și observatorul au rulat; lipsa semnalului = „neconcludent", nu „trecut". *Extinde F2. Mecanizabil: parțial — în testele de produs.*

## Istorie
- 2026-10-07: registru creat la decizia lui Alexandru („implementează tot"); candidaturile AE/AF populate din analiza Arenei (`sonde/arena-lectii-raspuns-2026-10-07.txt`).
