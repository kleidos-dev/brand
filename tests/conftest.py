# SPDX-License-Identifier: MIT
"""What the tests share: the tools on the path, a throwaway copy of the tree, the browser marker.

- ``tree``: a copy of the repository (sources, generated files and record, without the virtual
  environment or git's folder) for a test to plant a defect in;
- ``browser`` marker: a test that draws with Chromium; skipped when Playwright's browser is not
  installed.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

SKIPPED_ANYWHERE = {".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache"}


def skipped(folder: str, names: list[str]) -> set[str]:
    """Leave out what is not part of the tree: caches, the environment, and the root's build output."""
    out = {name for name in names if name in SKIPPED_ANYWHERE}
    if Path(folder) == ROOT:
        out |= {name for name in names if name == "dist"}
    return out


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "browser: draws with Chromium through Playwright")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """Return a copy of the repository a test may change."""
    target = tmp_path / "brand"
    shutil.copytree(ROOT, target, ignore=skipped)
    return target


@pytest.fixture(scope="session")
def chromium():
    """Return an open browser, or skip when Playwright's Chromium is not installed."""
    from kleidos_brand import raster

    opened = raster.Browser()
    try:
        opened.__enter__()
    except Exception as error:  # noqa: BLE001 - any failure to launch means: not installed here
        pytest.skip(f"Chromium is not available: {error}")
    yield opened
    opened.__exit__(None, None, None)
