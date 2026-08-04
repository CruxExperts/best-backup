"""Tests for repository pytest execution policy."""

import importlib
import os
from collections.abc import Callable
from typing import cast

import pytest


worker_count = cast(
    Callable[[object], int],
    getattr(importlib.import_module("tests.conftest"), "pytest_xdist_auto_num_workers"),
)


@pytest.mark.parametrize(
    ("cpus", "expected"),
    [
        (None, 1),
        (1, 1),
        (2, 1),
        (3, 1),
        (12, 6),
        (15, 7),
        (16, 8),
        (64, 8),
    ],
)
def test_xdist_worker_count_uses_half_cpus_capped_at_eight(
    monkeypatch: pytest.MonkeyPatch,
    cpus: int | None,
    expected: int,
) -> None:
    monkeypatch.setattr(os, "cpu_count", lambda: cpus)

    assert worker_count(None) == expected
