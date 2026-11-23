#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""Copy the nine board fronts from a checkout of the boards repository, or compare the copies with
one.

    tools/sync_from_boards.py --check <boards checkout>
    tools/sync_from_boards.py --copy <boards checkout>

``boards/<board>.svg`` are byte copies of ``<board>/svg/front.svg`` of the
boards repository, under its MIT License. ``--copy`` writes them and
``boards/boards.json`` (each copy's digest and the commit it was taken at),
and refuses a checkout whose fronts differ from its last commit; ``--check``
prints every copy that is not the checkout's file. Regenerate the images
after a copy (``tools/build.py``) and look at them.

The checkout's path is an argument and is stored nowhere. It must name the top
of a git checkout (:func:`checkout_folder`); git runs inside it and is given no
path but the fronts' own, and a front that leads out of the checkout is
refused. CI cannot run this: it holds the copies to the manifest instead
(``tools/check.py``).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kleidos_brand import BRAND_ROOT, boards

REPOSITORY = "https://github.com/kleidos-dev/boards"
#: The order a line-up shows the boards in (the site's), and how this repository names each one.
BOARDS = {
    "sticks3": "M5StickS3",
    "m5stickc-plus2": "M5StickC Plus2",
    "m5stickc-plus1": "M5StickC Plus 1.1",
    "m5stickc-plus-se": "M5StickC Plus SE",
    "coreink": "M5Stack CoreInk",
    "cores3-se": "M5Stack CoreS3 SE",
    "m5stack-core2-v13": "M5Stack Core2 v1.3",
    "cardputer": "M5Stack Cardputer ADV",
    "tdeck-plus": "LILYGO T-Deck Plus",
}
COMMENT = (
    "The board fronts under boards/: byte copies of the boards repository's <board>/svg/front.svg, "
    "under its"
    " MIT License, at the commit below. Written by tools/sync_from_boards.py --copy; do not edit."
)


def source(slug: str) -> str:
    """Return a front's path in the boards repository."""
    return f"{slug}/svg/front.svg"


def checkout_folder(value: str) -> Path:
    """Return the checkout *value* names, resolved; refuse what is not the top of one."""
    try:
        path = Path(value).resolve(strict=True)
    except OSError as error:
        raise argparse.ArgumentTypeError(f"{value!r} is not there: {error.strerror}") from error
    if not (path / ".git").exists():
        raise argparse.ArgumentTypeError(f"{value!r} is not the top of a git checkout")
    return path


def front(checkout: Path, slug: str) -> Path:
    """Return a front's file in the checkout; refuse one that leads out of it."""
    path = (checkout / source(slug)).resolve()
    if not path.is_relative_to(checkout.resolve()):
        raise SystemExit(f"{source(slug)}: leads out of the checkout")
    return path


def git(checkout: Path, *arguments: str) -> str:
    """Return what git prints in the checkout."""
    return subprocess.run(
        ["git", *arguments], cwd=checkout, check=True, capture_output=True, text=True
    ).stdout


def check(checkout: Path, root: Path = BRAND_ROOT) -> list[str]:
    """Return every copy that is not the checkout's file."""
    found = []
    for slug in BOARDS:
        theirs, ours = front(checkout, slug), root / boards.front_path(slug)
        if not theirs.is_file():
            found.append(f"{source(slug)}: not in the checkout")
        elif not ours.is_file() or ours.read_bytes() != theirs.read_bytes():
            found.append(
                f"{boards.front_path(slug)}: is not a byte copy of {source(slug)}; run --copy"
            )
    return found


def copy(checkout: Path, root: Path = BRAND_ROOT) -> int:
    """Copy every front and write the manifest."""
    paths = [source(slug) for slug in BOARDS]
    dirty = git(checkout, "status", "--porcelain", "--", *paths)
    if dirty.strip():
        print(
            f"the checkout's fronts differ from its last commit; commit them there first:\n{dirty}"
        )
        return 1
    commit = git(checkout, "rev-parse", "HEAD").strip()
    fronts = {slug: front(checkout, slug).read_bytes() for slug in BOARDS}
    (root / boards.BOARDS_DIR).mkdir(exist_ok=True)
    entries = {}
    for slug, name in BOARDS.items():
        target = root / boards.front_path(slug)
        target.write_bytes(fronts[slug])
        entries[slug] = {"name": name, "from": source(slug), "sha256": boards.digest(target)}
    manifest = {
        "$comment": COMMENT,
        "repository": REPOSITORY,
        "commit": commit,
        "license": "MIT",
        "boards": entries,
    }
    (root / boards.MANIFEST).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"copied {len(entries)} fronts at {commit[:12]}; now run tools/build.py and look at the "
        "images"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        metavar="BOARDS",
        type=checkout_folder,
        help="print every copy that is not this checkout's file",
    )
    mode.add_argument(
        "--copy",
        metavar="BOARDS",
        type=checkout_folder,
        help="copy every front from this checkout and write the manifest",
    )
    args = parser.parse_args(argv)
    if args.copy:
        return copy(args.copy)
    found = check(args.check)
    for line in found:
        print(line)
    if found:
        print(f"\n{len(found)} difference(s).")
        return 1
    print("sync check: every front is a byte copy of the boards repository's.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
