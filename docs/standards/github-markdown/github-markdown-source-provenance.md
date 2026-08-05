---
schema: "kbmd/1.0"
id: "bbackup://standards/github-markdown-source-provenance"
title: "GitHub Markdown Source Provenance"
description: "Page-by-page official source register for the repository GitHub Markdown writing and rendering profile."
type: "source-register"
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
  Records the official GitHub Markdown sources reviewed on 2026-08-04, the four supplied local standards imported
  into this repository, their original SHA-256 checksums, and the transformations applied for bbackup publication.
  Moving-branch source links remain identified as non-immutable evidence.
source_inputs:
  - name: "GitHub Writing on GitHub category and all listed pages"
    type: "official product documentation"
  - name: "github/docs public source Markdown"
    type: "official public source repository"
  - name: "GitHub Flavored Markdown Specification"
    type: "official syntax specification"
  - name: "GitHub Docs editorial guidance"
    type: "official writing guidance"
  - name: "Supplied GitHub Markdown capabilities, writing, review, and provenance standards"
    type: "local adaptation inputs"
intended_use: >-
  Provides durable provenance, scope decisions, exclusions, and refresh instructions for the local GitHub Markdown
  standard.
audience:
  - "Repository maintainers"
  - "Documentation agents"
  - "Technical writers"
  - "Auditors"
authority: "bbackup provenance register for the repository writing standard"
sensitivity: "public"
license: "not specified"
tags:
  - "github-markdown"
  - "source-provenance"
  - "github-docs"
  - "gfm"
  - "documentation-governance"
---
# GitHub Markdown source provenance

| Register control | Value |
|:--|:--|
| **Review date** | `2026-08-04` |
| **Primary scope** | Every page listed under GitHub's **Writing on GitHub** section |
| **Source form** | Rendered GitHub Docs page plus public Markdown source path in `github/docs` |
| **Renderer baseline** | GitHub Flavored Markdown specification |
| **Editorial supplement** | Official GitHub Docs style, readability, translation, content-design, and diagram guidance |
| **Refresh rule** | Recheck by `2026-11-04` or after a GitHub Markdown announcement |
| **Next revision authority** | bbackup repository maintainers |

The register supports the [GitHub Markdown Writing Standard](github-markdown-writing-standard.md), the
[Capabilities Reference](github-markdown-capabilities-reference.md), and the [Review Checklist](github-markdown-review-checklist.md).

## Imported source artifacts

These SHA-256 values identify the four supplied Markdown files before they were copied into the repository or
adapted. The source files were read from the operator-provided Downloads set on `2026-08-04`; no credential-bearing
content was present in the inputs.

| Supplied input | SHA-256 before adaptation | Repository destination |
|:--|:--|:--|
| `github-markdown-capabilities-reference.md` | `f06096c5d4470ce7422a50d99acb04a4bcb1f74df6039dbc01bfa6205bdc0131` | `docs/standards/github-markdown/github-markdown-capabilities-reference.md` |
| `github-markdown-writing-standard.md` | `bcbf90ed55b55f7f1da924bf7dfa818be0a4baea358fdb40c1ec6d1d02910a83` | `docs/standards/github-markdown/github-markdown-writing-standard.md` |
| `github-markdown-review-checklist.md` | `6b29bc0c000acf38dc2b0fa82c7483121cbf87765b165aa6b1c2557f51c2eacb` | `docs/standards/github-markdown/github-markdown-review-checklist.md` |
| `github-markdown-source-provenance.md` | `f653d7a44bcebcbb4c31a483e1e43d14db457d0f214bd07eb7a5bc7c80ae9b0d` | `docs/standards/github-markdown/github-markdown-source-provenance.md` |

The adaptation preserves the original source content as the starting point, then changes stable IDs, adoption status,
repository authority, publication sensitivity, cross-links, bbackup scope, and transformation metadata. It does not
relicense the supplied text; each adapted file retains `license: "not specified"`.

