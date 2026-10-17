# Persistent documentary dossiers and explained relations

Goal: deliver plan points 5/6 without changing collection state, generic entity pages or the current recommendation algorithm.
Inputs: a strict, versioned `content/editorial/dossiers.json`, publishable article copies after slug assignment, and optional approved article annotation relations.
Outputs: persistent `/dosar/<slug>/` view models, explained article relations, explicit subject links, and a machine-readable preparation report.
Acceptance: an expired article leaves no broken link; source documents and approved summaries survive; event and publication dates are separate; a changed target fingerprint hides its relation; co-occurrence never implies causality; withdrawn/unavailable evidence is visible and suppresses dependent current assertions.
Integration: call `prepare_dossiers` before any output deletion; render its pages before sitemap/search/file accounting; attach returned relation lists to article copies and subject links only to actual subject pages. No new AI calls or service.
Boundaries: `documentary` identifies assisted documentary examination, never human approval. The real pilot is one official Sector 1 notice; it does not certify platform availability or independent corroboration. A dossier is a bounded history, not the complete history of its subject.

## Public integration contract

`load_dossiers(path=None)` returns `{id: record}` (an absent catalog is empty; malformed content raises `EditorialError`). `prepare_dossiers(catalog, articles, annotations=None, now=None)` returns `(pages, article_relations, subject_dossiers, report)` without mutating any input.

- `pages` contains approved or withdrawn dossier views; `path`, `title`, `summary`, `reviewed_at`, `documents`, `events`, `history`, `uncertainties`, `relations`, `article_links`, and `indexable` are ready for autoescaped templates. Withdrawn pages are explanatory, excluded from search/indexing, and retain only their withdrawal note.
- `article_relations` maps an article `annotation_key` to ready-to-render relation items. Article relations come from a fresh approved annotation's `relations` array; dossier `article_links` also provide reviewed context links to their fingerprint-matching source article.
- `subject_dossiers` maps an explicitly approved subject slug to dossier links; the caller only displays these on subject pages it actually emits. No names are automatically merged.
- `report` counts emitted/indexable/withdrawn dossiers and lists suppressed article references or target/source changes. It contains public keys and reason codes, no private message content.

Relations require type, target, explanation, document/evidence IDs, documentary/human review metadata and `identity_basis`. `affects` additionally requires `effect_status=observed|projected` and `effect_evidence_ids`. Article targets require `target_fingerprint`; dossier targets require the target dossier content fingerprint. Changing substantive target content demands renewed review. `co_occurrence` is a separate type with a fixed visible noncausal disclaimer.

Dossier article references keep the approved article key, fingerprint, and explanation. An article may expire; its reference is then omitted from navigation while the dossier's document references remain. Events retain an optional `event_at` independently of `published_at`; events with missing event dates never inherit publication dates. Only an approved evidence-backed history item may change the current summary, and the latest correction must equal the dossier summary.

## Documentary examination

Examined 2026-10-17: [official Sector 1 notice](https://primariasector1.ro/intrerupere-temporara-a-serviciilor-de-plata-online-in-perioada-16-18-octombrie/), title, publication date 13.10.2026, body paragraphs 1-5. One institutional origin; no external confirmation. The announced interval is 16 October 19:00 through 18 October 18:00 local Bucharest time (timezone inferred from institution locale, not specified by source); the announced resumption is a forecast. No payment or availability probe was performed. The summary paraphrases the source, retains scope and uncertainty, and stores no full article copy.

## Verification responsibility

Unit and template tests cover schema rejection, unsafe URLs/HTML, immutability, expiration, same-name disambiguation, target changes, noncausal association, withdrawn documents and summary correction history. The integrating executor verifies site build, sitemap/search inclusion, browser experience and frontend audit on the combined branch. Rollback removes navigation/render integration while retaining the versioned catalog; a published withdrawn dossier retains an explanatory route.
