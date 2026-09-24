# Capability and runtime adapters

Choose tools by the current deliverable and actual environment. Do not install an arbitrary package or invoke a named private tool merely because a reference example uses it.

## Discover before committing

Check available presentation skills, runtime/dependency discovery tools, application connectors, and local applications. When an installed presentation skill supplies an authoring runtime, read and follow that skill's instructions. Read current tool documentation or local package examples for the operations you need; do not guess an API from another version.

Confirm these capabilities with a small representative file when uncertain:

| Requirement | Evidence to seek |
| --- | --- |
| Native text and shapes | Exported objects remain separate and editable |
| Native charts | A chart object and editable series data survive export; any workbook agrees with plotted data |
| Native tables | Table cells survive export and fit their content |
| Template reuse | Correct slide size, masters/layouts, theme, and recurring visible elements survive |
| Vietnamese content | Font includes required glyphs; composed text and diacritics render correctly |
| Speaker notes/citations | Notes or footnotes survive export in the intended location |
| Existing complex features | Required animation, media, links, chart data, and unsupported extensions are preserved |
| Rendering | All slides can be exported to inspectable images or a PDF without a missing-slide gap |

## Common adapters

**Supported presentation artifact runtime:** Useful for programmatic layout, native objects, and export when supplied by the host. Use its documented export/render APIs. Inspect the PPTX output as well as its preview; a runtime preview is not proof of PowerPoint rendering.

**PowerPoint application automation or connector:** Prefer when actual PowerPoint compatibility or preservation of application-specific features matters and the environment permits it. Work on a copy, save to the requested output, render/export all slides, and test playback for requested interactive features. A background process launching successfully is not evidence that the file opened without repair.

**OOXML library or package editing:** Suitable for controlled generation and narrowly scoped changes when its feature coverage fits. Different libraries may omit, alter, or discard unsupported parts. Before editing an existing deck, inventory features and relationships; compare the output and use [editing preservation](../../editing-powerpoint/references/preservation.md). Do not treat re-saving as a lossless operation by default.

**LibreOffice or another compatible renderer:** Can provide useful visual evidence when PowerPoint is unavailable. State the renderer used; font substitution, charts, or effects may differ in PowerPoint. Do not label this as actual PowerPoint validation.

**PDF or image-only environment:** Useful for reference inspection and visual review. It cannot alone prove native object editability, embedded chart workbook fidelity, notes, animation, or playback.

## Fallback boundaries

- If authoring is available but rendering is not, export the deck and state that visual inspection is incomplete. Provide a reproducible render/check path when known and relevant; do not invent a screenshot result.
- If the chosen runtime lacks a required native object, switch to a capable available path. If none exists, describe the precise limitation and agree on a material change only when necessary; do not silently replace editable charts with images.
- If round-trip preservation is uncertain, prefer targeted modification that retains untouched package parts or use the original application. Preserve the source file and disclose residual limitations.
- Treat downloading dependencies, publishing, and sending files according to the user's authorization and the host's permission boundaries. Tool selection does not itself authorize new external actions.
