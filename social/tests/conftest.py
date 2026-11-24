# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""What the tests share: the tools on the path, a throwaway copy of the pack, the browser.

- ``tree``: a copy of the pack (sources, pictures and record, without git's folder or the caches)
  for a test to plant a defect in, at ``<tmp>/brand/social``. Every other entry of that
  ``<tmp>/brand`` is a link to the real brand repository, which no test of this kind changes;
- ``tree_with_brand``: the same inside its own copy of brand, for a test that changes brand;
- ``chromium``: an open browser; a test that needs it is skipped when Playwright's Chromium is not
  installed.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from kleidos_brand.raster import Browser

ROOT = Path(__file__).resolve().parents[1]
#: The brand repository the pack is in.
BRAND = ROOT.parent
sys.path.insert(0, str(ROOT / "tools"))

SKIPPED_ANYWHERE = {".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
#: What a copy of brand leaves out at its root: the pack (copied on its own), build output and
#: coverage.
SKIPPED_IN_BRAND = {ROOT.name, "dist", ".coverage", "coverage.xml"}


def _skipped(top: Path, at_top: set[str]) -> Callable[[str, list[str]], set[str]]:
    def skipped(folder: str, names: list[str]) -> set[str]:
        out = {name for name in names if name in SKIPPED_ANYWHERE}
        if Path(folder) == top:
            out |= {name for name in names if name in at_top}
        return out

    return skipped


def _copy(target: Path, with_brand: bool) -> Path:
    """Copy the pack to *target* (``<tmp>/brand/social``), inside a copy of brand or links to it."""
    brand = target.parent
    if with_brand:
        shutil.copytree(BRAND, brand, ignore=_skipped(BRAND, SKIPPED_IN_BRAND), symlinks=True)
    else:
        brand.mkdir(parents=True)
        for entry in BRAND.iterdir():
            if entry.name not in SKIPPED_ANYWHERE | SKIPPED_IN_BRAND:
                (brand / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    shutil.copytree(ROOT, target, ignore=_skipped(ROOT, {"dist"}))
    return target


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "browser: draws with Chromium through Playwright")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """Return a copy of the pack a test may change, the rest of brand the real one."""
    return _copy(tmp_path / "brand" / ROOT.name, with_brand=False)


@pytest.fixture
def tree_with_brand(tmp_path: Path) -> Path:
    """Return a copy of the pack inside a copy of brand, both a test's to change."""
    return _copy(tmp_path / "brand" / ROOT.name, with_brand=True)


@pytest.fixture(scope="session")
def chromium() -> Iterator[Browser]:
    """Return an open browser, or skip when Playwright's Chromium is not installed."""
    import pack  # noqa: F401  puts brand's tools on the path
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
