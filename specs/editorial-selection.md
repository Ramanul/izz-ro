# Editorial selection F: explained homepage pilot

- Goal: compare evidence-backed editorial selection with the existing hero and diversified feed before activating a homepage pilot.
- Inputs: publication-filtered article copies with current, validated editorial annotations; explicit area, reason and evidence references in records[].selection.
- Outputs: editorial-selection-comparison.json, mode=pilot (or shadow with IZZ_EDITORIAL_SELECTION_ENABLED=0), selected paths/reasons, expired/outside-area/capacity exclusions and the existing selections. A single explained module follows the existing hero; the existing hero and category order remain unchanged.
- Acceptance: stale/unapproved annotations cannot recommend; deadlines match an examined resource and area; public impacts reference a documented affected group; deterministic ties; input is preserved.
- Acceptance: expired reasons cannot keep service priority; absence of annotations preserves the existing homepage. Different sources are not claimed to be independent.
- Scope: no new dependency, model call, cost, private reviewer data or synthetic public recommendation. No change to corrections, dossiers or their retention.
- Rollout: shadow comparison was examined before adding two documented selection reasons. One context record is eligible; the service notice is excluded as expired. Activation is confined to one module with chronological alternative and public method. The environment switch suppresses the module while preserving the report.

## Evidence and limitations

Local 19 October 2026 comparison first found 8785 publication-filtered articles and zero selection annotations. After explicit evidence-backed selection reasons were added, the Ineu registry context was selected and the Sector1 payment notice was excluded as expired. The Ineu reason explicitly withholds conclusions about the unexamined attached registry values. No synthetic production recommendation was added. F remains pending until final CI, browser, repeated audit and live checks. A-E remain 5/8 slices and 8/12 points at pilot scale until that release.

The selector consumes publication copies after moderation, corrections, future-date and budget exclusions. It never reloads withdrawn input. Priority describes attention allocation, not truth, moral polarity, human approval or demonstrated reader usefulness. A matching evidence reference is a validation condition, not a factual verification of the reason's wording. Review that wording before activation.

Verification: 98 focused context/resource/publication/selection tests passed locally; Ruff passed. Full CI, build integration and live verification remain separate. The rollout includes a visible module and accurate About/functional-method pages. Repeated frontend audit and real browser checks are required before release; scores belong to actual final-head artifacts.
