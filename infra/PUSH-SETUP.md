# Alerte de ultimă oră (Web Push, VAPID) — ce lipsește și cum îl pornești

Totul e **gratuit**: Cloudflare Workers Free + Workers KV Free, zero servicii terțe, zero
costuri pe abonat. Codul e deja în repo; ce lipsește sunt niște **chei pe care doar tu le
poți pune** (nu au ce căuta în git).

Până nu sunt puse, **nimic nu se strică**: rutele răspund `503` cu un mesaj în română,
butonul de alerte arată „Alertele nu sunt pornite pe server în acest moment", iar site-ul
funcționează exact ca înainte. Poți face merge liniștit și configura după aceea.

---

## 1. Lista scurtă — ce lipsește ACUM

| # | Ce | Unde se pune | Obligatoriu pentru |
|---|---|---|---|
| 1 | namespace KV `PUSH_SUBS` | `wrangler.jsonc` (blocul comentat) | abonări, trimitere |
| 2 | `VAPID_PUBLIC_KEY` | `wrangler secret put` | orice alertă |
| 3 | `VAPID_PRIVATE_KEY` | `wrangler secret put` | orice alertă |
| 4 | `VAPID_SUBJECT` | `wrangler secret put` | orice alertă |
| 5 | `PUSH_ADMIN_TOKEN` | `wrangler secret put` + `.env` local | trimiterea (nu abonarea) |

Fără 1: `/push/abonare` și `/push/trimite` → `503`. Fără 2–4: toate rutele → `503`.
Fără 5: abonările merg, trimiterea refuză cu `401`.

---

## 2. Namespace-ul KV (abonamentele)

```bash
npx wrangler kv namespace create PUSH_SUBS
```

Comanda întoarce un `id`. Apoi, în `wrangler.jsonc`, **decomentează** blocul de lângă
`assets` și pune id-ul:

```jsonc
"kv_namespaces": [
  { "binding": "PUSH_SUBS", "id": "<id-ul întors mai sus>" }
],
```

De ce e comentat în PR și nu scris direct: un `id` de placeholder face **deploy-ul să
pice** (namespace inexistent), iar PR-ul trebuia să poată fi publicat înainte să faci tu
pasul ăsta.

În KV ajung **doar datele tehnice ale abonamentului**: endpointul de push și cele două
chei ale lui. Niciun nume, niciun e-mail, niciun IP (nu e scris în cod), niciun profil de
cititor — alerta e aceeași pentru toți, cel mult o dată pe zi.

---

## 3. Cheile VAPID (identitatea site-ului față de serviciul de push)

Varianta scurtă, fără să instalezi nimic:

```bash
npx -y web-push generate-vapid-keys
```

Întoarce două valori `base64url`. Sau, din `openssl`:

```bash
openssl ecparam -name prime256v1 -genkey -noout -out vapid.pem
openssl ec -in vapid.pem -pubout -outform DER | tail -c 65 | base64 | tr '/+' '_-' | tr -d '=\n'
# cheia privată (32 de octeți, base64url):
openssl ec -in vapid.pem -outform DER 2>/dev/null | openssl asn1parse -inform DER -strparse 16 -noout -out - | tail -c 32 | base64 | tr '/+' '_-' | tr -d '=\n'
```

Apoi, în directorul repo-ului:

```bash
npx wrangler secret put VAPID_PUBLIC_KEY     # lipește cheia publică  (65 de octeți)
npx wrangler secret put VAPID_PRIVATE_KEY    # lipește cheia privată  (32 de octeți sau PEM PKCS#8)
npx wrangler secret put VAPID_SUBJECT        # mailto:contact@izz.ro  (sau https://izz.ro)
npx wrangler secret put PUSH_ADMIN_TOKEN     # un șir lung, generat de tine (ex: openssl rand -hex 32)
```

`VAPID_PRIVATE_KEY` se acceptă în **ambele forme** — `base64url` brut (32 de octeți) sau
PEM — tocmai pentru că se lipește manual și o formă greșită ar produce `503` pe toate
rutele, fără niciun alt simptom.

`PUSH_ADMIN_TOKEN` nu e o parolă de utilizator: e cheia cu care **tu** (sau un job)
declanșezi trimiterea. Pune-l și în `.env`, local, ca să meargă unealta:

```
PUSH_ADMIN_TOKEN=...
PUSH_URL=https://izz.ro        # implicit; schimbă-l doar dacă probezi pe alt deployment
```

---

## 4. Cum trimiți o alertă

```bash
# câți abonați sunt + când s-a trimis ultima dată
python tools/alerta_push.py --stare

# repetiție: validează politica și numără destinatarii, NU trimite, NU consumă ziua
python tools/alerta_push.py --uscat \
  --titlu "Guvernul a publicat ordonanța cu noile salarii din sănătate" \
  --text  "Documentul stabilește creșteri eșalonate începând cu 1 ianuarie." \
  --url   "https://izz.ro/economic/cresteri-salariale-sanatate/"

# de-adevăratelea
python tools/alerta_push.py --titlu "..." --text "..." --url "..."
```

