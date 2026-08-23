# Verificare Cloudflare — instrucțiuni pentru asistentul cu acces la API

> Scris 2026-08-23, după o migrare Pages → Workers executată parțial și cu o regresie.
> **Se citește împreună cu `infra/README-failover.md`, care e arhitectura canonică.**
> Sesiunile Claude Code pe web NU pot verifica nimic din asta singure: `api.cloudflare.com`,
> `izz.ro` și `*.pages.dev` sunt toate respinse de proxy cu `CONNECT tunnel failed, 403`
> (măsurat 2026-08-23). De aceea verificarea se delegă unui asistent cu acces direct.

## 0. Înainte de orice — rotește tokenul

Tokenul `cfat_RLfcz…` a fost lipit în clar într-un chat. Trebuie considerat compromis:
dash.cloudflare.com → My Profile → API Tokens → **Roll** pe el. Tokenul nou nu se lipește
niciodată într-un chat și nu se comite în repo — se pune în variabila de mediu
`CLOUDFLARE_API_TOKEN` local, sau în secretele GitHub Actions.

## 1. Arhitectura corectă (NU e opțiune de design, e măsurată)

```
client ── TLS ──▶ izz.ro ──▶ Worker izz-failover        ← ruta izz.ro/* stă AICI
                              ├─ 0) Cache API la edge   → header x-izz-cache: HIT/MISS/BYPASS
                              ├─ 1) primar: https://izz-ro.andifreelancer2.workers.dev (1,5s)
                              └─ 2) la 5xx/eroare/timeout → https://ramanul.github.io
```

`izz-ro` = Workers Static Assets, originea de conținut. **NU trebuie să aibă rută pe `izz.ro/*`** —
`wrangler.jsonc` din rădăcină nici nu declară vreuna, doar `workers_dev: true`. Dacă ruta e pe
`izz-ro`, se pierd trei lucruri deodată: failover-ul pe mirror, cache-ul de edge (măsurat
2026-08-17: fără el, 6 răspunsuri cache-uite din 34.419 în 7 zile = 0,02%) și headerele de
diagnostic `x-izz-origin` / `x-izz-cache`.

## 2. Verificări (READ-ONLY — rulează-le pe toate, raportează ieșirea brută)

```bash
export CF_API="https://api.cloudflare.com/client/v4"
export CF_ACCOUNT="636085fa5d41705958c81b63247026d4"
export CF_TOKEN="<tokenul NOU, din env, nu lipit in chat>"
H=(-H "Authorization: Bearer $CF_TOKEN")

# V1. Zone ID pentru izz.ro
ZONE=$(curl -s "${H[@]}" "$CF_API/zones?name=izz.ro" | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"][0]["id"])')
echo "ZONE=$ZONE"

# V2. CINE detine rutele pe zona  <-- verificarea centrala
curl -s "${H[@]}" "$CF_API/zones/$ZONE/workers/routes" \
  | python3 -c 'import sys,json;[print(r["pattern"],"->",r.get("script")) for r in json.load(sys.stdin)["result"]]'

# V3. Custom domains pe Workers (alt mecanism decat rutele; pot exista in paralel)
curl -s "${H[@]}" "$CF_API/accounts/$CF_ACCOUNT/workers/domains" \
  | python3 -c 'import sys,json;[print(d["hostname"],"->",d.get("service")) for d in json.load(sys.stdin)["result"]]'

# V4. DNS pentru izz.ro si www — tip, continut, proxied
curl -s "${H[@]}" "$CF_API/zones/$ZONE/dns_records?type=CNAME" \
  | python3 -c 'import sys,json;[print(r["name"],r["type"],r["content"],"proxied="+str(r["proxied"])) for r in json.load(sys.stdin)["result"]]'

# V5. Proiectul Pages — sursa GitHub si custom domains
curl -s "${H[@]}" "$CF_API/accounts/$CF_ACCOUNT/pages/projects/izz-ro" \
  | python3 -c 'import sys,json;p=json.load(sys.stdin)["result"];print("source:",p.get("source"));print("domains:",p.get("domains"))'

# V6. Subdomeniul workers.dev al contului (confirma numele originii primare)
curl -s "${H[@]}" "$CF_API/accounts/$CF_ACCOUNT/workers/subdomain"
```

