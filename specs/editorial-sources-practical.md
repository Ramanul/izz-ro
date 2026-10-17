# Sources and practical context pilot

- Goal: expose examined origin and exact disagreements; offer attributed practical resources with their area and expiry.
- Input: current article identities/fingerprints, approved annotations and an explicit catalog of examined sources/resources.
- Output: one existing sources-box with comparison, attributed impacts and optional practical links; deterministic coverage/expiry counts.
- Files: generator/editorial.py and render.py; tools/validate_editorial.py and editorial_report.py; content/editorial/annotations.json and source-provenance.json; templates/_editorial_context.html, _source_comparison.html and surse.html; tests/test_editorial_sources_practical.py; this note and STATE.
- Acceptance: five republications of one document count as one known origin; disagreement values stay attributed; unexamined independence stays unknown; expired resources lose current status; a resource cannot attach to a different approved article/area.
- Safety: immutable source state, strict references and safe literal URL schemes, no novel services, AI calls or personal data, no synthetic public example.
- Invalidation: an undocumented origin or geographic scope invalidates the annotation; documentary review cannot certify the whole article or independent verification.

The complete canonical plan was approved for implementation and publication.
This is slice C (points3/4), based on the published B at8f303cda. Resource scope
is manually examined and tied to one persisted article key; this validator does
not infer geography from a headline or certify the content of a retrieved page.

## Observed starting state and pilot

On 17 October, B was already published through #477 (merged), at8f303cda, and the
public site still showed its context. The preserved C worktree had an unfinished
editorial.py extension; no provenance catalog, resource annotation, template or
extension tests existed. C was fast-forwarded to origin/main ec0f7af9 before
completion; the inherited patch is preserved privately. No news state was edited.

The real C pilot is the official Sector1 notice about payment services during
16–18 October. Only its official notice was examined; no second source or
independent operational test is claimed. Scope is Sector1, Bucharest, not a
nationwide outage. The notice says 18 October2026 at18:00; interpreting this as
Bucharest local time (+03:00) is explicit in the public resource and unknowns.
The resource is the information notice itself, never a payment instruction.

## Maintenance and boundaries

`provenance_id` binds an evidence URL to an examined artifact. A republication
origin must point to an examined original in the catalog; the catalog counts
documented artifact origins, never independent confirmations. Differences retain
each examined position and evidence link without an average. The existing source
chronology statistics describe observation order only.

Resources require an examined URL, organizer, article key, exact area and locator.
An optional zoned deadline requires its documented time basis. Expiry is computed
at render time, with one clock shared by views and report. Expired entries remain
historical; undated entries are counted separately and never labelled current.
Static pages can lag a later notice or deadline until the next build; the public
copy states this and sends the reader to the source. Offline propagation belongs
to D, not this slice. Human review and continuous coverage are not promised.

Remove an action independently of its article to withdraw the practical resource.
Set a record withdrawn to hide its entire context. A changed article fingerprint
withholds context and resources pending review. An invalid catalog stops rendering
before previous output is removed. No new AI calls or paid services are added.

## Acceptance evidence

The focused suite exercises five republications with one origin, attributed
disagreement, unknown independence, expiry at the exact offset boundary, undated
resources, wrong area/article, unexamined destinations and output preservation.
The multiple-source cases are synthetic fixtures confined to tests; the public
pilot contains only the real examined municipal notice.
Local execution on the frozen main snapshot ec0f7af9: full suite2507passed,
6skipped and8expected failures; final focused suite65passed after presentation
adjustments. Ruff and editorial QA pass; QA emits a14%duplicate warning on the
source corpus. Full render12986files/9166articles,2fresh contexts,1examined
provenance/resource. Source-state SHA256 remains
59B71E388E32AFA66EA7A2204E3244051BFF8330B76B03FD793AC90ED092DFE9.
Stable before medians are home88/article96 for performance and100 for the other
three Lighthouse categories. After measurement and actual-page/HTML verification
are release gates. Pagefind is absent in this local audit runtime, so search uses
the existing simplified fallback in both revisions; search is outside this slice.
