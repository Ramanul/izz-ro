# Snapshot edge — configurația Cloudflare pentru izz.ro

> Baseline de referință pentru drift: ce e configurat în Cloudflare la data snapshot-ului.
> Nu e accesibil din repo; se retrage cu API (comanda jos) și se compară cu acest document.

**Data:** 2026-09-05 · **Plan:** Free Website · **Sursă:** API Cloudflare, token read-only
(zone + zone settings + firewall services + zone WAF + bot management, doar izz.ro)

## Setări de zonă

| Setare | Valoare |
|---|---|
| security_level | medium |
| ssl | full |
| always_use_https | on |
| browser_check | on |
| challenge_ttl | 1800 s (30 min) |
| comutatorul legacy „waf" | off (protecția modernă e activă prin managed ruleset, vezi jos) |

## Bot management

| Setare | Valoare |
|---|---|
| fight_mode (Bot Fight Mode) | **activ** |
| crawler_protection | enabled |
| ai_bots_protection | disabled |
| enable_js | true |

## Rulesets existente (6)

Gestionate de Cloudflare: `http_request_sanitize` (Normalization), `http_request_firewall_managed`
(**Cloudflare Managed Free Ruleset** — WAF gestionat activ), `ddos_l7`. De zonă: dynamic redirect
(default), response headers transform (default), `http_request_firewall_custom`.

## Reguli custom (versiunea 5, ambele active)

1. **Block known bad bots and crawlers** — `block`. UA conținând bot/crawler/spammer/scraper,
   cu excepția Googlebot/bingbot/Applebot/Twitterbot; blochează explicit crawlerii de antrenare AI:
   GPTBot, ClaudeBot, CCBot, Bytespider, Amazonbot, meta-externalagent, Applebot-Extended,
   Google-Extended.
2. **Challenge suspicious requests** — `managed_challenge`. `wp-admin` (exceptând admin-ajax),
   `xmlrpc.php`, `.env`.

## Ce NU există (stare normală pe Free)

Nicio regulă rate-limit proprie; nicio regulă custom în afara celor 2 de mai sus.

## Cum se retrage (pentru comparare)

Token read-only cu permisiunile Zone / Zone Settings / Firewall Services / Zone WAF /
Bot Management (Read), limitat la izz.ro. Comenzile: `GET /zones?name=izz.ro`, apoi
`/zones/{id}/settings/*`, `/zones/{id}/bot_management`, `/zones/{id}/rulesets` și
`/zones/{id}/rulesets/{id_custom}`. Token-ul NU se stochează în repo.