## Original metadata retained

All supplied files used `schema: "kbmd/1.0"`, `language: "en-US"`, `created: "2026-08-04T18:32:18-05:00"`,
`updated: "2026-08-04T18:32:18-05:00"`, `review_after: "2026-11-04"`, and
`generated_by: OpenAI ChatGPT / GPT-5.6 Pro`. The table records source identity and publication metadata before
adaptation.

| Artifact | Original stable ID | Original status | Original sensitivity | Original license |
|:--|:--|:--|:--|:--|
| Capabilities reference | `crux://standards/github-markdown-capabilities` | `proposed` | `internal` | `not specified` |
| Writing standard | `crux://standards/github-markdown-writing` | `proposed` | `internal` | `not specified` |
| Review checklist | `crux://standards/github-markdown-review-checklist` | `proposed` | `internal` | `not specified` |
| Source provenance | `crux://standards/github-markdown-source-provenance` | `proposed` | `internal` | `not specified` |

## Transformation ledger

The machine-readable [provenance manifest](github-markdown-provenance-manifest.json) records exact final SHA-256
values for all four adapted outputs. This source-provenance file does not embed its own hash; the separate manifest
records it without changing this file, and the final Git object or commit hash remains an independent integrity
authority for the self-describing register.

| Adapted output | SHA-256 after document adaptation | Version | Transformation summary |
|:--|:--|:--|:--|
| `docs/standards/github-markdown/github-markdown-capabilities-reference.md` | `34abcac2064c7cc974f05810a62840af34f05a2dd5e06429672ad21e7b0cde9d` | `1.1.0` | Retargeted identity and scope; replaced generic commands, diagrams, and missing assets with bbackup examples, a visible control table, and an explicit support boundary; corrected closing-keyword context to pull-request descriptions and commit messages. |
| `docs/standards/github-markdown/github-markdown-writing-standard.md` | `abdee1bf4b56a3fbfa9476279cfd42c41af94b54f1d1525202fcdcf44a888caf` | `1.1.0` | Added bbackup publication scope, authority hierarchy, metadata rendering boundary, and template exception; retargeted examples; corrected closing-keyword context to pull-request descriptions and commit messages; documented the structured changelog heading exception. |
| `docs/standards/github-markdown/github-markdown-review-checklist.md` | `1a14002e7d40d73713999fc07243f5154f8a89bd8f1a5b3784bed497a14ff79d` | `1.1.0` | Added bbackup-specific generated-doc, safety, public-scrub, asset, and template checks, governing links, and a visible control table; scoped heading uniqueness to exclude only release-category headings in `CHANGELOG.md`. |

## Method

The source review followed the public category inventory rather than selecting only the features used in the transformed brief. Every listed collection and detail page was classified into one of three groups:

1. **Repository-file capability**: syntax or behavior documented for `.md` files.
2. **Context-specific behavior**: behavior that belongs to issues, pull requests, discussions, comments, saved replies, or gists.
3. **GitHub Docs application behavior**: internal publishing syntax that does not belong in ordinary repository Markdown.

The local standard paraphrases and consolidates the official material. It does not reproduce the GitHub pages verbatim.

## Primary category inventory

