# CSS #380 pe main, absent pe live

**Măsurat:** 2026-10-02 (agent) · **Nu e opinie:** curl + MD5.

## Date

| Probă | Valoare |
|-------|--------|
| HTML live `?v=` | `5f633fc9` |
| MD5 `static/styles.css` pe **main** | `5f633fc9768b97ac…` |
| MD5 corp servit pe **izz.ro** | `e3f55590940eba9c…` |
| Octeți live / main | 62995 / 64847 |
| `clamp` + `animation-timeline` live | absente |
| același pe main (după #380) | prezente |
| `cf-cache-status` | HIT |
| `Cache-Control` | `public, max-age=2592000, immutable` |

Comenzi:

```bash
curl -sL https://izz.ro/ | grep -oE 'styles\.css\?v=[a-f0-9]+'
curl -sL https://izz.ro/static/styles.css | md5sum
curl -sL https://raw.githubusercontent.com/Ramanul/izz-ro/main/static/styles.css | md5sum
curl -sL https://izz.ro/static/styles.css | grep -c clamp
curl -sL https://raw.githubusercontent.com/Ramanul/izz-ro/main/static/styles.css | grep -c clamp
```

## Impact pentru cititor

Fazele 3/4/6 (tipografie fluidă, antet mobil, motion la scroll) **nu se văd**,
deși PR #380 e merged pe main.

## Interpretare

1. **Cache edge** pe `/static/*` cu `immutable` 30 zile — dacă cheia de cache
   ignoră `?v=`, un corp vechi rămâne servit sub URL-ul „nou”.
2. Sau **bundle deploy**: HTML generat cu `asset_ver` din sursa nouă, dar
   `output/static/styles.css` din versiunea Workers e încă vechi.

## Ce face ownerul (5 minute)

1. Cloudflare → Caching → Configuration → **Purge** URL:
   - `https://izz.ro/static/styles.css`
   - eventual purge everything dacă tot e vechi după 2 minute.
2. Re-verifică: `curl -sL https://izz.ro/static/styles.css | grep -c clamp` → ≥1.

## Ce face un agent în cod (PR separat, mic)

În `generator/render.py` → `_write_headers`, **după** regula `/static/*`, adaugă
(excepție pe modelul `harta-stiri`):

```
/static/styles.css
  ! Cache-Control
  Cache-Control: public, max-age=3600, must-revalidate
/static/*.js
  ! Cache-Control
  Cache-Control: public, max-age=3600, must-revalidate
```

Motivație: aceleași fișiere sunt „versionate” cu `?v=` tocmai pentru că se
schimbă; `immutable` 30 zile le tratează greșit ca fonturi eterne.

Nu schimba URL-uri, canonical, sitemap, TTL articole.

## Legături

- PR #380 (merged): tipografie + mobil + motion
- `render._asset_ver` / `render._write_headers`
- `wrangler.jsonc` — assets din `./output`
