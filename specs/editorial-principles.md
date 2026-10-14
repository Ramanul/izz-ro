# Editorial principles — implementation slice

- Goal: explain the IZZ editorial identity and three attributed philosophical reading notes at `/principii/`, without turning the books into evidence for news.
- Inputs: the owner's approved transformation plan, existing `content/pages/despre.md`, existing Markdown renderer and public contact/corrections routes.
- Outputs: `content/pages/principii.md`, an updated About page, and `docs/editorial-operation.md`; no new renderer, template, dependency, provider call or book download.
- Inputs: only the supplied Romanian editions of The Ra Contact volumes 1 and 2 and AlienMind, reconciled in the approved three-source plan; the earlier fourth source is excluded.
- Acceptance: seven observable principles, two labelled illustrative examples, three distinct book/volume notes with session/question and actual PDF pages for Ra, chapter/numbered paragraphs for AlienMind, explicit tensions and limits, and the existing correction channel.
- Acceptance: one H1 per rendered page, existing Jinja/Markdown pipeline, valid local policy links, no absolute local paths or downloadable supplied books, no unmeasured daily/universal human-review claim, and a visible distinction between current automation and editorial features still in development.
- Ownership: this slice does not edit `generator/render.py`, `templates/base.html`, styles, news state or deploy configuration; the integration owner adds navigation and performs whole-site/browser/live checks.
- Verification: targeted Markdown/Jinja tests and relevant existing regressions locally; publication and user comprehension are separate checks, not inferred from a green unit test.

## Editorial boundary

The owner authorised implementation of the full plan and live deployment. This slice
implements points 1 and 11 and documents the manual process for point 12. It does not
claim that the news corpus has already been read or checked by a human. A correction
must remain effective even if optional presentation features are disabled.

Preserve the existing seven-principle layout and two illustrative examples. Explain
the Creator/unity/free-will/Logos/densities/polarity/veil/higher-self/archetype framework
as the source's worldview, alongside the distinct nonlocal/collective/ecological
worldview of AlienMind. Do not equate the three files with independent corroboration.
Use Ra II 97.9, 88.10-88.12, 73.12 and 99.9 to make the limits of symbolism,
documentation, imposed service and capacity explicit. No source grants empirical
news-verification authority, a spiritual classifier or a health guarantee.

Context annotations, dossiers, correction-history propagation and editorial caches
are commitments in development, not features certified by this content slice.
The pilot starts with a bounded human-review scope and records actual work; it
does not claim universal review or a daily cadence. Navigation, sitemap integration,
whole-site build, browser checks and live publication remain with the integration owner.

## Failure and rollback

If readers confuse attributed spiritual claims with news evidence, shorten or revise
the philosophical notes while preserving the practical editorial rules. An incorrect
reference is corrected before retaining the related interpretation. The standalone
page can be revised without changing article addresses. Do not revert published
factual corrections as a side effect of withdrawing a design experiment.
