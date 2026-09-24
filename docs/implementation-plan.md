# Implementation plan

## Outcome

Ship a usable, repository-contained v0.1 of Superpowerpoint: composable PowerPoint skills, a Codex plugin manifest, portable skill installation, deterministic PPTX inspection, examples, and verification. The user authorized planning and full implementation on 2026-09-24.

## Design

Organize presentation work around a clear brief, an explicit plan, scoped execution, independent review and verification before delivery. Keep human checkpoints proportional to uncertainty and honor existing authorization. A small text edit must not restart a whole-deck design workflow.

Six skills share a single router:

1. `superpowerpoint`: entry point, task routing, scope, continuity.
2. `planning-powerpoint`: brief, evidence inventory, storyboard and work plan.
3. `designing-powerpoint`: template analysis, typography, layout and representative slides.
4. `building-powerpoint`: capability-aware editable authoring and bounded parallel work.
5. `editing-powerpoint`: minimal changes, preservation and round-trip checks.
6. `reviewing-powerpoint`: content, package and visual review, repair and delivery.

The library is renderer-independent. An adapter documents the installed Presentations capability; no private machine path or proprietary runtime is required for basic inspection. The demo uses an available renderer and labels synthetic data. No startup hooks, external services, tracking, model API keys or global configuration changes are needed.

## Work packages

- [x] Define task routing, workflow stages and validation requirements.
- [x] Author six concise skills, selectively loaded references, and Codex UI metadata.
- [x] Implement a read-only PPTX inspector with JSON output, meaningful exit status and regression tests.
- [x] Add a no-overwrite portable installer, repository validator, plugin manifest and cross-platform CI configuration.
- [x] Build a Vietnamese example containing editable text, table and chart; inspect rendered slides.
- [x] Run independent scenario review, fix demonstrated issues, run project checks and document unavailable checks.

Implementation evidence and remaining environment/evaluation limitations are recorded in [validation.md](validation.md). The local code suite, repository checks, sample export and one independent behavioral scenario were exercised. Remote CI, five additional behavior scenarios and native PowerPoint compatibility remain unexecuted. The optional Windows renderer has a documented native teardown failure after writing previews.

## Acceptance criteria

- Every skill has valid name/description, real links and a distinct trigger.
- Native installation copies the complete collection and resources without overwriting existing skills.
- PPTX checks follow presentation order and inspect notes, relationships, editable evidence, slide count, explicit text sizes and direct object bounds. Results explicitly separate mechanical evidence from visual/factual judgment.
- Tests cover malformed/missing packages, slide ordering, notes, relationships, hidden slides and editable object requirements, plus installer conflicts.
- A real sample PPTX opens in the selected library, passes declared structural requirements and has a render for every slide. Do not claim Microsoft PowerPoint was tested without opening it there.
- README explains quick start, renderer requirements, commands, workflow and what was actually tested.

## Scope boundaries

Do not publish, install globally, create marketplace entries outside this project, or overwrite a source presentation. PPTX rendering needs a separately available presentation engine. Automated XML checks cannot prove visual layout, factual truth, accessibility or fidelity in every office application.
