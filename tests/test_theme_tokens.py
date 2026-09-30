"""Theme tokens stay the source of truth for CSS and Plotly."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from prime_radiant.theme.css_tokens import APP_PATH, THEME_DIR, load_tokens, theme_stylesheet
from prime_radiant.theme.plotly_template import TEMPLATE_NAME, chart_theme, register_template

# Cool purple axis ink that used to tint chart chrome away from the hull.
_FORBIDDEN_COLOR = re.compile(
    r"168\s*,\s*158\s*,\s*210|#a89ed2|#b8a9e0|#c4b5fd|#8b7ec8|#9b8ec4",
    re.IGNORECASE,
)
_COLOR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(")
_PY_FILES = ("css_tokens.py", "plotly_template.py", "__init__.py")


def _rgb(color: str) -> tuple[int, int, int]:
    hex_match = re.fullmatch(r"#([0-9a-fA-F]{6})", color.strip())
    if hex_match:
        value = hex_match.group(1)
        return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    rgba = re.fullmatch(
        r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*[\d.]+\s*)?\)",
        color.strip(),
    )
    if not rgba:
        raise AssertionError(f"not a color: {color}")
    return tuple(int(channel) for channel in rgba.groups())  # type: ignore[return-value]


def _channel(value: int) -> float:
    channel = value / 255
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _luminance(color: str) -> float:
    red, green, blue = _rgb(color)
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def _contrast(foreground: str, background: str) -> float:
    lighter = max(_luminance(foreground), _luminance(background))
    darker = min(_luminance(foreground), _luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def test_hull_palette_is_unchanged() -> None:
    tokens = load_tokens()
    assert tokens["bg-deep"] == "#07060a"
    assert tokens["bg-deep-mid"] == "#100e14"
    assert tokens["bg-panel-solid"] == "#141218"
    assert tokens["accent"] == "#efe6d4"
    assert tokens["text-primary"] == "#efe6d4"
    assert tokens["accent-brass"] == "#c4a06a"
    assert tokens["accent-gold"] == "#c4a06a"
    assert tokens["accent-gold-soft"] == "#d4bc90"
    assert tokens["accent-steel"] == "#8fa0b0"
    assert tokens["accent-cyan"] == "#8fa0b0"
    assert tokens["accent-violet"] == "#8fa0b0"
    assert tokens["text-secondary"] == "#cfc6b8"
    assert tokens["text-muted"] == "#9a9084"
    assert tokens["text-faint"] == "#6a635c"
    assert tokens["signal-buy"] == "#b4c4c8"
    assert tokens["signal-trim"] == "#c4a06a"
    assert tokens["signal-strong-trim"] == "#c9a090"


def test_chart_alphas_use_palette_rgb() -> None:
    tokens = load_tokens()
    assert _rgb(tokens["chart-axis"]) == _rgb(tokens["accent-steel"])
    assert _rgb(tokens["chart-grid"]) == _rgb(tokens["accent-steel"])
    assert _rgb(tokens["chart-spike"]) == _rgb(tokens["accent-brass"])
    assert _rgb(tokens["chart-border"]) == _rgb(tokens["accent-brass"])
    assert _rgb(tokens["chart-zeroline"]) == _rgb(tokens["text-primary"])
    assert _rgb(tokens["bg-plot"]) == _rgb(tokens["bg-deep-mid"])
    assert _rgb(tokens["bg-plot-paper"]) == _rgb(tokens["bg-deep"])
    assert _rgb(tokens["bg-overlay"]) == _rgb(tokens["bg-deep"])
    assert _rgb(tokens["chart-hover-bg"]) == _rgb(tokens["bg-panel-solid"])
    assert _rgb(tokens["glass-sheen"]) == _rgb(tokens["accent"])
    assert tokens["chart-tick"] == tokens["text-secondary"]
    assert tokens["chart-up"] == tokens["signal-buy"]
    assert tokens["chart-down"] == tokens["signal-strong-trim"]


def test_ink_ramp_and_contrast() -> None:
    tokens = load_tokens()
    levels = ["text-faint", "text-muted", "text-secondary", "text-primary"]
    luminance = [_luminance(tokens[name]) for name in levels]
    assert luminance == sorted(luminance)
    assert _contrast(tokens["text-primary"], tokens["bg-deep"]) >= 7
    assert _contrast(tokens["text-secondary"], tokens["bg-deep"]) >= 7
    assert _contrast(tokens["accent-brass"], tokens["bg-deep"]) >= 4.5
    assert _contrast(tokens["text-muted"], tokens["bg-deep"]) >= 4.5


def test_no_lavender_literals_in_theme() -> None:
    for path in THEME_DIR.iterdir():
        if path.suffix not in {".css", ".py"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert _FORBIDDEN_COLOR.search(text) is None, path.name


def test_color_literals_live_only_in_tokens_css() -> None:
    app = APP_PATH.read_text(encoding="utf-8")
    assert _COLOR_LITERAL.search(app) is None
    for name in _PY_FILES:
        text = (THEME_DIR / name).read_text(encoding="utf-8")
        assert _COLOR_LITERAL.search(text) is None, name


def test_chart_theme_reads_tokens() -> None:
    tokens = load_tokens()
    theme = chart_theme()
    layout = theme["layout"]
    assert layout["paper_bgcolor"] == tokens["bg-plot-paper"]
    assert layout["plot_bgcolor"] == tokens["bg-plot"]
    assert layout["font"]["color"] == tokens["text-primary"]
    assert layout["font"]["family"] == tokens["font-ui"]
    assert layout["colorway"] == [tokens[f"series-{index}"] for index in range(1, 9)]
    for axis_name in ("xaxis", "yaxis"):
        axis = layout[axis_name]
        assert axis["gridcolor"] == tokens["chart-grid"]
        assert axis["linecolor"] == tokens["chart-axis"]
        assert axis["zerolinecolor"] == tokens["chart-zeroline"]
        assert axis["tickfont"]["color"] == tokens["chart-tick"]
        assert axis["spikecolor"] == tokens["chart-spike"]
    assert layout["hoverlabel"]["bgcolor"] == tokens["chart-hover-bg"]
    assert layout["hoverlabel"]["bordercolor"] == tokens["chart-hover-border"]
    assert layout["hoverlabel"]["font"]["color"] == tokens["text-primary"]
    assert layout["legend"]["bordercolor"] == tokens["chart-border"]
    assert layout["modebar"]["color"] == tokens["accent-steel"]
    assert layout["modebar"]["activecolor"] == tokens["accent-brass"]
    candle = theme["data"]["candlestick"][0]
    assert candle["increasing"]["line"]["color"] == tokens["chart-up"]
    assert candle["decreasing"]["line"]["color"] == tokens["chart-down"]
    serialized = repr(theme)
    assert "168, 158, 210" not in serialized
    assert "168,158,210" not in serialized


def test_stylesheet_inlines_tokens() -> None:
    sheet = theme_stylesheet()
    assert sheet.count(":root") == 1
    assert "@import" not in sheet
    assert "--accent-brass:" in sheet
    assert ".pr-panel" in sheet
    assert _COLOR_LITERAL.search(sheet.split(":root", 1)[1].split("}", 1)[1]) is None


def test_duplicate_token_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "tokens.css"
    path.write_text(":root { --a: #fff; --a: #000; }", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_tokens(path)


def test_token_cycle_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "tokens.css"
    path.write_text(":root { --a: var(--b); --b: var(--a); }", encoding="utf-8")
    with pytest.raises(ValueError, match="cycle"):
        load_tokens(path)


def test_plotly_template_smoke() -> None:
    import plotly.graph_objects as go
    import plotly.io as pio

    previous = pio.templates.default
    try:
        assert register_template() == TEMPLATE_NAME
        fig = go.Figure(go.Scatter(y=[1, 3, 2]))
        tokens = load_tokens()
        assert fig.layout.paper_bgcolor == tokens["bg-plot-paper"]
        assert fig.layout.plot_bgcolor == tokens["bg-plot"]
        assert fig.layout.font.color == tokens["text-primary"]
        assert fig.layout.xaxis.gridcolor == tokens["chart-grid"]
        assert fig.layout.xaxis.linecolor == tokens["chart-axis"]
        assert fig.layout.yaxis.tickfont.color == tokens["chart-tick"]
        assert fig.layout.hoverlabel.bgcolor == tokens["chart-hover-bg"]
        assert list(fig.layout.colorway)[:3] == [
            tokens["series-1"],
            tokens["series-2"],
            tokens["series-3"],
        ]
        candle = go.Figure(
            go.Candlestick(x=[1], open=[1], high=[2], low=[0.5], close=[1.5])
        )
        assert candle.data[0].increasing.line.color == tokens["chart-up"]
        assert candle.data[0].decreasing.line.color == tokens["chart-down"]
        assert "168, 158, 210" not in fig.to_json()
    finally:
        pio.templates.default = previous
