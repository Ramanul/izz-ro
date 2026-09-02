# §18 — Imagini de instituții locale: condiționate de consimțământ

> **Regulă L1** (decizie proprietar 2026-07-24). Nu stă în `CLAUDE.md` fiindcă se aplică doar când
> atingi calea imaginilor; hook-ul `PostToolUse` o livrează atunci. Numele „§18" e păstrat: e citat
> în jurnale și în registru. **Limita ei, scrisă lângă ea:** hook-ul se aprinde pe fișier, iar
> regula are și o latură conversațională (cineva propune o poză fără să atingă nimic) — de-aia
> `CLAUDE.md §18` păstrează cârligul care trimite aici.

- **Finanțarea din taxe NU pune fotografiile unei instituții în domeniul public.** „Public pe
  site-ul lor" ≠ liber de reutilizat. Legea 8/1996 art. 9 eliberează **TEXTUL** actelor oficiale —
  NU fotografiile.
- **O poză făcută de un angajat al primăriei e opera INSTITUȚIEI:** ea e titularul și ea trebuie să
  acorde reutilizarea. O poză de la un fotograf contractat sau o agenție (Agerpres/Mediafax)
  aparține terțului.
- **Prezența unui ales reduce *dreptul lui la imagine*, nu *dreptul de autor al fotografului*.**
  Cele două nu se confundă și nu se compensează.
- **Nu improviza fapte juridice.** Pentru orice operațional, proprietarul confirmă cu un avocat.
- **Trei căi, oricare, verificată și CONSEMNATĂ (link + citat):** (1) instituția publică termeni de
  reutilizare / licență deschisă care acoperă imaginile, SAU (2) există portret/poză
  liber-licențiată pe Wikidata / Wikimedia Commons (calea existentă — `fetch_leadphotos.py` PD/CC0,
  `fetch_portraits.py` CC-BY), SAU (3) instituția a dat permisiune scrisă de reutilizare.
- **Fără scraping în bloc pe site-uri de instituții.** Lipsesc toate trei → articolul își păstrează
  coperta generată.
- **Dovada se strânge într-un whitelist pe care proprietarul (sau juristul) îl aprobă ÎNAINTE** de
  a trage vreo imagine — om în buclă, ca `moderation.yaml`.
