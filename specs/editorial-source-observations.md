# Source text observations — E1

## Contract

- Goal: pair observed first publication with the limits of subsequent text observation.
- Input: selected-source deep metadata and published C syntheses; output: per-URL counters
  and exact comparable-read fractions, URL coverage and observation window on `/surse/`.
- Only adjacent FULL_TEXT reads of the same URL with increasing aware timestamps compare.
  A changed hash requires valid anchor samples; material change uses the existing >=20%
  anchor-drift threshold. RSS reads and extraction-mode transitions do not compare.
- Existing metadata provides one baseline, never invented historical comparisons. Counters
  are v1, contain no source text and expire with the existing article TTL.
- The catalog deduplicates first-source URLs; secondary publications and unobserved URLs
  cannot increase the observation denominator. No comparisons means `Nemăsurat`.
- Display unchanged/comparable reads, re-read/eligible URLs and UTC start/end; no score,
  ranking or claim of correctness. Ordinary editorial completions can change the text.
- Acceptance: legacy/first/repeated/changed reads, duplicate timestamps, fallback, corrupt
  schemas, no mutation, dry-run, expiry, source attribution, coverage and rendered limits.

## Interpretation boundary

This completes the prospective observation part of E1, following the R5 distinction in
`plan-paradigma-izz.md`: updated text is not evidence of a false original report. An unchanged
hash does not prove truth, and observations do not describe changes between readings.
The original source-to-function mapping is editorial interpretation of the supplied books;
the feature must remain useful to a reader who rejects those sources entirely.

No Git-history reconstruction runs during rendering. The archived metadata observed before
implementation is not silently converted into a historic reliability measure. Production
coverage grows only when selected URLs receive genuinely comparable future readings.

## Verification

- Local base: `24719a44` (fresh `origin/main`, 2026-10-26); the original dirty worktree is preserved.
- `python -m pytest tests/test_text_observations.py tests/test_render_source_observations.py tests/test_fetch_deep.py tests/test_render_sources.py tests/test_reguli.py -q`: **158 passed**. `python -m ruff check .`: passed.
- Reproduced before fixing: malformed metadata containers/version booleans; normalized item URLs differing from the actually fetched `original_link`; invalid anchor samples on changed hashes. Regression cases cover each failure, same/naive/backwards timestamps, fallback interruptions, exact 20% drift, read-only aggregation, dry-run persistence, TTL expiry and attribution.
- `python -m generator.main --render-only` and `bash tools/audit.sh` with `ARTICLE_PATH=/surse/`: completed on the saved real corpus. **11,796** visible inputs; **15,961 / 17,000** emitted files. The emitted source catalog has **657 sources**, **76 rows with statistics**, **622 eligible first-source URLs**, **0 comparisons**: all observation cells remain `Nemăsurat`.
- Before/after uses the original `origin/main` source template and the changed template with the same reconstructed publication context; the changed HTML was checked byte-for-byte against the complete build. Static asset hashes remain shared, including `styles.css=3c9a66cd`.
- Lighthouse 13.5.0, pa11y 10.0.0, Chrome 156.0.8078.47, mobile `/surse/`, **3 runs per revision**: performance **87/89/89 -> 88/88/88** (medians **89 -> 88**), accessibility / best-practices / SEO **100/100/100 -> 100/100/100**; WCAG2AA errors **0/0/0 -> 0/0/0**. The one-point performance movement does not establish a causal regression. The official audit also measured home **79/100/100/100**, WCAG2AA **0**.
- Headless browser checks at **390 px and 1440 px**: document width equals viewport width; all **76** source rows have six columns and `Nemăsurat`; no duplicate IDs or page-script errors. Existing horizontal table scrolling contains the added column. A scoped scan of the seven changed files found **0 credential-pattern hits**; this is a pattern check, not a guarantee against every possible secret format.

## Operational limits

`main.process_new` attaches recent published items to clusters containing new items, then calls `fetch_deep` on the selected synthesis groups (`main.py:193-226`). `_fetch_single` requests the article again without conditional HTTP headers or a full-text cache. A selected old URL can therefore accumulate a real comparison. There is **no periodic rereading of every URL**, and no promise that an eligible URL will be selected again before expiry. The counters do not repair this coverage limitation or reconstruct earlier readings.

The raw saved state contains 13,198 articles and 601 unexpired metadata URLs; none contain observation counters. Only 47 of 812 raw first-source URLs intersect that metadata exactly. These raw counts differ from the publication-filtered catalog above. No production observations have been created by this local render or by the mocked pipeline tests. No push, merge, deployment or live validation was performed.
