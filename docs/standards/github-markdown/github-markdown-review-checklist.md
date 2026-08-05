---
schema: "kbmd/1.0"
id: "bbackup://standards/github-markdown-review-checklist"
title: "GitHub Markdown Review Checklist"
description: "Repeatable review gate for repository Markdown, including structure, rendering, accessibility, provenance, and semantic integrity."
type: "review-checklist"
status: "active"
language: "en-US"
version: "1.1.0"
created: "2026-08-04T18:32:18-05:00"
updated: "2026-08-04T19:25:53-05:00"
review_after: "2026-11-04"
review_owner: "bbackup repository maintainers"
generated_by:
  agent: "OpenAI ChatGPT"
  model: "GPT-5.6 Pro"
adapted_by:
  agent: "OpenAI Codex"
  model: "openai-codex/gpt-5.6-luna"
  date: "2026-08-04"
provenance: >-
  Derived from the bbackup GitHub Markdown Writing Standard, the supplied capabilities and provenance standards, and
  the official GitHub writing and editorial sources listed in the provenance register. The source register records
  original input checksums and the transformation into this repository copy.
source_inputs:
  - name: "bbackup GitHub Markdown Writing Standard, version 1.1.0"
    type: "governing standard"
  - name: "Supplied GitHub Markdown capabilities, writing, and provenance standards"
    type: "local adaptation inputs"
  - name: "GitHub Writing on GitHub documentation reviewed 2026-08-04"
    type: "official documentation"
intended_use: >-
  Applied before merging a new or materially revised repository Markdown document.
audience:
  - "Authors"
  - "Documentation agents"
  - "Reviewers"
  - "Repository maintainers"
authority: "bbackup repository documentation quality gate"
sensitivity: "public"
license: "not specified"
tags:
  - "github-markdown"
  - "review-checklist"
  - "quality-gate"
  - "accessibility"
  - "provenance"
---
# GitHub Markdown review checklist

Use this checklist as a release gate, not as decorative task-list formatting.

Apply the [GitHub Markdown Writing Standard](github-markdown-writing-standard.md) and record source evidence in the
[GitHub Markdown Source Provenance](github-markdown-source-provenance.md) register.

| Control | Value |
|:--|:--|
| Status | Active |
| Version | `1.1.0` |
| Authority | bbackup repository maintainers |
| Gate | New or materially revised public Markdown |


## bbackup publication scope

Apply this gate to root user documentation, `.github/` community and contribution files, `docs/` reference and
standards files, and intentionally published Markdown under `scripts/` or `bbackup/data/`. For generated documents,
review the generator and the rendered output together. Do not apply this checklist to private agent policy or ignored
runtime ledgers unless those files are being prepared for publication.

## bbackup-specific checks

- [ ] Narrative behavior claims match the code, `VERSION`, `pyproject.toml`, and `config.yaml.example`.
- [ ] Generated CLI docs were changed through `scripts/generate_cli_skills.py` and pass `--check`; the docs and
      `bbackup/data/` mirrors are identical.
- [ ] Publishing and version checks pass before release or commit.
- [ ] Docker-socket warnings, destructive restore commands, encryption-key guidance, and remote-upload claims are
      explicit and accurate.
- [ ] Public Markdown contains no credentials, private paths, ignored runtime state, or internal-only instructions.
- [ ] Checked-in assets have descriptive alt text and a source, transformation, and license record or an explicit
      unresolved provenance note.
- [ ] `.github` issue and pull-request templates use their required GitHub context syntax and are not judged as
      ordinary knowledge documents.


## Authority and purpose

- [ ] The document states its purpose, audience, authority, status, and intended use.
- [ ] The editor identified the authoritative source before changing the document.
- [ ] Source-derived content, outside research, inference, and unresolved assumptions are distinguishable.
- [ ] Presentation edits did not silently change a governing decision.
- [ ] The semantic version reflects the significance of the change.

## Front matter and provenance

