---
name: reviewing-powerpoint
description: Review a PowerPoint's content, native structure, rendered appearance, and applicable compatibility evidence. Use for quality assurance before delivery or an explicit deck review, with clear separation of structural checks, visual inspection, and actual PowerPoint validation.
---

# Reviewing PowerPoint

Review the final export against the user's brief and the source material. Focus findings on consequences for the audience or the user's ability to edit and present the file. Use [the review rubric](references/review-rubric.md) to guide inspection and severity.

## 1. Structural and content checks

Confirm file readability, slide order/count, dimensions, expected native objects, source claims, numerical consistency, and relevant preserved features. Use the bundled inspector when a Python runtime is available:

```text
python <reviewing-powerpoint>/scripts/inspect_pptx.py deck.pptx --json --expect-slides 8 --require-chart 2 --require-table 3
```

Replace `<reviewing-powerpoint>` with this skill's actual directory. Chart/table flags take one-based slide numbers and may be repeated. Pass only expectations supported by the task. Omit count/object expectations for an exploratory review.

The inspector reports package evidence and heuristic warnings, including fonts and bounds. It does not render slides, determine font availability, measure visible text overflow, validate chart data semantics, or prove editability in PowerPoint. Investigate warnings in context; intentional bleed can extend outside a slide, and text may inherit its font from the theme. Do not turn a warning count into a visual-quality score.

## 2. Visual checks

Render every slide from the final export using an available presentation renderer. Inspect every slide at readable resolution; a contact sheet helps navigation but is insufficient for dense labels and footnotes. Check clipping, overlap, text wrapping, hierarchy, contrast, image crops, chart/table labels, citations, consistent geometry, and language glyphs. Compare to a supplied template and, for edits, the source deck.

Fix issues within the user's requested scope, then regenerate affected previews and rerun relevant checks. Confirm the full preview set matches the final deck. If rendering is unavailable, mark visual inspection incomplete rather than infer it passed from XML or file creation.

## 3. Target-application checks

If actual PowerPoint is available and the task calls for compatibility verification, open the final file and check repair dialogs, font/layout behavior, native object editing, and requested playback or navigation. Report only the actions actually performed. Another renderer or a PPTX structural parser cannot establish these results.

## Handoff evidence

Provide the final artifact or an actionable review, the validation performed, and any material remaining gaps. Separate these statuses: structural checks; rendered visual inspection with renderer; actual PowerPoint opening/editing/playback. For unresolved issues, identify the slide, observed problem, audience impact, and specific correction. Never claim “fully validated” when one of the required checks was unavailable.
