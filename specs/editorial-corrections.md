# Editorial transformation D: correction propagation

Goal: publish an approved correction consistently across article, cards, feed, search,
county pages and map; preserve a withdrawal explanation after source-state expiry.
Inputs: immutable collected articles and versioned corrections catalog (empty in production).
Outputs: corrected publication copies, explanatory withdrawal pages, deterministic public
manifest, map generated from those exact active copies, offline freshness notice.
Files: generator/publication.py, generator/render.py, tools/build_harta_data.py,
templates/article.html, templates/withdrawn.html, templates/base.html, static/sw.js,
static/editorial-updates.js, corrections catalog and tests.
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

Release verification continuation:
- The connected Chrome browser can now reach the local output on port 8873.
  The expired-correction explanation renders with its notice, review date,
  evidence link and AI-assistance disclosure, without expired article text.
- Terminal loopback still fails with WinError 10013 and Git Bash still fails
  with NtCreateDirectoryObject access denied. Browser reachability does not
  establish terminal audit capability.
- `.github/workflows/editorial-frontend-audit.yml` runs the canonical audit
  on the PR base and exact head, three times each on one Linux runner, with a
  fixed article path and pinned Lighthouse/pa11y versions. Read-only repository
  permissions; no secrets, deployment or periodic trigger. Reports and medians
  are retained as artifacts so performance validation can finish despite the
  local shell limitation. Scores remain unmeasured until that job succeeds.
- Desktop and 390px mobile browser checks cover the corrected article,
  withdrawal explanation and expired correction. The correction notice now
  uses the existing notice design with separate paragraphs rather than the
  small monospaced trust label. The focused suite passed again: 13 tests in
  15.69 s. Synthetic pages were served only from a local temporary QA folder.

18 October continuation (supersedes pending browser access above):
- Recovered PR head 3e2b9795 in an isolated release worktree. Its two failed jobs
  have one cause: STATE contained 42 content lines against its declared 40 limit.
  Condensed STATE while retaining the limit; local rule regression passes.
- Reproduced the missing reload offer for an online page served from saved HTML.
  A small deterministic editorial-revisions.json and page metadata now expose
  catalog changes; an external, versioned client offers a reader-controlled reload
  on load, reconnection or returning to the page. Offline/check failure never
  certifies freshness. This is a site-level revision signal, not a per-article
  judgment; it contains no active-news payload, personal data or tracking.
- Reproduced a model C timeline regenerating an old corrected number; corrected
  stories now withhold that timeline. Historical aliases link to their active
  corrected article rather than claiming it expired. Multiple active articles
  sharing one story_id remain rejected as ambiguous by the existing validator.
- Focused local regression: 18 Python tests and 7 Node contracts passed; Ruff
  and whitespace checks pass. Full suite and final-head audits remain pending.
- Earlier head audit39068580080: three runs each, home85->85/article96->96,
  other Lighthouse categories100; Pa11y home1->1 (existing #judet-pin finding).
  These are historical baseline measurements, not proof of the updated head.
