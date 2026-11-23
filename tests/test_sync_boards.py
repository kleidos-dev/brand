# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The boards sync script, against a small checkout shaped like the boards repository."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import sync_from_boards as sync

from kleidos_brand import boards


def git(folder: Path, *arguments: str) -> str:
    identity = ("-c", "user.name=Someone", "-c", "user.email=someone", "-c", "commit.gpgsign=false")
    return subprocess.run(
        ["git", *identity, *arguments], cwd=folder, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """Return a checkout that holds every front, committed."""
    folder = tmp_path / "boards checkout"
    for slug in sync.BOARDS:
        path = folder / sync.source(slug)
        path.parent.mkdir(parents=True)
        path.write_text(f"<svg>{slug}</svg>\n", encoding="utf-8")
    git(folder.parent, "init", "--quiet", str(folder))
    git(folder, "add", ".")
    git(folder, "commit", "--quiet", "-m", "Fronts")
    return folder


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return an empty brand tree, which the command writes into."""
    folder = tmp_path / "brand"
    folder.mkdir()
    for function in (sync.check, sync.copy):
        monkeypatch.setattr(function, "__defaults__", (folder,))
    return folder


def test_a_copy_is_the_checkout_s_bytes_at_its_commit(checkout: Path, root: Path) -> None:
    assert sync.main(["--check", str(checkout)]) == 1, "nothing is copied yet"
    assert sync.main(["--copy", str(checkout)]) == 0
    assert sync.main(["--check", str(checkout)]) == 0
    manifest = json.loads((root / boards.MANIFEST).read_text(encoding="utf-8"))
    assert manifest["commit"] == git(checkout, "rev-parse", "HEAD")
    assert list(manifest["boards"]) == list(sync.BOARDS)
    for slug in sync.BOARDS:
        copied = (root / boards.front_path(slug)).read_bytes()
        assert copied == (checkout / sync.source(slug)).read_bytes()


def test_a_front_missing_from_the_checkout_is_reported(
    checkout: Path, root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (checkout / sync.source("tdeck-plus")).unlink()
    assert sync.main(["--check", str(checkout)]) == 1
    assert "tdeck-plus/svg/front.svg: not in the checkout" in capsys.readouterr().out
    assert root.is_dir()


def test_uncommitted_fronts_are_not_copied(checkout: Path, root: Path) -> None:
    (checkout / sync.source("coreink")).write_text("<svg/>\n", encoding="utf-8")
    assert sync.main(["--copy", str(checkout)]) == 1
    assert not (root / boards.MANIFEST).exists()


@pytest.mark.usefixtures("root")
def test_git_is_given_no_argument_taken_from_the_command_line(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[list[str], Path]] = []
    real = subprocess.run

    def run(command: list[str], **options: Any) -> Any:
        calls.append((command, options["cwd"]))
        return real(command, **options)

    monkeypatch.setattr(subprocess, "run", run)
    assert sync.main(["--copy", str(checkout)]) == 0
    fronts = [sync.source(slug) for slug in sync.BOARDS]
    assert calls == [
        (["git", "status", "--porcelain", "--", *fronts], checkout.resolve()),
        (["git", "rev-parse", "HEAD"], checkout.resolve()),
    ]


@pytest.mark.usefixtures("root")
@pytest.mark.parametrize("mode", ["--check", "--copy"])
@pytest.mark.parametrize(
    ("place", "why"),
    [
        ("missing", "is not there"),
        ("sticks3", "is not the top of a git checkout"),
        ("sticks3/svg/front.svg", "is not"),
    ],
)
def test_a_path_that_is_not_the_top_of_a_checkout_is_refused(
    checkout: Path, mode: str, place: str, why: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as stopped:
        sync.main([mode, str(checkout / place)])
    assert stopped.value.code == 2
    assert why in capsys.readouterr().err


def test_a_front_that_leads_out_of_the_checkout_is_refused(
    checkout: Path, root: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.svg"
    outside.write_text("<svg>not a board</svg>\n", encoding="utf-8")
    front = checkout / sync.source("cardputer")
    front.unlink()
    front.symlink_to(outside)
    git(checkout, "add", ".")
    git(checkout, "commit", "--quiet", "-m", "A link")
    for mode in ("--check", "--copy"):
        with pytest.raises(SystemExit, match="cardputer/svg/front.svg: leads out of the checkout"):
            sync.main([mode, str(checkout)])
    assert list(root.iterdir()) == []
