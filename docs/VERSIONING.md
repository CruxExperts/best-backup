# Versioning

`VERSION` is the canonical release version for this repository. Release-facing
references must match it before publishing:

- `bbackup/__init__.py` `__version__`
- `pyproject.toml` `version`
- `pyproject.toml` `requires-python` set to `>=3.12`
- README version badge
- `CHANGELOG.md` current release header and `[Unreleased]` compare target
- generated CLI skills docs

Run the version sync check:

```bash
uv run python scripts/check_version_sync.py
```

Regenerate CLI skills docs after command metadata or package version changes:

```bash
uv run python scripts/generate_cli_skills.py
uv run python scripts/generate_cli_skills.py --check
```

Refresh the locked dependency graph only after dependency or supported Python
version changes:

```bash
uv lock
uv sync --locked
```

## Commit and hook setup

This repo includes local Git hooks in `.githooks/`. Git does not enable tracked
hook directories automatically after clone, so enable them once per checkout:

```bash
git config core.hooksPath .githooks
```

The hooks enforce conventional commit subjects and run release-readiness checks
before push.

## Release flow

1. Update `VERSION`.
2. Sync the version references listed above.
3. Run `uv lock` if dependencies or supported Python versions changed.
4. Add a dated `CHANGELOG.md` section for the release.
5. Run:

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

6. Commit with a conventional commit message.
7. Tag the release as `vX.Y.Z` and push the tag after CI is green.

Pushing a tag that matches `v*` runs `.github/workflows/release-notes.yml`.
The release job verifies that the tag matches `VERSION`, runs the version and
publishing checks, runs Ruff, py_compile, generated-doc checks, pytest, builds
release artifacts with `uv build`, smoke tests the built wheel, and creates a
GitHub release from the matching `CHANGELOG.md` section. The release job fails
if the matching changelog section is missing.
