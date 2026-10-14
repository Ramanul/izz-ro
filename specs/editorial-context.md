# Documentary context pilot — slice B

- Goal: one real article exposes attributed claims, examined evidence and explicit unknowns; other articles retain their existing presentation.
- Inputs: saved articles and stable slugs/story_id, UTF-8 annotations with explicit human/documentary review, input SHA256 and located evidence.
- Outputs: a voluntary context section, deterministic validation and coverage counts with a declared denominator. No source-state writes or new model calls.
- Files: generator/editorial.py, generator/render.py, templates/article.html, templates/_editorial_context.html, content/editorial/annotations.json, tools/validate_editorial.py, tools/editorial_report.py, tests/test_editorial_context.py, docs/editorial-operation.md and specs/STATE.md.
- Acceptance: missing catalogs preserve old article output; malformed/reference-broken context blocks before output deletion; changed input hides ordinary context; AI assistance is distinct from human review; evidence accessible in two actions; stored data remain unchanged.
- Scope: point 2 and validation/report foundation of point 12. Corrections, selection, dossiers, relationships, resources and map overrides remain separate slices; this pilot rejects their fields.
- Mandate: owner authorised implementation and deployment of the complete plan; continued in this chat on 2026-10-14. The three-source plan is reconciled. Original wider unfinished module preserved privately as full-reading/tmp/editorial-pre-context.py.

The pilot is maintained manually and does not promise continuous review. Approval denotes a limited documentary process, not independent confirmation or an infallible verdict. The examined official municipal page establishes an announcement and the presence of a PDF link, not the financial values in its unexamined attachment.

Invalidation: withdraw or revise the annotation if its locator does not support the precise claim, if the cited document is withdrawn, or if the labels suggest greater certainty or broader human review than the process established.

## Local validation

2026-10-14, base6d2c462d:37focused tests passed. Full Windows suite with inherited `PYTHONUTF8=1`:2433passed,6skipped,8xfailed in259.88s; Ruff and diff checks clean. The first full-suite attempt was interrupted after failure indicators; the reproducible diagnostic was a cp1252 child/UTF8 parent mismatch in the cadence CLI test. It passes with the inherited environment setting, without a site-code change. No full-green claim is made for those superseded runs.

The complete baseline render had12404files and8542published articles from9424visible input articles. Three stable mobile audits per page: home median82, pilot article96; accessibility/best-practices/SEO100. Pa11y:home1preexisting selector flag,article0. After measurements, browser, complete HTML control, CI and live evidence will be recorded separately. Raw data SHA256DC14DDD5E04EDDDF8928B5FBC34FE34BEEAA55D707E23BD3B1C70F449BA039C3. Private audit files and books are not public artifacts.

Final focused checks after separating structured stdout from diagnostics:38passed in17.02s, Ruff clean. Full after render:12405files,8542published articles and1fresh context; raw data hash unchanged. Canonical `bash tools/audit.sh` exited0. Three subsequent mobile audits:home80/article96medians, other categories100; pa11yhome1/article0. Home rolling24h counts/map changed with the clock, so this is an observed output comparison, not a perfectly isolated causal experiment or demonstrated performance gain/loss. Browser:Enter opens context, oneH1, main375px=scroll375px at390px, real evidence link and explicit unknowns. Internal reviewer identity is absent from output. Complete HTML control and final-head CI remain merge gates.

First CI head1160436d failed test collection because the new test imported bs4, locally present but absent from the pytest environment. The test now uses standard-library HTMLParser; production dependencies and output are unchanged. That failed head is not a release candidate. Final-head checks are required after the correction.
