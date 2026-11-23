#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the embedded metadata of every published picture and SVG, alone (tools/check.py runs it too).

    tools/check_metadata.py              every media file of the tree
    tools/check_metadata.py PATH ...     these files only
    tools/check_metadata.py --json       the findings as [{"path", "rule", "message"}]

Each finding reads ``path: Mxxx: message``:

- M001 a field the file's profile needs is missing
- M002 a field differs from what the file's record gives
- M003 the record's license or holders differ from what REUSE says for the path
- M004 a value holds a local path, a private host, a machine's time, a tool's name, an
       e-mail address or a pattern of the private deny-list
- M005 a container, chunk or segment outside the profile
- M006 a format or order error (chunk or segment order, a malformed file)
- M007 two slots of one file disagree (IIM and XMP)
- M008 a media file with neither a record nor a reason in METADATA_EXEMPT
- M009 the wrong profile for the picture's size (short under 64 px, full from 64)
- M010 a vendor miswritten, or a Spanish value that says "vault" or "bóveda"
- M011 an SVG's metadata outside REUSE-IgnoreStart and REUSE-IgnoreEnd
- M012 a raster without its IPTC digital source type, or with one outside the profile

Exit status: 0 clean, 1 findings, 2 a usage or internal error. The private deny-list comes
from tools/deny-local.txt (one pattern per line, never committed) or KLEIDOS_DENY_EXTRA; in
CI a missing list is a finding, unless KLEIDOS_DENY_OPTIONAL=1 says the secret cannot be read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check  # noqa: E402
from kleidos_brand import BRAND_ROOT  # noqa: E402

FINDING = re.compile(r"^(?P<path>[^:]+): (?P<rule>M\d{3}): (?P<message>.*)$")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "paths", nargs="*", help="files to check, relative to the repository (default: all)"
    )
    parser.add_argument("--json", action="store_true", help="print the findings as JSON")
    parser.add_argument(
        "--root", type=Path, default=BRAND_ROOT, help="the tree to check (default: this repository)"
    )
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        only = {Path(path).as_posix() for path in args.paths} or None
        found = check.metadata_findings(root, only=only)
    except Exception as error:  # noqa: BLE001 - any failure here is the checker's, reported as such
        print(f"check_metadata: internal error: {error}", file=sys.stderr)
        return 2
    if args.json:
        rows = []
        for line in found:
            match = FINDING.match(line)
            rows.append(match.groupdict() if match else {"path": "", "rule": "", "message": line})
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for line in found:
            print(line)
        print(
            f"\n{len(found)} finding(s)."
            if found
            else "metadata: every published picture and SVG carries its record."
        )
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
