# Editorial transformation D: correction propagation

Goal: publish an approved correction consistently across article, cards, feed, search,
county pages and map; preserve a withdrawal explanation after source-state expiry.
Inputs: immutable collected articles and versioned corrections catalog (empty in production).
Outputs: corrected publication copies, explanatory withdrawal pages, deterministic public
manifest, map generated from those exact active copies, offline freshness notice.
Files: generator/publication.py, generator/render.py, tools/build_harta_data.py,
templates/article.html, templates/withdrawn.html, static/sw.js, corrections catalog and tests.
Acceptance: stale approval fails before output cleanup; no withdrawn item in active assets;
corrected location agrees in county list/map; expired withdrawal retains its observed path;
same input yields same manifest digest; cached pages declare unverified freshness.
Synthetic corrections exist only in tests. No production correction is fabricated.
Existing A/B/C context approvals do not certify corrected article text.
