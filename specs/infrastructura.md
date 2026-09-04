# FAPTE CURENTE de infrastructură — injectate la pornire

> **De ce există fișierul ăsta, scris ca să nu fie șters ca redundant.** Hook-ul `SessionStart`
> injectează din registru doar stările ÎNCHISE (`respins`, `anulat`, `masurat-fals`, ...). Deci
> fiecare sesiune primea lista lucrurilor FALSE și niciodată lista lucrurilor ADEVĂRATE: un fapt
> pozitiv se consemnează ca `implementat`, stare pe care hook-ul n-o injectează — invizibil prin
> construcție, nu din vechime. Măsurat de două ori: pe 2026-08-23 o sesiune a pus proprietarul să
> reverifice planul Cloudflare, iar pe 2026-09-02 alta a făcut exact la fel, deși răspunsul era
> comis de 10 zile. Ambele au căutat corect și n-au găsit, fiindcă nu era unde se caută.
>
> **Plafon: 24 linii de fapt.** Verificat de `tests/test_reguli.py`, care citește cifra din rândul
> ăsta. Marja e mică deliberat: un fapt nou intră ușor, o listă în creștere nu. Se plătește o dată
> pe sesiune, nu la fiecare tură — dar tot se plătește.
>
> **Fiecare rând citează un `IZZ-####` care există în registru — impus de aceeași gardă.** Ăsta e
> antidotul la fosilizare: `IZZ-0257` s-a născut dintr-o afirmație lăsată în README fără dată și
> fără dovadă, iar nimeni n-a putut spune când fusese adevărată. Un fapt care se schimbă se
> înlocuiește AICI, în aceeași tură cu rândul nou de registru — nu se lasă să se contrazică.
>
> Ce NU intră aici: istoric, ce s-a încercat, ce a picat (→ registru), unde suntem cu munca
> (→ `specs/STATE.md`), reguli care obligă la o acțiune (→ `CLAUDE.md`).

- **Gazda e Cloudflare Workers Static Assets, NU Pages** — migrat în #211 pe 2026-08-22;
  `wrangler.jsonc` assets-only, fără `main`. Check-ul de pe PR-uri se numește
  `Workers Builds: izz-ro`. [IZZ-0258]
- **Contul e Workers PAID.** Plafonul de fișiere statice e 100.000/versiune (free ar fi 20.000);
  `config.py:363 OUTPUT_FILE_BUDGET=90000` e dimensionat pe el. Plafonul de 500 build-uri/lună al
  lui Pages NU se mai aplică — Workers n-are așa ceva. [IZZ-0305]
- **Constrângerea reală de creștere e NUMĂRUL DE FIȘIERE, nu lățimea de bandă și nu build-urile.**
  Randare 2026-09-02: 43.148 fișiere la 11.867 articole. Fereastra TTL plină proiectează ~70.000,
  deci se apropie de plafonul plătit. Decizie deschisă a proprietarului. [IZZ-0237, IZZ-0238]
- **Allowlist-ul proxy-ului e PER-HOST și diferă între sesiuni** — nu se citează din memorie, se
  măsoară cu `bash tools/verify_allowlist.sh`. `izz-ro.andifreelancer2.workers.dev` trece; alte
  hosturi `workers.dev`, preview-urile de PR și `api.cloudflare.com` nu. [IZZ-0247, IZZ-0248]
- **Sursele de știri sunt inaccesibile din orice sesiune** — limita e a sesiunii, nu a proiectului;
  runnerele le văd. Poarta autoritară pentru feed-uri e `feedcheck.yml`. [IZZ-0257]
- **Repo-ul e PUBLIC** ⇒ minute Actions gratuite și nelimitate. Timpul de job nu e o resursă de
  economisit; build-urile Cloudflare și cuota AI sunt. [IZZ-0139]
