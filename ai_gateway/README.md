# ai_gateway — FreeQuotaGuard în fața OmniRoute

Gateway AI de coding cu **cost $0 garantat mecanic**: clientul tău de coding vorbește
cu gate-ul local de aici, care aplică regulile de siguranță și trimite mai departe spre
[OmniRoute](https://github.com/diegosouzapw/OmniRoute) (gateway MIT extern), iar OmniRoute
spre providerii free.

    client (ZCode / Claude Code / orice client OpenAI-compatibil)
        ↓  http://127.0.0.1:20129/v1
    ai_gateway (aici: FreeQuotaGuard, redactare secrete, free-only, tracking UTC)
        ↓  http://127.0.0.1:20128/v1
    OmniRoute (rutare, fallback, compresie RTK/Caveman, dashboard)
        ↓
    Groq · Cerebras · Gemini · Mistral · GitHub Models · Z.AI · Cloudflare · OpenAI*

\* OpenAI doar cu oferta „complimentary tokens" confirmată + margină 20% + oprire
înainte de plafon — pentru că OpenAI e singurul care facturează depășirea.

**Documentația completă (instalare, chei, cote, OpenAI, costuri): [FREE_AI_SETUP.md](FREE_AI_SETUP.md)**

Comenzi rapide:

```powershell
# statusul cotelor în terminal
python -m ai_gateway status

# pornește gate-ul (cere OmniRoute pe 20128 pentru traficul real)
python -m ai_gateway serve

# scenariul de test din spec (fără rețea): OpenAI 2.5M, consumat 2.0M, cerere 700K
python -m ai_gateway simulate
```

Cod doar din biblioteca standard Python — fără dependențe noi.
