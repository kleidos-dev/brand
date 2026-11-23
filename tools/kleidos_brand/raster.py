# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""Drawing an SVG to pixels with Chromium, through Playwright, headless.

One browser draws every image of ``brand`` and ``social``. Its version is
recorded with the images (``exports.json``), because the same SVG can come out
a few pixels different from another version: a comparison against the record
is refused under a different browser instead of reported as a difference.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

#: The page is XHTML, so Chromium reads the SVG with its XML parser, as the
#: checks do; an HTML parser reads some markup otherwise.
PAGE_SUFFIX = ".xhtml"

#: Waits until every font the page declared has loaded (``fonts.ready`` also
#: resolves after a failed load, so each face's status is read), every picture
#: is decoded, and two frames have been painted.
SETTLE_JS = """async () => {
  await document.fonts.ready;
  const failed = [...document.fonts]
    .filter((face) => face.status !== 'loaded')
    .map((face) => face.family);
  const pictures = [...document.images, ...document.querySelectorAll('image')];
  await Promise.all(pictures.map((p) => (p.decode ? p.decode().catch(() => null) : null)));
  await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
  return failed;
}"""


class FontNotLoaded(RuntimeError):
    """A page declared a font face that did not load: the image would be drawn in a fallback."""


def page(svg: str, size: tuple[int, int], head: str = "", hide: tuple[str, ...] = ()) -> str:
    """Return the page an export is a screenshot of: *svg* inline, stretched to *size* pixels.

    :param head: Extra CSS, for instance the ``@font-face`` rules of a source with live text.
    :param hide: The ids of the groups not drawn (a source's ``guides`` layer).
    """
    markup = re.sub(r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>", "", svg)
    width, height = size
    hidden = "".join(f"#{name}{{display:none}}\n" for name in hide)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en"><head><meta charset="utf-8"/>
<style>
{head}
html,body{{margin:0;padding:0;background:transparent}}
body{{width:{width}px;height:{height}px;overflow:hidden}}
body>svg{{display:block;width:{width}px;height:{height}px}}
{hidden}</style></head><body>{markup}</body></html>
"""


class Browser:
    """Chromium, opened once for a run of exports.

    Use as a context manager. Playwright is imported on entry, so a static
    check never needs it installed.
    """

    def __init__(self) -> None:
        self._playwright: Any = None
        self._browser: Any = None
        self._page: Any = None
        self._scratch: tempfile.TemporaryDirectory[str] | None = None
        self.version = ""

    def __enter__(self) -> Browser:
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch()
        self.version = self._browser.version
        context = self._browser.new_context(device_scale_factor=1, color_scheme="dark")
        self._page = context.new_page()
        self._scratch = tempfile.TemporaryDirectory(prefix="kleidos-brand-")
        return self

    def __exit__(self, *_: object) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        if self._scratch is not None:
            self._scratch.cleanup()

    def shoot(self, document: str, size: tuple[int, int], name: str = "page") -> bytes:
        """Return the screenshot of *document* at *size*, once everything is settled, on
        transparency."""
        if self._scratch is None or self._page is None:
            raise RuntimeError("the browser is not open: draw inside `with Browser() as browser:`")
        path = Path(self._scratch.name) / f"{name}{PAGE_SUFFIX}"
        path.write_text(document, encoding="utf-8")
        self._page.set_viewport_size({"width": size[0], "height": size[1]})
        self._page.goto(path.resolve().as_uri())
        failed = self._page.evaluate(SETTLE_JS)
        if failed:
            raise FontNotLoaded(
                f"{name}: these font faces did not load: {', '.join(sorted(set(failed)))}"
            )
        shot: bytes = self._page.screenshot(omit_background=True)
        return shot

    def draw(
        self, svg: str, size: tuple[int, int], name: str = "page", hide: tuple[str, ...] = ()
    ) -> bytes:
        """Return the screenshot of *svg* stretched to *size* pixels."""
        return self.shoot(page(svg, size, hide=hide), size, name)
