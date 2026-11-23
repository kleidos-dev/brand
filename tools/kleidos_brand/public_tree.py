# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""What must never be in a tree that will be published, and what every file's license must be.

The same rules hold in ``brand`` and in ``social``, which calls this module
with its own lists:

- nothing private: no home-directory path, private address, hardware
  address, serial port of one machine, local host name, token or key, and no
  e-mail address but the project's contact, its supplier and ``example.com``;
- licenses are declared, not mentioned: every SPDX tag, every identifier of
  ``REUSE.toml`` and every text under ``LICENSES/`` is one of the allowed
  ones, all approved by the OSI. Prose may name any license (a notice has to
  say what a neighboring repository uses); a declaration may not;
- fonts: only the pinned files, byte for byte; no other font container and no
  font inside an SVG, because a subset or a converted copy is a Modified
  Version under the OFL;
- pictures: a raster or a PDF only where the repository says its own go;
- no drawing of a board outside the folders a repository names for the
  copies it takes from ``boards`` (MIT), and no registered-trademark sign
  beside a name that is not registered (a board's own print, in those
  folders, keeps its maker's).
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
import subprocess
import tomllib
from pathlib import Path

from . import PROJECT_CONTACT, PROJECT_SUPPLIER, meta

TEXT_SUFFIXES = frozenset(
    {
        ".md",
        ".json",
        ".py",
        ".yml",
        ".yaml",
        ".toml",
        ".txt",
        ".svg",
        ".css",
        ".h",
        ".cfg",
        ".ini",
        "",
    }
)
FONT_SUFFIXES = frozenset({".ttf", ".otf", ".woff", ".woff2", ".ttc", ".eot"})
PICTURE_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".avif",
        ".bmp",
        ".tif",
        ".tiff",
        ".ico",
        ".pdf",
        ".eps",
        ".ai",
        ".psd",
    }
)
ALLOWED_EMAIL_DOMAINS = ("example.com",)

IPV4 = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3})(?![\w.]*\d)")
DOC_NETS = [
    ipaddress.ip_network(net)
    for net in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "127.0.0.0/8", "0.0.0.0/32")
]
MAC = re.compile(r"(?<![0-9A-Fa-f:-])([0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5})(?![0-9A-Fa-f:-])")
EMAIL = re.compile(
    r"(?<![\w.%+-])([A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}))\b"
)
#: A pattern whose ``shown`` group is not the whole match shows that group in its finding.
PRIVATE = [
    (
        "a home-directory path",
        re.compile(
            r"/Users/[A-Za-z][\w.-]*|/home/(?!runner\b)[a-z][\w.-]*|[A-Za-z]:\\\\?Users\\\\?[A-Za-z]"
        ),
    ),
    (
        "a machine's serial port",
        re.compile(
            r"/dev/(?:cu|tty)\.[A-Za-z][\w.-]*\d|/dev/tty(?:USB|ACM)\d|/dev/serial/by-(?:id|path)/[A-Za-z0-9][^\s`'\")]*"
        ),
    ),
    (
        "a local host name",
        re.compile(
            r"(?<![\w-])(?:(?![a-z0-9])\w*+-)*+"
            r"(?P<shown>[a-z0-9][\w-]*+\.(?:local|lan|home\.arpa))(?![\w.-])",
            re.I,
        ),
    ),
    (
        "the name of a private setting",
        re.compile(r"\bKLEIDOS_(?=[A-Z0-9_]*(?:MAC|IP|HOST|PORT|TOKEN|KEY|PASS))[A-Z0-9_]++\b"),
    ),
    (
        "a token or a key",
        re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}"
            r"|glpat-[A-Za-z0-9_-]{20,}|sk-(?:ant-)?[A-Za-z0-9_-]{32,}|AKIA[0-9A-Z]{16})\b"
            r"|-----BEGIN "
            r"(?:[A-Z]+ )*PRIVATE KEY-----"
        ),
    ),
]
# REUSE-IgnoreStart
SPDX_TAG = re.compile(r"SPDX-License-Identifier:[ \t]*([^\n\r]*)")
# REUSE-IgnoreEnd
#: The licensing header a Markdown file opens with: an HTML comment of SPDX lines.
LICENSING_HEADER = re.compile(r"\A<!--\n(?:SPDX-[^\n]*\n)+-->\n")