### Ce înseamnă ieșirea de la V2

| Ce vezi | Verdict |
|---|---|
| `izz.ro/* -> izz-failover` | ✅ corect, arhitectura e intactă |
| `izz.ro/* -> izz-ro` | ❌ **regresie** — failover-ul și cache-ul de edge sunt scoase din lanț |
| `www.izz.ro/* -> izz-ro` | ⚠️ rută adăugată pe 08-23, nu e în niciun config din repo |
| nicio rută pe `izz.ro/*` | ❌ site-ul e servit de Pages sau e mort |

## 3. Testul REAL — „HTTP 200" nu dovedește nimic

Un 200 spune doar că *cineva* a răspuns, nu *cine*. Discriminatorul e manifestul
`/build.json` (generat de `generator/render.py:_write_build_metadata`, câmpuri:
`commit`, `branch`, `generated_at`, `article_count`) plus headerele Worker-ului.

```bash
CB=$(date +%s)
echo "--- izz.ro ---";        curl -s  "https://izz.ro/build.json?cb=$CB"
echo "--- primar Worker ---"; curl -s  "https://izz-ro.andifreelancer2.workers.dev/build.json?cb=$CB"
echo "--- mirror ---";        curl -s  "https://ramanul.github.io/build.json?cb=$CB"
echo "--- headere izz.ro ---"
curl -sI "https://izz.ro/?cb=$CB"                | grep -iE 'x-izz-origin|x-izz-cache|server|cf-cache-status'
curl -sI "https://izz.ro/static/styles.css"      | grep -i x-izz-cache   # ruleaza de 2x: a doua oara HIT
```

| Observație | Ce dovedește |
|---|---|
| `x-izz-origin: primary` | ✅ `izz-failover` e în lanț și primarul e sănătos |
| `x-izz-origin: mirror` | ⚠️ primarul e căzut, failover-ul a intrat — investighează `izz-ro` |
| headerele `x-izz-*` lipsesc complet | ❌ `izz-failover` NU mai e în lanț (regresia de la §2) |
| `build.json` pe izz.ro == cel de pe workers.dev | ✅ aceeași versiune servită |
| `build.json` pe izz.ro mai vechi | ❌ altcineva servește (Pages) sau cache blocat |
| `commit: "local"` | ❌ build fără metadate de CI — sondă verde-pe-nimic (eșecul din 08-21) |

## 3b. Ce s-a CONFIRMAT deja (2026-08-23, măsurat — nu re-verifica)

Verificările din §2 au fost rulate de un asistent cu acces la API, iar codul deployat a fost
citit prin conectorul MCP. Rezultatul, ca fapt stabilit:

| Ce | Măsurat | Verdict |
|---|---|---|
| `izz.ro/*` | → `izz-ro` (rută `4d10b675…`) | ❌ regresia, confirmată |
| `www.izz.ro/*` | → `izz-ro` (rută `20b10eda…`) | ❌ la fel |
| `izz-failover` | **fără nicio rută**, zero trafic | ❌ scos complet din lanț |
| Workers custom domains | niciunul în cont | traficul merge exclusiv prin rute |
| Zona `izz.ro` | activă (`5c27cb1e…`) | ✅ |

**Codul deployat pe `izz-failover` e cel din repo, curent și corect** — deci rebind-ul e sigur,
nu pui site-ul pe un Worker vechi:

