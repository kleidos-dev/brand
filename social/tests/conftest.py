# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""What the tests share: the tools on the path, a throwaway copy of the tree, the browser.

- ``tree``: a copy of this repository (sources, pictures and record, without the virtual environment
  or git's folder) for a test to plant a defect in. Its ``brand`` is a link to the real submodule,
  which no test of this kind changes;
- ``tree_with_brand``: the same with its own copy of the submodule, for a test that changes brand;
- ``chromium``: an open browser; a test that needs it is skipped when Playwright's Chromium is not
  installed.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from kleidos_brand.raster import Browser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

SKIPPED_ANYWHERE = {".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache"}


def _copy(target: Path, with_brand: bool) -> Path:
    def skipped(folder: str, names: list[str]) -> set[str]:
        out = {name for name in names if name in SKIPPED_ANYWHERE}
        if Path(folder) == ROOT:
            out |= {
                name for name in names if name == "dist" or (name == "brand" and not with_brand)
            }
        return out

    shutil.copytree(ROOT, target, ignore=skipped)
    if not with_brand:
        (target / "brand").symlink_to(ROOT / "brand", target_is_directory=True)
    return target


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "browser: draws with Chromium through Playwright")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """Return a copy of the repository a test may change, its brand the real one."""
    return _copy(tmp_path / "social", with_brand=False)


@pytest.fixture
def tree_with_brand(tmp_path: Path) -> Path:
    """Return a copy of the repository and of its submodule, both a test's to change."""
    return _copy(tmp_path / "social", with_brand=True)


@pytest.fixture(scope="session")
def chromium() -> Iterator[Browser]:
    """Return an open browser, or skip when Playwright's Chromium is not installed."""
    import pack  # noqa: F401  puts brand/tools on the path
    from kleidos_brand import raster

    try:
        from playwright.sync_api import Error as PlaywrightError
    except ImportError as error:
        pytest.skip(f"Playwright is not installed: {error}")
    opened = raster.Browser()
    try:
        opened.__enter__()
    except PlaywrightError as error:
        pytest.skip(f"Chromium is not available: {error}")
    yield opened
    opened.__exit__(None, None, None)
