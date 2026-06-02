"""
Packaged runtime resource helpers.
"""

from __future__ import annotations

from importlib import resources


DATA_PACKAGE = "bbackup.data"


def read_text_resource(name: str) -> str:
    """Read a bundled text resource."""
    return resources.files(DATA_PACKAGE).joinpath(name).read_text(encoding="utf-8")


def resource_exists(name: str) -> bool:
    """Return True when a bundled resource is available."""
    return resources.files(DATA_PACKAGE).joinpath(name).is_file()
