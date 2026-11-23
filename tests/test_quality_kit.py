# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The Kleidos quality kit's copies and blocks are the bytes SOURCE.json records.

A byte copy of kleidos-dev/.github quality/templates/test_quality_kit.py,
written by that repository's sync.py --write --test-dir <dir>: never edit it
here. It makes this repository's own test suite fail on kit drift, as the
commit-check copies' digest test does:

- the offline check: every copy and managed block is the bytes
  .github/quality/SOURCE.json records, and the configs keep the kit's rules
  (check_quality.py, the same check the pre-commit hook runs);
- with kleidos-dev/.github checked out beside this repository (or named by
  KLEIDOS_QUALITY_KIT), the recorded commit must also hold those bytes, so a
  copy cannot drift from the commit it names.

Runs under pytest or unittest; needs PyYAML, which the checker reads with.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


def _root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".github" / "quality" / "SOURCE.json").is_file():
            return parent
    raise RuntimeError("no .github/quality/SOURCE.json above this test")


ROOT = _root()
CHECKER = ROOT / ".github" / "quality" / "check_quality.py"


def _check(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--repo", str(ROOT), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


class QualityKitTest(unittest.TestCase):
    def test_the_kit_copies_and_rules_hold(self) -> None:
        result = _check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_the_recorded_commit_holds_the_same_bytes(self) -> None:
        named = os.environ.get("KLEIDOS_QUALITY_KIT")
        central = Path(named) if named else ROOT.parent / ".github"
        if not (central / ".git").exists():
            self.skipTest("kleidos-dev/.github is not checked out beside this repository")
        result = _check("--kit-git", str(central))
        if result.returncode == 3:
            self.skipTest(result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
