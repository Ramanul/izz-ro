# Instrucțiuni: readu rutele izz.ro pe `izz-failover`

> Pentru un asistent/operator **cu acces de scriere la API-ul Cloudflare**. Sesiunile Claude Code pe
> web NU pot executa asta: `api.cloudflare.com` întoarce `CONNECT tunnel failed, 403` prin proxy, iar
> conectorul MCP expune pentru Workers doar `list` / `get` / `get_code`. Măsurat 2026-09-06.

## Sarcina, într-o frază

Mută rutele `izz.ro/*` și `www.izz.ro/*` de pe Worker-ul `izz-ro` înapoi pe `izz-failover`, lăsând
`izz-ro` **fără nicio rută**, și dovedește rezultatul cu headerele `x-izz-*`, nu cu un cod HTTP.

## De ce — și de ce citești asta a doua oară

Aceeași regresie s-a produs de două ori, prin exact același raționament greșit:

| Data | Ce s-a făcut | Cum s-a declarat reușită | Decizie |
|---|---|---|---|
| 2026-08-23 | ruta `izz.ro/*` mutată `izz-failover` → `izz-ro` | `HTTP 200` pe `https://izz.ro` | IZZ-0237 |
| 2026-09-06 04:31 | aceeași mutare, plus `www.izz.ro/*` | `HTTP 200` pe `https://izz.ro` | IZZ-0308 |

**Un `200` spune că a răspuns *cineva*, nu *cine*.** Ambele Worker-uri servesc același conținut, deci
ambele întorc `200` cu HTML valid. Codul de stare nu distinge configurația corectă de cea stricată —
de asta a trecut de două ori.

Ce se pierde când ruta stă pe `izz-ro`:

- **failover-ul pe mirror** — `izz-failover` încearcă `PRIMARY` cu timeout de 1500 ms și cade pe
  `https://ramanul.github.io` la 5xx/eroare/timeout. Fără el, o cădere a originii primare = site căzut.
- **cache-ul de edge** — Cache API din Worker, `s-maxage` 120 s pentru HTML și 300 s pentru XML.
  Măsurat 2026-08-17 fără el: **6 răspunsuri cache-uite din 34.419 în 7 zile (0,02%)**.
- **headerele de diagnostic** — `x-izz-origin` (`primary`/`mirror`) și `x-izz-cache`
  (`HIT`/`MISS`/`BYPASS`). Fără ele nicio sondă nu mai poate spune cine servește.

## Starea de la care pleci (măsurată 2026-09-06)

| Ce | Valoare |
|---|---|
| Worker `izz-failover` | id `b9119466c67b4c8ea855bac42b0b5162`, creat 2026-07-24 |
| Worker `izz-ro` | id `e7b5cf861f2849f3aae3249629321b03`, Static Assets, creat 2026-08-22 |
| Rute pe `izz-ro` acum | `izz.ro/*` și `www.izz.ro/*` — **de mutat** |
| Rute pe `izz-failover` acum | niciuna — **de restaurat** |
| Zonă | `izz.ro` |
| `PRIMARY` în `failover-worker.js:28` | `https://izz-ro.andifreelancer2.workers.dev` |
| `MIRROR` în `failover-worker.js:29` | `https://ramanul.github.io` |

`izz-ro` este **originea primară**, nu un concurent: `izz-failover` îl consumă prin `workers.dev`.
De asta `izz-ro` trebuie să rămână publicat pe `workers.dev`, dar **fără rute pe domeniu**.

## Precondiții — verifică-le ÎNAINTE de orice scriere

Nu sări peste pasul 1. Riscul real nu e ruta, ci ca `izz-failover` să ruleze cod vechi care
fetch-uiește o origine moartă: atunci rebind-ul mută site-ul pe nimic.

1. **Codul deployat pe `izz-failover` țintește originea vie.** Citește-l și confirmă că `PRIMARY`
   este `https://izz-ro.andifreelancer2.workers.dev`. Dacă găsești `izz-ro.pages.dev` (host retras),
   **OPREȘTE-TE**: întâi redeployează Worker-ul din `infra/failover-worker.js`, abia apoi rebind.
2. **Originea primară răspunde**, direct, ocolind domeniul:
   `curl -sS -o /dev/null -w '%{http_code}\n' https://izz-ro.andifreelancer2.workers.dev/` → `200`.
3. **DNS-ul e proxied.** O rută de Worker se aplică **doar** peste o înregistrare DNS proxied
   (nor portocaliu) pentru `izz.ro` și `www.izz.ro`. Fără asta ruta se creează, dar nu prinde niciodată.

## Acțiunea

Ordinea contează: creezi ruta nouă înainte să o ștergi pe cea veche, ca să nu existe fereastră fără rută.

**Prin dashboard:** Workers & Pages → `izz-failover` → Settings → Domains & Routes → Add route
(`izz.ro/*`, zonă `izz.ro`), apoi din nou pentru `www.izz.ro/*`. Apoi Workers & Pages → `izz-ro` →
Settings → Domains & Routes → șterge `izz.ro/*` și `www.izz.ro/*`. **Nu** atinge subdomeniul
`workers.dev` al lui `izz-ro` — acolo e originea.

**Prin API** (`<zone_id>` = zona `izz.ro`):

