# E4: manual correction footprint and initial summary

Goal: preserve the first title/summary across correction reruns and offer an explicitly
approved comparison with the current summary, without republishing withdrawn text.
Inputs: saved articles, manual moderation overrides and the approved corrections catalog.
Outputs: immutable initial summary, current corrected body and optional native HTML details.
Files: generator/moderation.py, generator/publication.py, generator/render.py,
templates/article.html, tests/test_editorial_moderation_versions.py and specs/STATE.md.
Acceptance: save/load and a second correction retain the first summary; a publication copy
does not alias stored history; replaced synthesis does not leave stale dialectic or timeline;
history is escaped, excluded from Pagefind, and absent unless the current correction opts in.

`show_initial_version` is an optional strict boolean in either trusted correction record.
Omission and false hide history. A later approved catalog correction controls visibility
even after a manual opt-in. Each moderation run discards persisted permission and reads
the current config again; removing a manual correction therefore revokes its old opt-in.
An enabled flag changes the catalog revision signal; revoking it restores the hidden signal.
Withdrawals cannot opt in. Takedown/withdrawal filters run before an active article can render.
Malformed existing snapshots stop the correction rather than fabricate a historical version.

The public label is "Rezumat înainte de corecție": first title and teaser/synthesis only.
This is not a complete copy of structured source analysis or a ledger of intermediate edits.
History is hidden on public pages by default; saved article state is repository data,
not private storage. This feature does not erase earlier Git commits or backups.
No production correction, retrospective approval or historical content is fabricated.

Audit regressions on the original PR head: 20 failed, 20 passed. A separate actual
three-domain timeline case failed before the render safeguard was extended to manual edits.
Validation on 28 October 2026: 186 focused tests passed. The broad run had 2953 passed,
5 skipped, 8 xfailed and one startup-budget failure caused by the longer STATE note.
The note was shortened without raising any cap; the failed guard, STATE cap and version
tests then passed together (43 passed). Ruff and diff checks passed; scoped credential
patterns found zero matches in the seven changed text files.

Canonical `tools/audit.sh` passed: 9857 articles, 15092/17000 files, Pagefind complete.
Lighthouse 13.4.1 / pa11y 10.0.0 / Chrome 156.0.8078.48. Three paired runs per revision
used the same render context and assets, with the old article template from e9d9c275.
Home medians before/after: 86/100/100/100; pinned article: 95/100/100/100.
All twelve paired pa11y checks had zero errors. The captured after HTML matches the
actual emitted files byte for byte; these uncorrected pages are unchanged by the toggle.
The earlier measurement on the older corpus is retained as evidence, not used as baseline.
Local browser: approved summary expands to the original 120 while the current body says
12; no opt-in produces no control or old text. Tested at default width and 390 px, with
no horizontal overflow. This is a synthetic example, not a fabricated production correction.
CI and live publication remain separate gates; no merge/deploy is asserted here.
