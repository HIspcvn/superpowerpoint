---
name: building-powerpoint
description: Build editable PowerPoint presentations from a brief, storyboard, data, or approved visual direction, and produce renderable deliverables. Use for native slide authoring or substantive rebuilds, not for generic image generation.
---

# Building PowerPoint

Produce the requested editable presentation from a content and visual contract. If either is materially missing, use [planning-powerpoint](../planning-powerpoint/SKILL.md) or [designing-powerpoint](../designing-powerpoint/SKILL.md) only as much as needed. A clear brief can be implemented directly.

## Choose an available authoring path

Read [capability and runtime adapters](references/capability-adapters.md) before selecting tools. Prefer an installed presentation skill and its supported runtime when available; follow its tool-specific instructions. This library does not require any particular renderer, cloud service, or authoring package.

Confirm that the selected path supports the required objects, template fidelity, editable chart data, text language, export, and rendering. Test a representative slide before generating a large deck. Do not promise a capability based only on a library's name.

## Author the deck

- Preserve the requested aspect ratio, slide count, template, content language, and source evidence. Treat the storyboard as a content contract, while allowing local improvements that do not change its claims.
- Use native text boxes and shapes for labels, body text, diagrams, and simple visual structures. Use native chart and table objects where requested or useful; populate chart data and any embedded workbook consistently.
- Use images for visual media, not as replacements for editable slide content. Disclose any unavoidable object that is flattened or cannot be edited as requested.
- Implement recurring elements through supported layouts, masters, or reusable components. Keep meaningful text out of tiny labels and avoid using manual line breaks to hide incorrect geometry.
- Preserve source locators in readable footnotes, notes, or an appendix as appropriate. Keep numerical units, periods, categories, and number formats aligned with the original data.
- Save the final PPTX and requested additional formats in a clear output location. Keep generated data or build source when it helps the user revise the result; do not make optional extra formats a dependency for delivery.

## Verify the exported file

Run [reviewing-powerpoint](../reviewing-powerpoint/SKILL.md) on the final export. Render every slide, inspect every rendered slide, and fix observed problems before delivery. After changing slides, regenerate the affected previews and rerun relevant checks; ensure the full preview set corresponds to the final export.

Report package checks, visual inspection, and actual PowerPoint validation separately. If a renderer or PowerPoint is unavailable, state exactly which checks remain unperformed rather than treating a successful save as proof of quality.
