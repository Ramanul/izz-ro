# §13. Verificare front-end — măsoară, nu te uita cu ochiul

> Regulă L1: nu stă în `CLAUDE.md` (care se plătește la fiecare tură), ci sosește prin hook-ul
> `PostToolUse` exact când atingi front-end-ul. Declanșator: `templates/`, `static/styles.css`,
> `generator/render.py`. Mecanismul și limitele lui: `specs/regim-reguli.md` §4.3.

- **După orice felie care schimbă output-ul de front-end** (template-uri, `static/styles.css`,
  HTML/JSON-LD din `render.py`): rulează `bash tools/audit.sh` și raportează scorurile Lighthouse
  (Perf / A11y / Best-practices / SEO) și numărul de erori pa11y WCAG2AA **înainte vs după**.
  „Arată bine" nu e un rezultat; un delta de scor e.
- **Rulează 3+ repetări per revizie și compară medianele**, cu `ARTICLE_PATH=/cat/slug/` fixat.
  Varianța e un comutator cu două stări, nu zgomot — o singură pereche înainte/după nu poate
  rezolva un efect sub ~8 puncte pe home.
- **Măsurătoarea e busolă, nu pilot automat.** Scorurile *informează* felia următoare, pe care tot
  tu o propui și proprietarul o confirmă (§5). Niciodată un maraton autonom de „optimizare", și
  niciodată vânătoare de scor cu trucuri care strică experiența reală.
- **Baseline, cifre, ipoteze picate (CLS, fonturi, consent) → `specs/masuratori-frontend.md`.**
  Citește-l ÎNAINTE de a re-investiga CLS: două explicații sunt deja măsurate și infirmate acolo.
