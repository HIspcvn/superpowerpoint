# Preservation when editing PowerPoint

An existing PPTX is a related package of slides, masters, layouts, themes, charts, embedded data, media, notes, and other parts. A visually correct changed slide can coexist with lost features elsewhere.

## Establish the baseline

Keep a source copy and record the slide count/order and dimensions. Inventory the features that matter for this file: masters/layouts, theme/font usage, text and hyperlinks, notes, native tables/charts, embedded workbooks, images, audio/video, animations, transitions, comments, accessibility text, and linked or embedded objects. Do not promise preservation of a feature the editing path cannot read or retain.

For complex decks, compare package part names, relationship targets, and content types before and after. Byte-level differences alone are not necessarily defects because applications may rewrite harmless metadata; deleted parts, orphaned relationships, or changed data need investigation.

## Choose the least disruptive path

- Prefer a native application workflow for features specific to PowerPoint when it is available and authorized.
- Use targeted object or OOXML changes when the required scope is narrow and the change can retain untouched parts and valid relationships.
- Use a full library import/export only after checking its preservation behavior for the file's required features. Avoid rebuilding the entire deck to fix a single string.

## Feature-specific checks

| Feature | Preservation check |
| --- | --- |
| Charts | Chart type, series order, categories, labels, axes, units, formulas, caches, external links, and embedded workbook agree |
| Embedded workbook | Original workbook content and formulas outside the requested update remain intact; plotted values match the data |
| Text | Keep run styling, paragraph settings, bullet levels, links, language, and diacritics; inspect overflow after replacement |
| Tables | Keep native cells, merges, widths, number formats, and the distinction between empty and zero |
| Template | Retain valid slide-layout-master-theme links, aspect ratio, logos, footer/page-number behavior, and font choices |
| Animation/transitions | Preserve timing and relationship parts; test actual playback when it matters |
| Audio/video/OLE | Preserve embedded or linked targets and relationships; test activation or playback in the target app where required |
| Notes and sources | Keep speaker notes, citations, source access, and relevant notes master relationships |
| Hyperlinks/navigation | Keep external URLs and internal slide targets valid after slide reordering or deletion |
| Accessibility | Preserve meaningful alternative text and reading order where supported |

Updating only a chart's cached values can leave “Edit Data” showing stale values. Updating only its workbook can leave the rendered chart stale. Use an API that maintains both or deliberately synchronize and validate both representations.

## Compare and disclose

Check the full deck for unintended changes and visually compare changed slides against the source. Structural retention is evidence about package contents, not proof that effects play correctly. Record the authoring path, renderer, and whether actual PowerPoint opening/playback was performed.

If a tool changes fonts, drops an extension, flattens an object, or cannot preserve a feature, describe that specific limitation and its affected slides. Preserve the untouched source so the user can recover or continue in PowerPoint.