Regulile sunt aplicate de **server**, nu de unealtă (un client care le-ar aplica singur
poate fi ocolit cu un `curl`):

- **maximum o alertă pe zi** — cheia `cap:<data>` în KV, scrisă *înainte* de trimitere;
- **politica «Zgomot zero»** (`infra/push.js::verificaAlerta`): fără `!`, `?`, `…`, emoji,
  majuscule strigate, cuvinte-momitoare; textul între 30 și 200 de caractere; URL-ul
  trebuie să fie pagina articolului, fără parametri de urmărire;
- **abonamentele moarte** (404/410 de la serviciul de push) se șterg singure.

Refuzul vine cu motive în română și cod `422` (politică) sau `409` (zi deja consumată).

---

## 5. Cât încape, pe planul Free

Cifrele sunt de pe `developers.cloudflare.com/workers/platform/pricing/` și
`/kv/platform/limits/`, citite la 2026-10-03. De ele depinde forma codului:

| Limită (Free) | Valoare | Ce înseamnă pentru alerte |
|---|---|---|
| CPU per invocare Worker | **10 ms** | trimiterea e **pe loturi de 40**, cu cursor — unealta reia singură |
| Cereri Worker | 100.000/zi | rutele de push sunt neglijabile pe lângă trafic; activele statice nu se numără |
| KV citiri / scrieri / ștergeri / listări | 100.000 / 1.000 / 1.000 / 1.000 pe zi | o alertă pe zi = 1 listare + N citiri + 1 scriere; abonările NU rescriu dacă există deja |
| KV stocare | 1 GB | ~1 KB per abonament → sute de mii de abonați |

**Riscul real pe planul Free nu e traficul, e cineva care golește plafonul de 1.000 de
scrieri/zi** cu POST-uri repetitive. De aceea endpointurile de push sunt validate contra
unei liste de servicii cunoscute (FCM, Mozilla, Apple, Windows) și de aceea re-abonarea
aceluiași dispozitiv nu scrie a doua oară.

---

## 6. Cine are voie la ce (autorizare)

Cinci rute, două niveluri. Regula după care sînt împărțite: **tot ce ține de cititor e
deschis** (altfel opt-in-ul n-ar funcționa — browserul telefonului nu are și nici nu poate
avea o cheie de admin), iar **tot ce poate consuma cota zilnică sau poate scrie în numele
site-ului e sub token**.

| Rută | Metodă | Autorizare | De ce |
|---|---|---|---|
| `/push/cheie` | GET | **public** | e cheia publică VAPID; browserul o cere înainte de abonare. N-are nevoie de KV, deci funcționează și pe un deployment neconfigurat. |
| `/push/abonare` | POST | **public, prin design** | e însuși opt-in-ul cititorului. O cheie de admin aici ar însemna ca tot site-ul să poarte secretul. |
| `/push/dezabonare` | POST | **public** | șterge doar cheia endpointului primit: nu poți dezabona pe altcineva fără să-i ai endpointul. |
| `/push/stare` | GET | `Authorization: Bearer <PUSH_ADMIN_TOKEN>` | numărul de abonați e o cifră de business, nu una publică. |
| `/push/trimite` | POST | `Authorization: Bearer <PUSH_ADMIN_TOKEN>` | singura acțiune care consumă ziua și scrie în KV. `uscat: true` tot cu token: repetiția arată exact ce ar pleca. |

Cum se compară tokenul (`infra/push.js::tokenCorect`):

- se ia headerul `authorization`, i se taie prefixul `Bearer ` (insensibil la majuscule) și se compară cu secretul, **în timp constant în lungimea maximă** — nu cu `===`, ca să nu lase scurtcircuitul de la primul octet să cronometreze răspunsul;
- lipsa sau greșeala lui → `401 {"eroare":"lipsa autorizare"}`, **fără** să spună ce anume a fost greșit (lungime, prefix, conținut);
- secretul lipsă cu totul → `503` cu lista cheilor care lipsesc (configLipsa), pentru că aici problema e de configurare, nu de autorizare;
- nu e JWT și n-are expirare: e o cheie simetrică de admin. Rotația = `wrangler secret put PUSH_ADMIN_TOKEN` + aceeași valoare în `.env`-ul de pe mașina de lucru.

**Ce NU protejează, asumat:** abonarea e deschisă oricui. Cine vrea poate chema
`/push/abonare` în buclă și poate goli plafonul de scrieri KV (1.000/zi pe Free) — simptomul
e `503` la abonări, nu scurgeri de date. Ce limitează paguba: validarea strictă de mai jos,
faptul că re-abonarea **nu rescrie** (deci același endpoint nu consumă decît o singură
scriere, oricîte cereri ar face), și faptul că un endpoint fals nu primește nimic — moare
prima dată cînd serviciul de push răspunde `404/410` și e șters atunci.

## 7. Ce se validează, și ce se respinge cu ce cod

La abonare (`/push/abonare`, în `valideazaAbonament`):

