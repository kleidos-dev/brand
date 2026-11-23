# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The boards sync script, against a small checkout shaped like the boards repository."""

from __future__ import annotations

import json
import shutil
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
    git(checkout, "rm", "--quiet", sync.source("tdeck-plus"))
    git(checkout, "commit", "--quiet", "-m", "One front fewer")
    assert sync.main(["--check", str(checkout)]) == 1
    missing = "tdeck-plus/svg/front.svg: not in the checkout's commit"
    assert missing in capsys.readouterr().out
    with pytest.raises(SystemExit, match=missing):
        sync.main(["--copy", str(checkout)])
    assert list(root.iterdir()) == []


def test_a_copy_is_what_the_commit_holds_not_what_the_checkout_writes(
    checkout: Path, root: Path
) -> None:
    """A checkout may write other bytes than the commit's with nothing to commit."""
    (checkout / ".gitattributes").write_text("*.svg text eol=crlf\n", encoding="utf-8")
    git(checkout, "add", ".")
    git(checkout, "commit", "--quiet", "-m", "Line ends")
    for slug in sync.BOARDS:
        (checkout / sync.source(slug)).unlink()
    git(checkout, "checkout", "--", ".")
    assert (checkout / sync.source("cardputer")).read_bytes() == b"<svg>cardputer</svg>\r\n"
    assert sync.main(["--copy", str(checkout)]) == 0
    assert (root / boards.front_path("cardputer")).read_bytes() == b"<svg>cardputer</svg>\n"
    assert sync.main(["--check", str(checkout)]) == 0


def test_uncommitted_fronts_are_not_copied(checkout: Path, root: Path) -> None:
    (checkout / sync.source("coreink")).write_text("<svg/>\n", encoding="utf-8")
    assert sync.main(["--copy", str(checkout)]) == 1
    assert not (root / boards.MANIFEST).exists()


@pytest.mark.usefixtures("root")
def test_git_is_given_nothing_but_fixed_words_the_fronts_and_the_commit_s_own_ids(
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
    commit = git(checkout, "rev-parse", "HEAD")
    expected = [
        ["git", "rev-parse", "--is-inside-work-tree", "--show-prefix", "HEAD"],
        ["git", "rev-parse", "HEAD"],
    ]
    for front in fronts:
        blob = git(checkout, "rev-parse", f"HEAD:{front}")
        expected.append(["git", "ls-tree", commit, "--", front])
        expected.append(["git", "cat-file", "blob", blob])
    expected.append(["git", "status", "--porcelain", "--", *fronts])
    made = [command for command, _ in calls][: len(expected)]
    assert made == expected
    assert {folder for _, folder in calls} == {checkout.resolve()}


@pytest.mark.usefixtures("root")
@pytest.mark.parametrize("mode", ["--check", "--copy"])
@pytest.mark.parametrize(
    ("place", "why"),
    [
        ("missing", "is not there"),
        ("sticks3", "is not the top of a git checkout"),
        ("sticks3/svg/front.svg", "is not the top of a git checkout"),
        (".git", "is not the top of a git checkout"),
    ],
)
def test_a_path_that_is_not_the_top_of_a_checkout_is_refused(
    checkout: Path, mode: str, place: str, why: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as stopped:
        sync.main([mode, str(checkout / place)])
    assert stopped.value.code == 2
    assert why in capsys.readouterr().err


@pytest.mark.usefixtures("root")
@pytest.mark.parametrize("mode", ["--check", "--copy"])
def test_a_git_folder_of_its_own_does_not_make_a_checkout(
    checkout: Path, mode: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """git walks up past a `.git` that holds no repository, to the one around it."""
    inner = checkout / "inner"
    for slug in sync.BOARDS:
        path = inner / sync.source(slug)
        path.parent.mkdir(parents=True)
        path.write_text("<svg/>\n", encoding="utf-8")
    (inner / ".git").mkdir()
    with pytest.raises(SystemExit) as stopped:
        sync.main([mode, str(inner)])
    assert stopped.value.code == 2
    assert "is not the top of a git checkout" in capsys.readouterr().err


@pytest.mark.usefixtures("root")
@pytest.mark.parametrize("mode", ["--check", "--copy"])
def test_a_repository_with_no_commit_or_no_files_is_refused(
    tmp_path: Path, mode: str, capsys: pytest.CaptureFixture[str]
) -> None:
    git(tmp_path, "init", "--quiet", "empty")
    git(tmp_path, "init", "--quiet", "--bare", "bare")
    for name in ("empty", "bare"):
        with pytest.raises(SystemExit) as stopped:
            sync.main([mode, str(tmp_path / name)])
        assert stopped.value.code == 2
        assert "is not the top of a git checkout" in capsys.readouterr().err


@pytest.mark.parametrize("mode", ["--check", "--copy"])
@pytest.mark.parametrize("target", ["outside.svg", "../../.git/config", "../../sticks3/svg"])
def test_a_front_that_is_a_link_is_refused(
    checkout: Path, root: Path, tmp_path: Path, mode: str, target: str
) -> None:
    (tmp_path / "outside.svg").write_text("<svg>not a board</svg>\n", encoding="utf-8")
    front = checkout / sync.source("cardputer")
    front.unlink()
    front.symlink_to(tmp_path / target if target == "outside.svg" else target)
    git(checkout, "add", ".")
    git(checkout, "commit", "--quiet", "-m", "A link")
    with pytest.raises(SystemExit, match="cardputer/svg/front.svg: is not a file in the checkout"):
        sync.main([mode, str(checkout)])
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("where", ["outside", "sticks3"])
def test_a_front_behind_a_linked_folder_is_not_in_the_commit(
    checkout: Path, root: Path, tmp_path: Path, where: str, capsys: pytest.CaptureFixture[str]
) -> None:
    outside = tmp_path / "outside/svg"
    outside.mkdir(parents=True)
    (outside / "front.svg").write_text("<svg>not a board</svg>\n", encoding="utf-8")
    shutil.rmtree(checkout / "cardputer")
    target = tmp_path / where if where == "outside" else Path(where)
    (checkout / "cardputer").symlink_to(target)
    git(checkout, "add", ".")
    git(checkout, "commit", "--quiet", "-m", "A linked folder")
    assert sync.main(["--check", str(checkout)]) == 1
    missing = "cardputer/svg/front.svg: not in the checkout's commit"
    assert missing in capsys.readouterr().out
    with pytest.raises(SystemExit, match=missing):
        sync.main(["--copy", str(checkout)])
    assert list(root.iterdir()) == []
