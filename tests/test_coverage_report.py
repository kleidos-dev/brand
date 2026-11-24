# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The coverage report SonarQube Cloud reads names every file once, from the repository root.

Brand and its social pack both have a ``check.py`` and a ``check_metadata.py``. A report that
names a file relative to its code root (``check.py`` under ``tools`` and under ``social/tools``)
keeps one of the two in the XML and leaves the other's name ambiguous to the scanner, which drops
both files' coverage. The test measures a small tree shaped like this one under the repository's
own ``.coveragerc``, as CI's two pytest runs do, and reads the report it writes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: The tree's code, one file per root and the two names both trees hold; the files no run executes
#: are reported too, at 0 %.
CODE = {
    "tools/check.py": "def run():\n    return 1\n",
    "tools/check_metadata.py": "def run():\n    return 2\n",
    "tools/kleidos_brand/__init__.py": "",
    "tools/kleidos_brand/tokens.py": "VALUE = 3\n",
    "kicad/kleidos_kicad.py": "VALUE = 4\n",
    "social/tools/check.py": "def run():\n    return 5\n",
    "social/tools/check_metadata.py": "def run():\n    return 6\n",
}
#: The two runs: brand's tests, then the pack's, appended to the same data, as CI runs them.
RUNS = {
    "tests/probe.py": "import runpy\nrunpy.run_path('tools/check.py')['run']()\n",
    "social/tests/probe.py": "import runpy\nrunpy.run_path('social/tools/check.py')['run']()\n",
}


def _coverage(tree: Path, *args: str) -> None:
    # Without the variables a measured parent hands down, so the run is the one asked for.
    env = {key: value for key, value in os.environ.items() if not key.startswith("COV")}
    subprocess.run([sys.executable, "-I", "-m", "coverage", *args], cwd=tree, env=env, check=True)


def test_the_report_names_every_file_once_from_the_root(tmp_path: Path) -> None:
    tree = tmp_path / "brand"
    for name, text in {**CODE, **RUNS}.items():
        (tree / name).parent.mkdir(parents=True, exist_ok=True)
        (tree / name).write_text(text, encoding="utf-8")
    shutil.copy(ROOT / ".coveragerc", tree / ".coveragerc")

    _coverage(tree, "run", "tests/probe.py")
    _coverage(tree, "run", "--append", "social/tests/probe.py")
    _coverage(tree, "xml", "-o", "coverage.xml")

    report = ET.parse(tree / "coverage.xml").getroot()  # noqa: S314  the report coverage just wrote
    classes = [element.attrib for element in report.iter("class")]
    assert sorted(named["filename"] for named in classes) == sorted(CODE)
    rates = {named["filename"]: named["line-rate"] for named in classes}
    assert rates["tools/check.py"] == rates["social/tools/check.py"] == "1"
    assert rates["tools/check_metadata.py"] == rates["social/tools/check_metadata.py"] == "0"