- [Writing on GitHub category](https://docs.github.com/en/get-started/writing-on-github)
- [Category source directory](https://github.com/github/docs/blob/main/content/get-started/writing-on-github)

<details open>
<summary><strong>1. Getting started with writing and formatting on GitHub</strong></summary>

- [Collection overview](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github)
- [Collection source Markdown](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/index.md)

| Page | Rendered documentation | Source Markdown | Local disposition |
|:--|:--|:--|:--|
| Quickstart for writing on GitHub | [Open page](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github.md) | Normative capability overview |
| About writing and formatting on GitHub | [Open page](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/about-writing-and-formatting-on-github) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/about-writing-and-formatting-on-github.md) | Context and editor behavior |
| Basic writing and formatting syntax | [Open page](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax.md) | Normative repository syntax and GitHub extensions |

</details>
<details>
<summary><strong>2. Working with advanced formatting</strong></summary>

- [Collection overview](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting)
- [Collection source Markdown](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-advanced-formatting/index.md)

| Page | Rendered documentation | Source Markdown | Local disposition |
|:--|:--|:--|:--|
| Organizing information with tables | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-tables) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-tables.md) | Normative table syntax |
| Organizing information with collapsed sections | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections.md) | Normative details and summary syntax |
| Creating and highlighting code blocks | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-and-highlighting-code-blocks) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-advanced-formatting/creating-and-highlighting-code-blocks.md) | Normative fenced-code guidance |
| Creating diagrams | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams.md) | Normative diagram capability |
| Writing mathematical expressions | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/writing-mathematical-expressions) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-advanced-formatting/writing-mathematical-expressions.md) | Normative math capability |
| Autolinked references and URLs | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/autolinked-references-and-urls) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-advanced-formatting/autolinked-references-and-urls.md) | Mixed; repository and conversation contexts separated |
| Attaching files | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-advanced-formatting/attaching-files.md) | Contextual; durable repository assets preferred locally |
| About tasklists | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/about-tasklists) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-advanced-formatting/about-tasklists.md) | Mixed; Markdown checkboxes retained, retired tasklist blocks excluded |
| Creating a permanent link to a code snippet | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-a-permanent-link-to-a-code-snippet) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-advanced-formatting/creating-a-permanent-link-to-a-code-snippet.md) | Contextual; comment embedding excluded from repository profile |
| Using keywords in issues and pull requests | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/using-keywords-in-issues-and-pull-requests) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-advanced-formatting/using-keywords-in-issues-and-pull-requests.md) | Issue and pull-request context only |

</details>
<details>
<summary><strong>3. Working with saved replies</strong></summary>