def prose(path: Path) -> str:
    """Return a Markdown text as its readers quote it: without its licensing header, stripped."""
    return LICENSING_HEADER.sub("", path.read_text(encoding="utf-8"), count=1).strip()


BOARD_MARKERS = (re.compile(r"""(?:id|class)=["'][^"']*\b(?:screen-active|hotspots)\b"""),)
SVG_FONT = re.compile(r"@font-face|data:font|data:application/(?:x-)?font|<font\b|<font-face\b")
REGISTERED = chr(0xAE)


def tracked(root: Path) -> list[Path]:
    """Return every file git tracks or would track at *root*, relative to it."""
    try:
        listed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"],
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
        files = [Path(name) for name in listed.split("\0") if name]
    except OSError, subprocess.CalledProcessError:
        files = [
            path.relative_to(root)
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.parts
        ]
    return sorted(
        path for path in files if (root / path).is_file() and not (root / path).is_symlink()
    )


def private_findings(
    name: str,
    text: str,
    allowed_emails: frozenset[str] = frozenset({PROJECT_CONTACT, PROJECT_SUPPLIER}),
) -> list[str]:
    """Return the private data in one file's text."""
    found = [
        f"{name}: holds {what} ({match[match.lastgroup or 0][:60]})"
        for what, pattern in PRIVATE
        for match in pattern.finditer(text)
    ]
    for match in IPV4.finditer(text):
        try:
            address = ipaddress.ip_address(match.group(1))
        except ValueError:
            continue
        if address.is_private and not any(address in net for net in DOC_NETS):
            found.append(f"{name}: holds a private network address ({match.group(1)})")
    found.extend(
        f"{name}: holds a hardware address ({match.group(1)})" for match in MAC.finditer(text)
    )
    for match in EMAIL.finditer(text):
        mailbox, domain = match.group(1), match.group(2).lower()
        if mailbox.lower() not in allowed_emails and domain not in ALLOWED_EMAIL_DOMAINS:
            found.append(
                f"{name}: holds an e-mail address that is not the project's contact ({mailbox})"
            )
    return found


#: The operators of an SPDX expression, which name no license.
SPDX_OPERATORS = frozenset({"AND", "OR", "WITH"})


def license_ids(expression: str) -> list[str]:
    """Return the license (and exception) identifiers of an SPDX expression, in order."""
    words = expression.replace("(", " ").replace(")", " ").split()
    return [word for word in words if word not in SPDX_OPERATORS]


