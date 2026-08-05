from pathlib import Path

from scripts import check_markdown_standards


FIXTURE = Path(__file__).parent / "fixtures" / "markdown" / "changelog-duplicate-category.md"
UNVERSIONED_FIXTURE = Path(__file__).parent / "fixtures" / "markdown" / "changelog-unversioned-category.md"
SAME_VERSION_DATES_FIXTURE = (
    Path(__file__).parent / "fixtures" / "markdown" / "changelog-same-version-different-dates.md"
)


def test_same_release_category_heading_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        check_markdown_standards,
        "relative_name",
        lambda _path: "CHANGELOG.md",
    )
    errors = check_markdown_standards.scan_file(FIXTURE)

    assert any(
        "heading anchor is duplicated in the same changelog version: added" in error
        for error in errors
    ), errors


def test_category_after_non_version_heading_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        check_markdown_standards,
        "relative_name",
        lambda _path: "CHANGELOG.md",
    )
    errors = check_markdown_standards.scan_file(UNVERSIONED_FIXTURE)

    assert any(
        "release category heading must be under a version heading: added" in error
        for error in errors
    ), errors


def test_same_release_identifier_with_different_dates_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        check_markdown_standards,
        "relative_name",
        lambda _path: "CHANGELOG.md",
    )
    errors = check_markdown_standards.scan_file(SAME_VERSION_DATES_FIXTURE)

    assert any(
        "heading anchor is duplicated in the same changelog version: added" in error
        for error in errors
    ), errors
