# IZZ Intelligence API

Optional Cloudflare Worker entrypoint for the strategic intelligence layer. It is intentionally not wired into `wrangler.jsonc` in this slice; production deployment remains on the existing repo → PR → CI path.

## Bindings

- `IZZ_DB`: Cloudflare D1 database using `infra/intelligence/schema.sql`.
- `LEAD_INGEST_KEY`: environment secret required for `POST /api/intelligence/leads`.

## Endpoints

`GET /api/intelligence/market` returns aggregated observation counts and average confidence.

`GET /api/intelligence/company?cui=RO...` returns an entity plus its recent observations.

`POST /api/intelligence/actions` accepts `{ "text": "..." }` and returns deterministic next actions.

`POST /api/intelligence/leads` accepts `{ "need": "...", "city": "...", "budget": "...", "session_key": "..." }`; the `X-IZZ-Lead-Key` header must match `LEAD_INGEST_KEY`.

All responses are JSON. The API never returns credentials and does not expose the lead-ingest secret.