def license_findings(root: Path, files: list[Path], allowed: frozenset[str]) -> list[str]:
    """Return every license declaration that is not one of *allowed*.

    A declaration is an SPDX tag in a file (outside a REUSE ignore block), an
    identifier in ``REUSE.toml`` or a text under ``LICENSES/``.
    """
    found: list[str] = []
    texts = (
        {path.stem for path in (root / "LICENSES").glob("*.txt")}
        if (root / "LICENSES").is_dir()
        else set()
    )
    found.extend(
        f"LICENSES/{extra}.txt: only {', '.join(sorted(allowed))} belong in LICENSES/"
        for extra in sorted(texts - allowed)
    )
    found.extend(f"LICENSES/{missing}.txt: missing" for missing in sorted(allowed - texts))
    reuse = root / "REUSE.toml"
    if reuse.is_file():
        for annotation in tomllib.loads(reuse.read_text(encoding="utf-8")).get("annotations", []):
            identifier = annotation.get("SPDX-License-Identifier", "")
            found.extend(
                f"REUSE.toml: declares {part.strip()!r} for {annotation.get('path')}; only "
                f"{', '.join(sorted(allowed))} are declared here"
                for part in license_ids(identifier)
                if part not in allowed
            )
    else:
        found.append("REUSE.toml: missing")
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES or path.parts[0] == "LICENSES":
            continue
        try:
            text = (root / path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in SPDX_TAG.finditer(meta.without_ignore_blocks(text)):
            expression = match.group(1).strip().rstrip("*/ ->").strip()
            parts = meta.spdx_ids(expression)
            if not parts or any(part not in allowed for part in parts):
                found.append(
                    f"{path}: its license tag reads {expression!r}; a tag stands alone on its line "
                    f"and names one of {', '.join(sorted(allowed))}"
                )
    return found


def font_findings(root: Path, files: list[Path], pins: dict[str, str]) -> list[str]:
    """Return every font that is not a pinned file with its pinned bytes, and every font inside an
    SVG.

    :param pins: Each pinned file's path, relative to *root*, and its SHA-256.
    """
    found = []
    for path in files:
        suffix = path.suffix.lower()
        if suffix in FONT_SUFFIXES:
            pin = pins.get(path.as_posix())
            if pin is None:
                found.append(
                    f"{path}: a font file that is not pinned; a subset, an instance or a converted "
                    "copy is a Modified Version"
                )
            elif hashlib.sha256((root / path).read_bytes()).hexdigest() != pin:
                found.append(f"{path}: its bytes are not the pinned upstream file's")
        elif suffix == ".svg" and SVG_FONT.search(
            (root / path).read_text(encoding="utf-8", errors="replace")
        ):
            found.append(
                f"{path}: holds a font or a font-face rule; an SVG here holds outlines, never a "
                "font"
            )
    for name, pin in pins.items():
        if not (root / name).is_file():
            found.append(f"{name}: pinned and missing")
        elif hashlib.sha256((root / name).read_bytes()).hexdigest() != pin:
            found.append(f"{name}: its bytes are not its pin's")
    return sorted(set(found))


def findings(
    root: Path,
    files: list[Path],
    picture_dirs: tuple[str, ...],
    allowed_emails: frozenset[str] = frozenset({PROJECT_CONTACT, PROJECT_SUPPLIER}),
    skip_private: tuple[str, ...] = (),
    board_dirs: tuple[str, ...] = (),
) -> list[str]:
    """Return what in the tree at *root* must not be published.

    :param picture_dirs: The folders a raster picture or a PDF may be in.
    :param board_dirs: The folders that hold byte copies of the boards
        repository's drawings, which keep their markers and their print.
    :param skip_private: Files whose text is not scanned for private data
        (the tests that plant it, the gate copied from another repository).
    """
    found = []
    for path in files:
        name = path.as_posix()
        suffix = path.suffix.lower()
        if suffix in PICTURE_SUFFIXES and not any(
            name.startswith(f"{folder}/") for folder in picture_dirs
        ):
            found.append(f"{name}: a picture or a PDF outside {', '.join(picture_dirs)}")
        if suffix not in TEXT_SUFFIXES or path.parts[0] == "LICENSES" or name == "LICENSE":
            continue
        try:
            text = (root / path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            found.append(f"{name}: not UTF-8 text")
            continue
        in_boards = any(name.startswith(f"{folder}/") for folder in board_dirs)
        if name not in skip_private:
            found += private_findings(name, text, allowed_emails)
            if REGISTERED in text and not in_boards:
                found.append(
                    f"{name}: prints the registered-trademark sign; Kleidos is not a registered "
                    "trademark"
                )
        if suffix == ".svg":
            if any(marker.search(text) for marker in BOARD_MARKERS) and not in_boards:
                where = f" (copies go in {', '.join(board_dirs)})" if board_dirs else ""
                found.append(
                    f"{name}: carries a board drawing's markers; board drawings are the boards "
                    f"repository's{where}"
                )
            if re.search(r"<image\b|data:image", text):
                found.append(f"{name}: embeds a picture")
    return found


PIN = re.compile(r"`([^`]+\.(?:ttf|otf|txt))`\s+`([0-9a-f]{64})`")


def font_pins(root: Path, versions: str = "fonts/VERSIONS.md") -> dict[str, str]:
    """Return the pinned files of ``fonts/VERSIONS.md``: each path, relative to *root*, and its
    SHA-256."""
    folder = Path(versions).parent
    return {
        (folder / name).as_posix(): digest
        for name, digest in PIN.findall((root / versions).read_text(encoding="utf-8"))
    }
