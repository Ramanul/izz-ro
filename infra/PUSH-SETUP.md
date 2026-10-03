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

## 6. Cum verifici că merge, înainte de a anunța pe nimeni

1. `python tools/alerta_push.py --stare` → `Abonamente: 0` (nu eroare).
2. Deschide site-ul pe telefon, footer → **„Alerte de ultimă oră"** → **Activează**.
   Ar trebui să apară „Alertele sunt active pe acest dispozitiv".
3. `python tools/alerta_push.py --stare` → `Abonamente: 1`.
4. `python tools/alerta_push.py --uscat ...` → `ar pleca la 1 abonamente`.
5. Trimite una reală **către tine** și vezi dacă se deschide pe articol.
6. A doua în aceeași zi → `REFUZAT — maxim o alertă pe zi`.

---

## 7. Ce NU e verificat încă (spus ca să nu pară mai mult decât e)

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
