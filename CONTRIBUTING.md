# Contributing — izz-ro

> Generatorul site-ului izz.ro: pipeline Python → site static → Cloudflare Workers (+ mirror
> GitHub Pages). Repo public; coordonarea merge prin `specs/STATE.md`, nu prin chat.

## Înainte de orice

1. Citește `CLAUDE.md` din rădăcină — contractul complet de operare.
2. Citește `AGENTS.md` — rolul de executor, branch discipline, fișiere intangibile.
3. `specs/STATE.md` spune unde suntem; `specs/registru.tsv` ține deciziile.

## Reguli care nu se negociază

- **Nimic direct pe `main`.** Fiecare sarcină = un branch nou din `origin/main` proaspăt,
  o felie verticală, commit pe verde, apoi stop. Merge-ul îl face managerul.
- **Verifică, nu afirma.** „Merge" e valid doar după ce ai rulat comanda și ai văzut-o
  trece. Comenzile: `python -m generator.main` (pipeline complet), `--dry-run`,
  `--render-only`, `python -m pytest tests/ -q`, `python -m ruff check .`.
- **Fișierele pe care nu le-ai creat sunt intangibile.** Fără `git restore`/`stash`/`clean`
  pe munca altcuiva; un working tree murdar nu e o problemă de reparat.
- **Fără headline-uri trunchiate sau brute în output** — regula „Zero Zgomot".
- **Nu edita de mână** `data/articles.json` (stare de pipeline) și `moderation.yaml`.

## Spec înainte de cod

3–8 linii: scop, intrări/ieșiri, criterii de acceptanță. Fără spec → fără cod. Dacă spec-ul
e ambiguu, întreabă — nu improviza scope.

## Securitate

Nu publica niciodată nimic singur. Vulnerabilitățile se raportează privat (butonul
„Privately report a vulnerability" al repo-ului) sau la `/.well-known/security.txt`.

## Colaborare Arena ↔ PC

Sincronizarea se face prin ramuri Git și PR-uri; nu există runner self-hosted pentru PC în acest repo.
Pașii sunt în [`handoff/arena-pc-collaboration.md`](handoff/arena-pc-collaboration.md).