- [ ] The YAML delimiters are balanced.
- [ ] Required identity, version, timestamp, provenance, source, audience, and authority fields are present.
- [ ] Stable IDs were preserved unless an identity change was intentional.
- [ ] Supersession and related-document links are current.
- [ ] The review date is realistic.

## Structure and navigation

- [ ] The document contains exactly one H1.
- [ ] Body sections begin at H2.
- [ ] No heading level is skipped.
- [ ] Headings are unique and sentence case; only `CHANGELOG.md` may repeat release-category headings under version headings.
- [ ] Every heading has content before a deeper heading begins.
- [ ] Long content has a curated map that supplements rather than duplicates GitHub's outline.
- [ ] Custom anchors are unique, prefixed, lowercase, and attached to visible targets.
- [ ] Internal section links resolve.

## Prose and scanability

- [ ] The opening paragraph states what the document is and why it matters.
- [ ] Each major section begins with its conclusion or decision.
- [ ] Paragraphs focus on one topic.
- [ ] Technical terms match the authoritative source.
- [ ] Ambiguous pronouns and stacked modifiers were removed where practical.
- [ ] Bold, italic, and code formatting carry meaning rather than decoration.
- [ ] The document has no unnecessary alert, table, diagram, or collapsed block.

## Lists, tables, and task lists

- [ ] Bulleted items are grammatically parallel.
- [ ] Numbered lists are sequential or ranked.
- [ ] Task lists represent real work, obligations, or acceptance gates.
- [ ] Tables compare consistent attributes.
- [ ] Table separator rows are valid.
- [ ] Literal pipes inside cells are escaped.
- [ ] Wide or complex tables have a prose summary or a clearer alternate structure.

## Code and technical literals

- [ ] Every fenced code block is closed.
- [ ] Language identifiers are lower-case and appropriate.
- [ ] Commands omit unnecessary shell prompts.
- [ ] Destructive commands have warnings and scope information.
- [ ] Placeholders are explicit and visually distinct.
- [ ] Filenames, paths, identifiers, and literal values use backticks consistently.

## Links and sources

- [ ] Repository-local links use relative paths where practical.
- [ ] Link text is descriptive and on one source line.
- [ ] Moving branch links are not used as immutable evidence.
- [ ] Every factual external claim has a nearby source when the document requires citations.
- [ ] The source register records review dates and applicability.
- [ ] Restricted, private, or access-controlled links are labeled.

## Images, diagrams, and math

- [ ] Every meaningful image has useful alt text.
- [ ] Complex figures have a visible long description or equivalent data.
- [ ] Captions identify source and transformation status.
- [ ] Diagrams supplement complete prose or list descriptions.
- [ ] Mermaid diagrams render without custom theme assumptions.
- [ ] Meaning does not depend on color alone.
- [ ] Math symbols are defined near their first use.
- [ ] Technical geometry and data were verified at the required accuracy tier.

## GitHub-specific components

- [ ] The document uses no more than two rendered alerts.
- [ ] Alerts are not consecutive or nested.
- [ ] `<details>` blocks do not hide prerequisites, safety information, or core decisions.
- [ ] `<details>` and `<summary>` tags are balanced.
- [ ] Raw HTML is limited to the approved local profile.
- [ ] No Liquid, `AUTOTITLE`, custom CSS, JavaScript, iframe, or remote executable embed is present.
- [ ] The document does not depend on issue-only color, closing, task, mention, or snippet behavior.

## Final rendering and release

- [ ] The file was inspected as plain text.
- [ ] The file was inspected in GitHub's rendered view or a renderer verified against the required GitHub features.
- [ ] Light and dark rendering were checked for diagrams and images.
- [ ] Relative links and assets resolve from the committed file location.
- [ ] The input and output checksums were recorded for a regenerated artifact.
- [ ] Known limitations and unresolved questions are explicit.
- [ ] The final reviewer can state exactly what changed and what did not change.
