"""ai_gateway — stratul de siguranță free-only în fața OmniRoute.

Arhitectura (spec proprietar, secțiunile 1-34):

    coding client (ZCode / Claude Code / Grok CLI)
        ↓  http://127.0.0.1:20129/v1  (aici stă gate-ul ăsta)
    ai_gateway  — FreeQuotaGuard, redactare secrete, free-only, tracking
        ↓  http://127.0.0.1:20128/v1
    OmniRoute (gateway MIT extern, diegosouzapw/OmniRoute)
        ↓
    provideri free (Groq, Cerebras, Gemini, Mistral, GitHub Models, Z.AI, ...)

OmniRoute face rutarea, fallback-ul și compresia. Acest pachet garantează ce
OmniRoute nu garantează: nimic plătit niciodată (GLOBAL_FREE_ONLY / OPENAI_FREE_ONLY),
margine de siguranță 20% înaintea oricărui plafon care poate factura (OpenAI
complimentary tokens), redactarea secretelor din contextul trimis, și evidența
persistentă a consumului, în UTC.

Doar biblioteci standard Python — rulează în același venv ca pipeline-ul, fără
dependențe noi, și trece prin aceeași poartă CI (ruff F+DTZ, pytest tests/).
"""

__version__ = "0.1.0"
