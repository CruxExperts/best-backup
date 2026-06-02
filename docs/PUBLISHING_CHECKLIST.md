# Publishing checklist

Use this checklist before making the repository public or cutting a release.

## Documentation and community files

- [ ] `README.md` describes the project, install path, quick start, docs, and license.
- [ ] `INSTALL.md` and `QUICKSTART.md` are current.
- [ ] `SECURITY.md` explains supported versions and vulnerability reporting.
- [ ] `.github/CONTRIBUTING.md` documents setup, tests, commits, and PR expectations.
- [ ] `SUPPORT.md` explains where users should ask questions or get help.
- [ ] `.github/ISSUE_TEMPLATE/` and `.github/pull_request_template.md` are present.
- [ ] `LICENSE` has the intended owner and license.
- [ ] `docs/VERSIONING.md` describes release/version checks and local hook setup.

## Automation

- [ ] `git config core.hooksPath .githooks` is set in the active checkout.
- [ ] `.githooks/commit-msg` validates conventional commit subjects.
- [ ] `.githooks/pre-push` runs version sync, generated-doc checks, and whitespace checks.
- [ ] `.github/workflows/ci.yml` runs syntax, tests, CLI docs, version sync, support doc presence, and publishing readiness checks.
- [ ] `.github/workflows/release-notes.yml` verifies the tag, builds with `uv build`, and creates a GitHub release from `v*` tags.
- [ ] CI and release workflows smoke test the installed wheel.
- [ ] GitHub workflow actions are on current supported major versions.
- [ ] GitHub workflows declare least-privilege `permissions`.
- [ ] CI installs dependencies with `uv sync --locked` and runs commands with `uv run`.

## Version and release state

- [ ] `VERSION` contains the intended semantic version.
- [ ] `bbackup/__init__.py`, `pyproject.toml`, README badge, `CHANGELOG.md`, and generated CLI skills docs match `VERSION`.
- [ ] `pyproject.toml` requires Python `>=3.12`.
- [ ] `.python-version` pins the local baseline to `3.12`.
- [ ] `uv.lock` is present and current.
- [ ] `CHANGELOG.md` has a dated section for the release.
- [ ] `uv sync --locked` passes.
- [ ] `uv run python scripts/check_version_sync.py` passes.
- [ ] `uv run python scripts/check_publishing_ready.py` passes.
- [ ] `uv run python scripts/generate_cli_skills.py --check` passes.

## Scrub

- [ ] No secrets, API keys, tokens, private keys, `.env` files, or credentials are tracked.
- [ ] No local backup archives, logs, caches, or runtime state are tracked.
- [ ] No machine-specific install paths are documented as required paths.
- [ ] Public URLs point to the intended GitHub repository.
- [ ] Localsetup runtime state and agent run ledgers remain untracked.

## Validation

```bash
uv sync --locked
uv run python scripts/check_version_sync.py
uv run python scripts/check_publishing_ready.py
uv run python scripts/generate_cli_skills.py --check
uv run python -m py_compile bbackup.py bbman.py bbackup/*.py bbackup/data/*.py bbackup/management/*.py scripts/*.py
uv build
uv run python scripts/smoke_installed_artifact.py
uv run pytest
git diff --check
```
