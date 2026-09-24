# Design contract

Record only decisions useful to the builder and reviewer. Use the existing deck's conventions when editing; a contract is not permission to redesign it.

| Decision | What to record |
| --- | --- |
| Canvas | Aspect ratio and dimensions; keep the source ratio for edits |
| Typography | Available families, weight roles, title/body/caption hierarchy, language coverage |
| Color | Background, text, accent, data-series, semantic roles, and relevant brand values |
| Geometry | Margins, title region, content region, footer and page-number positions |
| Layouts | The few layouts required by this storyboard, with usage examples |
| Data graphics | Axis and label conventions, units, number/date formats, source captions |
| Assets | Supplied logos/photos/icons, crop behavior, provenance, required credits |
| Template rules | Masters/layouts to reuse and recurring elements that must remain intact |
| Delivery setting | Live presentation, standalone reading, print, or a combination |

Avoid arbitrary font-size rules across all decks. Establish a readable range for this canvas and setting, then inspect the actual output. Notes can hold supporting detail for a live talk; a standalone deck may need that detail on the slide.

## Template fidelity

1. Inspect both rendered examples and the native file. Theme tokens do not reveal every local override.
2. Reuse appropriate source masters and layouts. Keep layout-to-master relationships, theme fonts, logo placement, footer behavior, slide size, and brand-specific spacing.
3. Match recurring visible elements first. A similar palette alone is not template fidelity.
4. When a runtime cannot retain the original feature, choose a compatible editing path or explicitly identify the substitution. Do not silently flatten the template to an image.

## A representative slide should exercise risk

Choose the densest content layout, a chart/table slide, or one with non-Latin text if those are the hardest parts of the deck. Inspect it at readable resolution before applying its design broadly. A title slide alone rarely proves that the data and body layouts work.

## Charts and tables

- Match the chart to the comparison: category magnitude, time trend, part-to-whole, distribution, or relationship. Avoid decorative complexity that obscures values.
- Ensure the visual encoding matches the data and label nonzero baselines or unusual scales when they could mislead.
- Use native chart objects with editable series data when the authoring path supports them; keep the source dataset or embedded workbook consistent.
- Use native table cells for exact-value lookup. Set intentional column widths, alignment, and header contrast; verify long labels and Vietnamese diacritics do not clip.
- Respect supplied number formats and reporting periods. Do not convert missing data to zero or round away a meaningful difference.