| Verificare | Respins cu |
|---|---|
| corpul e JSON | `400 corp JSON invalid` |
| `subscription` e obiect | `400 abonament lipsa` |
| `endpoint` e URL `https:` | `400 endpoint de push neacceptat` |
| gazda e un serviciu de push cunoscut (10 gazde: FCM, Mozilla, Apple, Windows) | `400 endpoint de push neacceptat` |
| `keys.p256dh` și `keys.auth` sînt șiruri | `400 cheile abonamentului lipsesc` |
| `p256dh` decodifică base64url și are **65 de octeți** (punct P-256 necomprimat) | `400 cheia publica a abonamentului are lungimea gresita` |
| `auth` decodifică și are **cel puțin 16 octeți** | `400 secretul de autentificare e prea scurt` |
| altfel | `201 {"ok":true,"nou":true}` |

Cheia din KV e `sub:` + SHA-256(endpoint), deci re-abonarea aceluiași dispozitiv găsește
înregistrarea și răspunde `200 {"ok":true,"nou":false}` **fără scriere**.

La trimitere (`/push/trimite`, în `verificaAlerta` + `trimiteLot`):

| Situație | Cod |
|---|---|
| politica «Zgomot zero» refuză | `422` + `motive` în română |
| azi s-a trimis deja (cheia `cap:<data>` există) | `409` + ziua |
| lipsește KV / cheile VAPID | `503` + ce anume lipsește |
| lipsă sau greșit tokenul | `401` |
| ok | `200` + `{trimise, esecuri, sterse, cursor_urmator}` |

La dezabonare: același `gazdaAcceptata` ca la abonare; nu se verifică dacă endpointul
există deja — ștergerea unei chei inexistente e un no-op, nu o eroare.

**Politica «Zgomot zero», în cifre** (toate în `verificaAlerta`, toate refuză cu `422` și
motive în română): titlul între 12 și 90 de caractere; textul între 30 și 200; textul nu are
voie să repete titlul; niciun `!` sau `?`, niciun `…`, niciun emoji în vreunul din cele două;
niciun cuvînt de peste 3 majuscule care nu e acronim (SUA, UE, BNR… sînt trecute în lista de
scutiri); niciun cuvînt-momitor (echivalat fără diacritice, deci „șoc" și „soc" sar amîndouă);
adresa trebuie să fie `https://izz.ro/{categorie}/{slug}/`, fără parametri de urmărire.

La trimiterea propriu-zisă, răspunsurile serviciului de push sînt citite, nu ignorate:

| răspunsul serviciului | ce face Workerul |
|---|---|
| `200`/`201` | succes |
| `404`/`410` | abonamentul e **șters** din KV — aplicația a fost dezinstalată sau permisiunea a fost retrasă; altfel KV crește cu morți și fiecare alertă plătește cîte o cerere pentru ei |
| `429` sau alt cod | eșec, iar abonamentul **rămîne** (limitat nu înseamnă mort). `Retry-After` nu e citit, pentru că reluarea se face a doua zi: plafonul de o alertă pe zi face inutilă reîncercarea în aceeași zi. |

**Ce NU se validează, și de ce:** nu cerem și nu putem cere dovada că un endpoint aparține
cuiva anume — Web Push n-are un astfel de mecanism la nivel de aplicație (legătura e între
browser și serviciul de push; noi primim doar un URL și două chei). Protecția e economică și
prin curățare, nu criptografică.

## 8. Cum verifici că merge, înainte de a anunța pe nimeni

1. `python tools/alerta_push.py --stare` → `Abonamente: 0` (nu eroare).
2. Deschide site-ul pe telefon, footer → **„Alerte de ultimă oră"** → **Activează**.
   Ar trebui să apară „Alertele sunt active pe acest dispozitiv".
3. `python tools/alerta_push.py --stare` → `Abonamente: 1`.
4. `python tools/alerta_push.py --uscat ...` → `ar pleca la 1 abonamente`.
5. Trimite una reală **către tine** și vezi dacă se deschide pe articol.
6. A doua în aceeași zi → `REFUZAT — maxim o alertă pe zi`.

---

## 9. Ce NU e verificat încă (spus ca să nu pară mai mult decât e)

- **Nicio alertă nu a plecat printr-un serviciu de push real.** Criptarea e verificată pe
  vectorul de test din RFC 8291 și prin decriptare cu cheia clientului
  (`tests/test_push_criptare.py`), iar rutele sunt verificate cu un KV simulat
  (`tests/test_push_rute.py`) — dar codul `201` al FCM/Mozilla și felul în care arată
  notificarea pe un telefon real sunt **neconfirmate**.
- **Instalarea PWA nu a fost încercată într-un browser**: sesiunea asta n-a avut la
  dispoziție un Chromium headless, deci nici Lighthouse (§13) pentru delta de scoruri.
  Ce s-a putut verifica: `output/sw.js` există la rădăcină, `/offline/` se randează,
  manifestul e valid, iar `tools/html_check.py` trece curat pe output-ul construit.

Ambele se închid într-o tură următoare, pe preview-ul Workerului.
