# Contributing

Thanks for taking the time to contribute. This document covers how to set up a development environment, the commit conventions the project uses, and what to expect from the review process.

---

## Development setup

For contributing you need a UV-managed editable environment so source changes take effect immediately:

```bash
git clone https://github.com/CruxExperts/best-backup.git
cd best-backup

uv sync --locked

# Verify
uv run bbackup --version
uv run bbman --version
```

You will need Docker running locally to test backup and restore operations. `rsync` is required for volume backups; install it with your system package manager if it is not already present.

Enable the repo-managed Git hooks once per checkout:

```bash
git config core.hooksPath .githooks
```

The hooks validate conventional commit subjects and run release-readiness checks before push. See [docs/VERSIONING.md](../docs/VERSIONING.md) for the full version and release checklist.

---

## Making changes

Keep changes focused. A pull request that fixes one bug or adds one feature is easier to review than one that combines several concerns.

Run the syntax check before pushing:

```bash
uv run python -m py_compile bbackup.py bbman.py bbackup/*.py bbackup/data/*.py bbackup/management/*.py scripts/*.py
```

---

## Commit messages

This project uses [conventional commits](https://www.conventionalcommits.org/). The prefix determines how the version is bumped on the next release:

| Prefix | Bump | When to use |
|---|---|---|
| `feat:` | minor | New user-visible feature |
| `fix:` | patch | Bug fix |
| `docs:` | patch | Documentation only |
| `refactor:` | patch | Code restructure, no behavior change |
| `perf:` | patch | Performance improvement |
| `test:` | patch | Test additions or changes |
| `chore:` | patch | Build, tooling, dependency updates |
| `feat!:` or `BREAKING CHANGE:` in body | major | Incompatible change |

One subject line, imperative mood, no trailing period. Example:

```
fix: handle missing Docker socket gracefully

Closes #12
```

---

## Pull requests

- Open a PR against `main`
- Fill in the PR template
- One feature or fix per PR
- CI must be green before merge

If you are fixing a reported issue, reference it in the PR description with `Closes #N` so it closes automatically on merge.

---

## Reporting bugs

Use the bug report issue template. The more detail you include (OS, Docker version, Python version, the exact command you ran, and the full error output), the faster it gets resolved.

---

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Treat everyone with respect.

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/CruxExperts/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->
