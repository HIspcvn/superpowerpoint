---
name: editing-powerpoint
description: Modify an existing PowerPoint while preserving its intended content, template, editable objects, and unrelated features. Use for targeted corrections, data or style updates, slide additions, and explicitly requested deck restructuring.
---

# Editing PowerPoint

Make the requested changes with the smallest appropriate scope. For a typo, label, number, or single-slide update, inspect the source, edit directly, and verify the result. Do not require a new brief, storyboard, or visual system unless the change actually affects them.

## Inspect and preserve

1. Locate the source deck and identify the exact slide/object targets from visible content as well as slide numbers. Inspect affected slides and representative surrounding slides.
2. Preserve the original file. Save a new output unless the user explicitly requests overwriting or an existing controlled workflow provides version recovery.
3. Read [preservation guidance](references/preservation.md) before choosing an editing path, especially for charts, embedded data, animation, media, and complex templates. Inventory the features the path must retain.
4. Reuse the source slide size, theme, master/layout relationships, fonts, geometry, and recurring elements. Change unrelated content or formatting only when necessary to satisfy the request and explain the dependency.

Use the [capability adapters](../building-powerpoint/references/capability-adapters.md) when runtime choice is uncertain. Prefer an available application or tool that preserves required features. Never assume that importing and exporting a deck is lossless.

## Apply the change

- Keep text native and preserve language, diacritics, emphasis, hyperlinks, and meaningful run formatting. Adjust nearby layout when longer replacement text requires it; do not silently shrink the whole deck's typography.
- For chart updates, keep series, categories, units, labels, caches, and embedded workbook values aligned. Preserve chart formatting unless redesign is requested.
- Preserve editable tables and their number formats. Do not change missing values to zero or recalculate supplied figures without a valid basis.
- For broad restructuring, reuse [planning-powerpoint](../planning-powerpoint/SKILL.md); for redesign, use [designing-powerpoint](../designing-powerpoint/SKILL.md). Keep the source's supported content and assets unless the user asks to replace them.
- If a required feature cannot survive the selected path, switch paths where possible. Explain any unavoidable material fidelity or editability loss before accepting it as the finished result.

## Verify and deliver

Compare the before/after deck for requested changes and unintended effects. Check slide order/count, object and feature preservation, chart data, notes, and links as relevant. Render every output slide and inspect the complete deck, with before/after comparison on changed slides. Use [reviewing-powerpoint](../reviewing-powerpoint/SKILL.md) and distinguish structural, visual, and actual PowerPoint checks.

Deliver the edited file, a concise change summary, and specific remaining limitations. Do not claim animation or media playback survived merely because the corresponding package files are still present.
