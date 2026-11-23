# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""Parse XML (the SVG sources, the board fronts, the pictures' records) with no document type.

The one parser of the package. expat, as Python ships it (2.4.1 and newer),
expands no external entity and bounds entity amplification; this module also
refuses any document type declaration before expat sees the text, so no entity
can be declared at all. A refusal is an ``xml.etree.ElementTree.ParseError``,
the error a caller already handles for text that is not well-formed.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

#: A document type or entity declaration, in text or bytes.
_DECLARATION = re.compile(rb"<!(?:DOCTYPE|ENTITY)", re.IGNORECASE)


def fromstring(text: str | bytes) -> ET.Element:
    """Return the root element of *text*; raise ``ParseError`` on a document type declaration."""
    raw = text.encode("utf-8") if isinstance(text, str) else text
    if _DECLARATION.search(raw):
        raise ET.ParseError("a document type or entity declaration is refused")
    # The declaration check above leaves expat no entity to expand.
    return ET.fromstring(text)  # noqa: S314


def parse(path: str | Path) -> ET.Element:
    """Return the root element of the XML file at *path* (see :func:`fromstring`)."""
    return fromstring(Path(path).read_bytes())
