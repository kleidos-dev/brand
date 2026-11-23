# SPDX-License-Identifier: MIT
"""The record of what was built (``exports.json``) and the generated blocks of the README pages.

The record names the browser the pictures were drawn with and, for every
picture, its bytes and the bytes of what it was drawn from. It holds file
digests only: a commit's name would not survive a squashed history, and a
commit that changes nothing a picture reads should not make it stale.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

EXPORTS_JSON = Path("exports.json")
COMMENT = "Written by tools/build.py: the bytes of each picture and of what it was drawn from. Do not edit; run the builder."


def sha256(data: bytes) -> str:
    """Return the SHA-256 of *data*, in hex."""
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    """Return the SHA-256 of a file."""
    return sha256(path.read_bytes())


def load(root: Path) -> dict[str, Any]:
    """Return the record at *root*, or an empty one."""
    path = root / EXPORTS_JSON
    if not path.is_file():
        return {"files": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def dump(record: dict[str, Any]) -> str:
    """Return the record as the text of ``exports.json``."""
    ordered = {
        "$comment": COMMENT,
        **{key: value for key, value in record.items() if key != "$comment"},
    }
    return json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"


def block_markers(name: str) -> tuple[str, str]:
    """Return the two comment lines a generated block of a README page stands between."""
    return (
        f"<!-- BEGIN GENERATED: {name} (tools/build.py); do not edit by hand -->",
        f"<!-- END GENERATED: {name} -->",
    )


def with_block(text: str, name: str, body: str) -> str:
    """Return *text* with its generated block *name* holding *body*."""
    begin, end = block_markers(name)
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise ValueError(f"the page has no generated block {name!r}")
    return pattern.sub(lambda _: f"{begin}\n\n{body}\n\n{end}", text)


def human_bytes(count: int) -> str:
    """Return a byte count as a reader takes it in: ``96 kB``, ``1.2 MB``."""
    if count < 1000:
        return f"{count} B"
    if count < 1_000_000:
        return f"{count / 1000:.0f} kB"
    return f"{count / 1_000_000:.1f} MB"
