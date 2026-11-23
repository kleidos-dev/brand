# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The tokens: what is generated from them round-trips, and the contrast figures are right."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kleidos_brand import palette, tokens

ROOT = Path(__file__).resolve().parents[1]


def independent_contrast(first: str, second: str) -> float:
    """WCAG 2 contrast, written out again from the definition."""

    def luminance(color: str) -> float:
        parts = []
        for at in (1, 3, 5):
            share = int(color[at : at + 2], 16) / 255
            parts.append(share / 12.92 if share <= 0.04045 else ((share + 0.055) / 1.055) ** 2.4)
        return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]

    high, low = max(luminance(first), luminance(second)), min(luminance(first), luminance(second))
    return (high + 0.05) / (low + 0.05)


def test_generated_files_round_trip() -> None:
    loaded = tokens.load(ROOT)
    assert (ROOT / tokens.FLAT_JSON).read_text(encoding="utf-8") == tokens.flat_json(loaded)
    assert (ROOT / tokens.TOKENS_CSS).read_text(encoding="utf-8") == tokens.css(loaded)
    flat = json.loads((ROOT / tokens.FLAT_JSON).read_text(encoding="utf-8"))
    assert flat["brand.signal"] == "#00d2ff" and flat["brand.select"] == "#0f3460"


def test_the_hairline_is_computed_not_stored() -> None:
    loaded = tokens.load(ROOT)
    assert "$value" not in loaded["social"]["rule"]
    assert tokens.resolve(loaded)["social.rule"] == "#2e3033"
    assert tokens.over("#eceef1", "#0a0c0f", 0.16) == "#2e3033"


def test_aliases_resolve_and_loops_are_refused() -> None:
    values = tokens.resolve(tokens.load(ROOT))
    assert values["social.ground"] == values["web.dark.stage"] == "#0a0c0f"
    assert values["social.signal"] == values["brand.signal"]
    with pytest.raises(ValueError, match="loop"):
        tokens.resolve(
            {"a": {"$value": "{b}", "$type": "color"}, "b": {"$value": "{a}", "$type": "color"}}
        )


@pytest.mark.parametrize(
    ("color", "ground", "expected"),
    [
        ("#00d2ff", "#0a0c0f", 10.88),
        ("#00d2ff", "#08090c", 11.06),
        ("#00d2ff", "#000000", 11.66),
        ("#00d2ff", "#0f3460", 6.94),
        ("#00d2ff", "#ffffff", 1.80),
        ("#0f3460", "#ffffff", 12.50),
        ("#0f3460", "#0a0c0f", 1.57),
        ("#eceef1", "#0a0c0f", 16.85),
        ("#9aa3ad", "#0a0c0f", 7.66),
        ("#00708c", "#f2f4f5", 5.15),
        ("#e0e0e0", "#000000", 15.91),
    ],
)
def test_contrast_matches_an_independent_computation(
    color: str, ground: str, expected: float
) -> None:
    assert round(tokens.contrast(color, ground), 2) == expected
    assert tokens.contrast(color, ground) == pytest.approx(
        independent_contrast(color, ground), abs=1e-9
    )


def test_the_colors_page_states_the_measured_figures() -> None:
    page = (ROOT / "colors/README.md").read_text(encoding="utf-8")
    values = tokens.resolve(tokens.load(ROOT))
    for color, ground, _ in palette.PAIRS:
        assert f"{independent_contrast(values[color], values[ground]):.2f}:1" in page


def test_the_stylesheet_carries_the_sites_own_names() -> None:
    sheet = tokens.css(tokens.load(ROOT))
    for name in (
        "--signal: #00d2ff;",
        "--ink-2: #9aa3ad;",
        "--stage: #0a0c0f;",
        '--t-hero-fvs: "opsz" 72;',
        "--device-bg-base: #000000;",
    ):
        assert name in sheet
    assert "--kl-" not in sheet


def test_rgb565_and_print_values() -> None:
    assert tokens.rgb565("#00d2ff") == "0x069F"
    assert tokens.cmyk("#00d2ff") == (100, 18, 0, 0)
    assert tokens.cmyk("#000000") == (0, 0, 0, 100)
