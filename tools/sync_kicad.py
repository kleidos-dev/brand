#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Hand the KiCad kit to a repository that draws with it, as byte copies held to a manifest.

    tools/sync_kicad.py --copy <dir>    write the kit's files into a consumer's kit folder
                                        (boards/_shared/kicad/, meter/hardware/kicad/) with
                                        KIT.json: the kit's version, this repository's address,
                                        the commit the files were taken at and each file's SHA-256
    tools/sync_kicad.py --check <dir>   say whether that folder holds this checkout's kit, and
                                        nothing else

The kit's files must be committed here before they are copied, so the commit
KIT.json names holds them. A consumer holds its copy to KIT.json in its own
tests, with no brand checkout; never edit a copy: change brand and sync.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kleidos_brand import BRAND_ROOT, kicad  # noqa: E402

MANIFEST = "KIT.json"
SOURCE = "https://github.com/kleidos-dev/brand"
#: What a consumer's kit folder may hold besides the kit and its manifest.
IGNORED = frozenset({"__pycache__"})


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def commit(root: Path = BRAND_ROOT) -> str:
    """Return the commit the kit is taken at; refuse when a kit file differs from it."""
    files = [path.as_posix() for path in kicad.kit_files(root)]
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *files], cwd=root, capture_output=True, text=True, check=True).stdout
    if dirty.strip():
        raise SystemExit(f"commit the kit first: these files differ from HEAD:\n{dirty}")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def manifest(root: Path = BRAND_ROOT, at: str | None = None) -> dict:
    """Return the manifest of this checkout's kit."""
    style = kicad.load(root)
    return {
        "$comment": "Written by brand's tools/sync_kicad.py --copy. The Kleidos KiCad kit, byte copies of brand's kicad/ at the commit below;"
                    " never edit a file here: change brand and sync.",
        "kit": style["kit"],
        "source": SOURCE,
        "commit": at if at is not None else commit(root),
        "files": {path.name: sha256((root / path).read_bytes()) for path in kicad.kit_files(root)},
    }


def copy(target: Path, root: Path = BRAND_ROOT, at: str | None = None) -> list[str]:
    """Write the kit and its manifest into *target*; remove what the kit no longer holds; return what was written.

    :param at: The commit to record; by default this checkout's HEAD, refused when a kit file differs from it.
    """
    data = manifest(root, at)
    target.mkdir(parents=True, exist_ok=True)
    for path in kicad.kit_files(root):
        (target / path.name).write_bytes((root / path).read_bytes())
    (target / MANIFEST).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for extra in sorted(target.iterdir()):
        if extra.is_file() and extra.name not in data["files"] and extra.name != MANIFEST:
            extra.unlink()
    return [*data["files"], MANIFEST]


def findings(target: Path, root: Path | None = BRAND_ROOT) -> list[str]:
    """Return what is wrong with a consumer's kit folder: a file not its manifest's, or (with *root*) not this checkout's kit."""
    found = []
    path = target / MANIFEST
    if not path.is_file():
        return [f"{target}: no {MANIFEST}; run brand's tools/sync_kicad.py --copy"]
    data = json.loads(path.read_text(encoding="utf-8"))
    for name, digest in data["files"].items():
        held = target / name
        if not held.is_file():
            found.append(f"{held}: missing")
        elif sha256(held.read_bytes()) != digest:
            found.append(f"{held}: not the bytes {MANIFEST} records; never edit a copy, sync it again")
    for extra in sorted(target.iterdir()):
        if extra.name not in data["files"] and extra.name != MANIFEST and extra.name not in IGNORED:
            found.append(f"{extra}: not part of the kit")
    if root is not None:
        ours = {item.name: sha256((root / item).read_bytes()) for item in kicad.kit_files(root)}
        if data["files"] != ours or data.get("kit") != kicad.load(root)["kit"]:
            found.append(f"{target}: not this checkout's kit; run tools/sync_kicad.py --copy {target}")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--copy", type=Path, metavar="DIR", help="write the kit into DIR")
    group.add_argument("--check", type=Path, metavar="DIR", help="compare DIR with this checkout's kit")
    args = parser.parse_args(argv)
    if args.copy:
        written = copy(args.copy.resolve())
        print(f"wrote {len(written)} files to {args.copy}")
        return 0
    found = findings(args.check.resolve())
    for line in found:
        print(line)
    if found:
        return 1
    print(f"{args.check}: this checkout's kit, byte for byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