- [Collection overview](https://docs.github.com/en/get-started/writing-on-github/working-with-saved-replies)
- [Collection source Markdown](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-saved-replies/index.md)

| Page | Rendered documentation | Source Markdown | Local disposition |
|:--|:--|:--|:--|
| About saved replies | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-saved-replies/about-saved-replies) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-saved-replies/about-saved-replies.md) | Reviewed; outside repository-file rendering |
| Creating a saved reply | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-saved-replies/creating-a-saved-reply) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-saved-replies/creating-a-saved-reply.md) | Reviewed; outside repository-file rendering |
| Editing a saved reply | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-saved-replies/editing-a-saved-reply) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-saved-replies/editing-a-saved-reply.md) | Reviewed; outside repository-file rendering |
| Deleting a saved reply | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-saved-replies/deleting-a-saved-reply) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-saved-replies/deleting-a-saved-reply.md) | Reviewed; outside repository-file rendering |
| Using saved replies | [Open page](https://docs.github.com/en/get-started/writing-on-github/working-with-saved-replies/using-saved-replies) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/working-with-saved-replies/using-saved-replies.md) | Reviewed; outside repository-file rendering |

</details>
<details>
<summary><strong>4. Editing and sharing content with gists</strong></summary>

- [Collection overview](https://docs.github.com/en/get-started/writing-on-github/editing-and-sharing-content-with-gists)
- [Collection source Markdown](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/editing-and-sharing-content-with-gists/index.md)

| Page | Rendered documentation | Source Markdown | Local disposition |
|:--|:--|:--|:--|
| Creating gists | [Open page](https://docs.github.com/en/get-started/writing-on-github/editing-and-sharing-content-with-gists/creating-gists) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/editing-and-sharing-content-with-gists/creating-gists.md) | Reviewed; gist workflow, not repository-file rendering |
| Forking and cloning gists | [Open page](https://docs.github.com/en/get-started/writing-on-github/editing-and-sharing-content-with-gists/forking-and-cloning-gists) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/editing-and-sharing-content-with-gists/forking-and-cloning-gists.md) | Reviewed; gist workflow |
| Saving gists with stars | [Open page](https://docs.github.com/en/get-started/writing-on-github/editing-and-sharing-content-with-gists/saving-gists-with-stars) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/editing-and-sharing-content-with-gists/saving-gists-with-stars.md) | Reviewed; gist workflow |
| Moderating gist comments | [Open page](https://docs.github.com/en/get-started/writing-on-github/editing-and-sharing-content-with-gists/moderating-gist-comments) | [Open source](https://github.com/github/docs/blob/main/content/get-started/writing-on-github/editing-and-sharing-content-with-gists/moderating-gist-comments.md) | Reviewed; gist workflow |

</details>

## Supplemental official sources

| Source | Role in the local standard |
|:--|:--|
| [GitHub Flavored Markdown Specification](https://github.github.com/gfm/) | Formal CommonMark-based grammar and GFM extensions |
| [GitHub Docs Style Guide](https://docs.github.com/en/contributing/style-guide-and-content-model/style-guide) | Heading, emphasis, alert, code, image, and editorial conventions adapted for local use |
| [Best practices for GitHub Docs](https://docs.github.com/en/contributing/writing-for-github-docs/best-practices-for-github-docs) | Audience, structure, readability, and scanability principles |
| [Content design principles](https://docs.github.com/en/contributing/writing-for-github-docs/content-design-principles) | User-centered scope, clarity, meaning, correctness, and consistency |
| [Writing content to be translated](https://docs.github.com/en/contributing/writing-for-github-docs/writing-content-to-be-translated) | Translation-friendly source-language rules |
| [Using Markdown and Liquid in GitHub Docs](https://docs.github.com/en/contributing/writing-for-github-docs/using-markdown-and-liquid-in-github-docs) | Reviewed to identify and exclude GitHub Docs-only Liquid, `AUTOTITLE`, reusable, version, and product syntax |

## Governing conclusions from the source review

### Included in the repository profile

- GFM headings, emphasis, blockquotes, fenced code, links, relative paths, images, lists, tables, task-list syntax, autolinks, and strikethrough
- GitHub alerts, with strict local limits
- `<details>` and `<summary>`
- `<picture>` with an `<img>` fallback
- Mermaid, GeoJSON, TopoJSON, ASCII STL, and mathematical expressions
- Footnotes in repository Markdown files
- Custom anchors and HTML comments
- Standard sanitized HTML used within the local allowlist

### Included with context restrictions

- Issue and pull-request references, because rich behavior differs between conversations and files
- Mentions, because notification behavior is conversational and should not be a documentation dependency
- Task lists, because ordinary checkboxes remain supported while the former dedicated tasklist block is retired
- Attachments, because a durable document should use governed repository assets rather than incidental conversation uploads
- Permanent code links, because rich code embedding is limited to comments and same-repository contexts

### Reviewed but excluded from repository-file rendering

- Closing keywords and duplicate keywords
- Color swatches that appear only in issues, pull requests, and discussions
- Saved-reply creation and management
- Gist creation, forking, starring, and moderation workflows
- GitHub Docs Liquid, `AUTOTITLE`, reusables, product tags, version tags, operating-system tags, tool tags, and Octicon Liquid helpers
- GitHub Docs-specific table row-header and code-annotation helpers

## Durability limits

The register points to live documentation and the moving `main` branch of `github/docs`. That choice records what was reviewed on `2026-08-04` but is not an immutable historical snapshot. During repository integration, a maintainer MAY replace source links with commit-pinned links if strict audit reproduction is required.

The local standard MUST be refreshed when GitHub changes any of the following:

- Markdown parser or sanitizer behavior
- Alert syntax or supported alert types
- Mermaid, math, map, or STL rendering
- Footnote support
- Task-list behavior
- Relative-link transformation
- Supported HTML elements or attributes
- GitHub Docs guidance that the repository has adopted as local policy