```bash
# 1. Ce rute există acum, și pe ce script
curl -sS -H "Authorization: Bearer $CF_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/<zone_id>/workers/routes" | jq '.result[]'

# 2. Repointează fiecare rută pe izz-failover (PUT pe id-ul existent, nu POST)
curl -sS -X PUT -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/<zone_id>/workers/routes/<route_id_apex>" \
  --data '{"pattern":"izz.ro/*","script":"izz-failover"}'

curl -sS -X PUT -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/<zone_id>/workers/routes/<route_id_www>" \
  --data '{"pattern":"www.izz.ro/*","script":"izz-failover"}'

# 3. Confirmă că izz-ro a rămas fără rute
curl -sS -H "Authorization: Bearer $CF_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/<zone_id>/workers/routes" \
  | jq '[.result[] | select(.script=="izz-ro")]'   # trebuie []
```

`PUT` pe ruta existentă e preferabil unui `DELETE` + `POST`: schimbă scriptul fără să lase domeniul
descoperit între cele două apeluri.

## Verificarea care chiar dovedește

**Nu raporta „reușit" pe baza unui cod HTTP.** Rulează, de pe o mașină cu ieșire la internet:

```bash
bash infra/verifica-live.sh
```

Trebuie să vezi **toate** cele trei:

1. `x-izz-origin: primary` — `izz-failover` e în lanț și primarul răspunde.
   Dacă headerele `x-izz-*` **lipsesc**, ruta nu a prins: nu e reparat, indiferent ce cod HTTP vezi.
   Dacă apare `x-izz-origin: mirror`, ruta e corectă dar **originea primară e căzută** — investighează
   `izz-ro`, nu rutele.
2. `x-izz-cache: HIT` la a doua cerere pe același asset. Testează cu **GET**, nu `curl -I`:
   `isCacheableRequest()` respinge orice metodă ≠ GET și întoarce `BYPASS` prin proiectare — o sondă
   cu `-I` nu poate raporta `HIT` oricât de sănătos ar fi cache-ul (IZZ-0240, măsurătoare falsă deja
   consemnată).
3. `/build.json` cu **același `commit`** pe `https://izz.ro` și pe origine, și diferit de `local`.
   Un `commit: "local"` înseamnă build fără metadate de CI — sondă verde pe nimic.

Echivalentul manual, dacă nu poți rula scriptul:

```bash
curl -fsS -o /dev/null -D - "https://izz.ro/?cb=$(date +%s)" | grep -i '^x-izz-'
curl -fsS "https://izz.ro/build.json?cb=$(date +%s)" | jq -r .commit
curl -fsS "https://izz-ro.andifreelancer2.workers.dev/build.json?cb=$(date +%s)" | jq -r .commit
```

## Dacă ceva merge prost

Rollback: `PUT` înapoi cu `"script":"izz-ro"` pe aceleași id-uri de rută. Site-ul redevine
funcțional imediat (fără failover și fără cache, adică starea de dinaintea reparației) — deci un
eșec nu lasă domeniul căzut.

Simptom → cauză:

| Ce vezi | Ce înseamnă |
|---|---|
| headerele `x-izz-*` lipsesc, dar site-ul merge | ruta nu a prins — verifică DNS-ul proxied |
| `x-izz-origin: mirror` persistent | `izz-ro` nu răspunde pe `workers.dev` — repară originea |
| `502`/`523` după rebind | `izz-failover` rulează cod cu `PRIMARY` mort — redeployează din repo |
| commit-uri diferite domeniu vs. origine | edge cache vechi; reia peste 2 minute cu `?cb=` nou |

## Ce să NU faci

- **Nu declara reușită migrarea pe baza unui `HTTP 200`.** Asta a cauzat ambele regresii.
- **Nu adăuga rute pe `izz-ro`.** `wrangler.jsonc` e assets-only și **nu declară nicio rută** —
  orice rută pusă acolo manual e orfană față de repo și dispare la următorul deploy.
- **Nu șterge custom domain-ul `izz.ro` din proiectul Pages.** Ruta de Worker are prioritate și îl
  scurtcircuitează oricum; ștergerea lui poate lua cu ea CNAME-ul de apex.
- **Nu atinge subdomeniul `workers.dev` al lui `izz-ro`** — sondele (`visual`, `monitor`,
  `harta-smoke`) au nevoie de o origine fără bot challenge, iar zona `izz.ro` are challenge activ.
- **Nu porni Bot Fight Mode / reguli WAF noi „ca să repari" 403-uri.** Sunt deja active de pe
  2026-09-05, iar o parte din 403-uri sunt chiar efectul lor (IZZ-0310).

## Config drift de rezolvat separat

`infra/wrangler.toml` declară o singură rută:

```toml
routes = [
  { pattern = "izz.ro/*", zone_name = "izz.ro" }
]
```

`www.izz.ro/*` **lipsește**, deși `www` are CNAME proxied din 20 iunie și servește dintotdeauna
conținut. Absența lui din config e exact gaura prin care ruta `www` a putut rămâne pe alt Worker
fără ca nimeni să observe. După reparare, adaugă-l în `toml` printr-un PR — altfel următorul
`wrangler deploy` din `infra/` revendică doar apex-ul.

*Deschis, decizie de proprietar:* azi `www` servește conținut duplicat în loc să facă 301 către apex
(`output/_redirects` nu are nicio regulă `www`).
