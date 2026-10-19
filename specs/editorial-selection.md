# Editorial selection F: shadow phase

- Goal: compare evidence-backed editorial selection with the existing hero and diversified feed before activating a homepage pilot.
- Inputs: publication-filtered article copies with current, validated editorial annotations; explicit area, reason and evidence references in records[].selection.
- Outputs: editorial-selection-comparison.json, mode=shadow, selected paths/reasons, expired/outside-area/capacity exclusions and the existing selections. No homepage order changes.
- Acceptance: stale/unapproved annotations cannot recommend; deadlines match an examined resource and area; public impacts reference a documented affected group; deterministic ties; input is preserved.
- Acceptance: expired reasons cannot keep service priority; absence of annotations preserves the existing homepage. Different sources are not claimed to be independent.
- Scope: no new dependency, model call, cost, private reviewer data or synthetic public recommendation. No change to corrections, dossiers or their retention.
- Rollout: inspect the real comparison first, then populate documented selection annotations and implement one visible pilot module plus the public method. That activation remains pending.

## Evidence and limitations

Local 19 October 2026 comparison: 8785 publication-filtered articles, zero selection annotations, zero recommendations. Existing context annotations are not retroactively promoted to editorial selection decisions. This is the F foundation, not completion of point 7 or the overall transformation. A-E remain 5/8 slices and 8/12 points at pilot scale.

The selector consumes publication copies after moderation, corrections, future-date and budget exclusions. It never reloads withdrawn input. Priority describes attention allocation, not truth, moral polarity, human approval or demonstrated reader usefulness. A matching evidence reference is a validation condition, not a factual verification of the reason's wording. Review that wording before activation.

Verification: 98 focused context/resource/publication/selection tests passed locally; Ruff passed. Full CI, build integration and live verification remain separate. No visible output is introduced, so this shadow-only change does not claim a frontend performance comparison.