| Verificat în codul deployat | Valoare | |
|---|---|---|
| `PRIMARY` | `https://izz-ro.andifreelancer2.workers.dev` | ✅ pe Worker, nu pe Pages (`df56e62`) |
| `MIRROR` | `https://ramanul.github.io` | ✅ |
| Cache API | prezent, `s-maxage` 120s HTML / 300s XML | ✅ |
| `x-izz-origin` / `x-izz-cache` | prezente | ✅ |
| Clasa DO `RateLimiter` | **absentă** | ✅ migrarea `cleanup-2026-08-22` a reușit |

Ce rămâne nemăsurat: nimeni n-a rulat încă testele HTTP din §3 — nici sesiunea web, nici
asistentul cu API nu pot ieși spre `izz.ro` sau `*.workers.dev`. **Trebuie rulate de pe mașina
proprietarului**, după reparație.

## 4. Reparația, în ordinea asta (ordinea contează)

**R1 — restaurează ruta pe `izz-failover`.** Calea curată e din repo, nu din API, fiindcă
`infra/wrangler.toml` declară deja `routes = [{ pattern = "izz.ro/*", zone_name = "izz.ro" }]`:

```bash
cd infra && CLOUDFLARE_API_TOKEN="<token nou>" wrangler deploy
```

Tokenul are nevoie de **Workers Scripts:Edit** + **Workers Routes:Edit** pe zona izz.ro.
O rută e unică per zonă → mai întâi se șterge `izz.ro/* -> izz-ro`, altfel deploy-ul se lovește de ea.

**R2 — `www.izz.ro/*` e acum în config, deci R1 o rezolvă odată cu apexul.** A fost adăugată în
`infra/wrangler.toml` pe 08-23: `www` are CNAME proxied din 20 iunie și a servit dintotdeauna
conținut, iar absența lui din config era exact gaura prin care ruta a rămas pe alt Worker.
**Deschis, decizie de proprietar:** azi `www` servește conținut duplicat, nu face 301 către apex
(`output/_redirects` n-are nicio regulă `www`). Dacă vrei 301, calea ieftină e o Redirect Rule
pe zonă — verifică întâi dacă nu există deja una, înainte s-o adaugi.

**R3 — abia apoi atinge Pages, și în ordinea asta.** Capcana: dacă `izz.ro` e înregistrat ca
*custom domain* al proiectului Pages, CNAME-ul e gestionat de Pages, iar ștergerea proiectului
poate lua cu ea înregistrarea DNS. O rută de Worker are nevoie de o înregistrare DNS **proxied**
ca să se aplice — fără ea, site-ul cade, cu tot cu rută corectă.

1. verifică V4/V5 și confirmă cine deține înregistrarea `izz.ro`;
2. dacă e a lui Pages, adaugă întâi un înlocuitor proxied (`AAAA izz.ro 100:: proxied`) SAU
   atașează `izz.ro` ca **Workers Custom Domain** pe `izz-failover`;
3. re-testează §3 și confirmă `x-izz-origin: primary`;
4. **abia apoi** deconectează sursa GitHub a proiectului Pages (oprește build-urile care pică pe
   plafonul de 20.000 de fișiere și mănâncă din bugetul de ~500 build-uri/lună);
5. ștergerea proiectului Pages e opțională și ultima — cele 1.761 de deployment-uri o blochează
   oricum, iar deconectarea sursei rezolvă problema reală.

## 5. Ce să NU faci

- **Nu declara „migrare reușită" pe baza unui HTTP 200.** Vezi §3: 200 nu spune cine a răspuns.
- **Nu muta ruta `izz.ro/*` de pe `izz-failover`.** E stratul de redundanță, nu un intermediar inutil.
- **Nu șterge proiectul Pages înainte de §4-R3.** Riști să pierzi înregistrarea DNS a apexului.
- **Nu improviza direct din API ce e declarat în `infra/wrangler.toml`.** Config drift: starea reală
  ajunge să difere de repo, iar următorul `wrangler deploy` o răstoarnă tăcut înapoi.
