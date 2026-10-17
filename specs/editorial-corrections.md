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

Validation recorded on 17 October 2026:
- Final focused Python suite: 120 passed in 37.33 s; 2 Node cache tests passed.
- Ruff passed; repository rule/history checks: 81 passed, 4 skipped.
- Production-data render on the initial PR head: 12,994 files, 9,166 active articles,
  732 mapped articles. Publication/map digests match; zero wrong map paths or titles.
- Collected article SHA256 remains 59B71E388E32AFA66EA7A2204E3244051BFF8330B76B03FD793AC90ED092DFE9.
- QA passes with the existing 14% duplicate warning; A/B/C catalog validates (2 records).
- Initial exact-head GitHub checks all passed. Local broad suite: 2,498 passed,
  24 failed, 10 skipped, 8 xfailed; failures include denied loopback sockets and an
  incomplete/stale reconstructed local baseline. Rule/history and image fixtures were
  then reconciled with main; do not call that first broad run green.

PR: https://github.com/Ramanul/izz-ro/pull/497 (draft; not published).
Remaining release gates: exact final-head CI/reviews and visual/performance checks.
Browser verification could not reach localhost (ERR_CONNECTION_TIMED_OUT); in-app
browser also failed with a session error. Git Bash fails with NtCreateDirectoryObject
access denied; Lighthouse/pa11y before/after measurements are not completed.
No fictional corrections are present in the production catalog.
