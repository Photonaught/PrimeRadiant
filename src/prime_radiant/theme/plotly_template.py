"""Plotly template for the ship-library hull.

Colors are loaded from tokens.css. This module has no palette literals.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from prime_radiant.theme.css_tokens import load_tokens

TEMPLATE_NAME = "prime_radiant"

_LAYOUT_TOKENS = (
    "bg-plot-paper",
    "bg-plot",
    "text-primary",
    "text-secondary",
    "font-ui",
    "chart-grid",
    "chart-axis",
    "chart-zeroline",
    "chart-tick",
    "chart-spike",
    "chart-hover-bg",
    "chart-hover-border",
    "chart-border",
    "chart-up",
    "chart-down",
    "accent-steel",
    "accent-brass",
    "bg-deep-mid",
    "bg-panel-solid",
)
_SERIES = tuple(f"series-{index}" for index in range(1, 9))


def chart_theme(tokens: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Layout and trace defaults whose colors are resolved token values."""
    palette = dict(tokens) if tokens is not None else dict(load_tokens())
    missing = [name for name in (*_LAYOUT_TOKENS, *_SERIES) if name not in palette]
    if missing:
        raise KeyError("tokens.css missing: " + ", ".join(missing))

    def axis() -> dict[str, Any]:
        return {
            "gridcolor": palette["chart-grid"],
            "linecolor": palette["chart-axis"],
            "zerolinecolor": palette["chart-zeroline"],
            "tickcolor": palette["chart-axis"],
            "tickfont": {"color": palette["chart-tick"]},
            "title": {"font": {"color": palette["text-secondary"]}},
            "spikecolor": palette["chart-spike"],
        }

    ink = {"color": palette["text-primary"], "family": palette["font-ui"]}
    up = palette["chart-up"]
    down = palette["chart-down"]
    # OHLC traces paint the wick only. Candles also fill the body.
    ohlc = {
        "increasing": {"line": {"color": up}},
        "decreasing": {"line": {"color": down}},
    }
    candle = {
        "increasing": {"line": {"color": up}, "fillcolor": up},
        "decreasing": {"line": {"color": down}, "fillcolor": down},
    }
    return {
        "layout": {
            "paper_bgcolor": palette["bg-plot-paper"],
            "plot_bgcolor": palette["bg-plot"],
            "font": {**ink, "size": 12},
            "title": {"font": {"color": palette["text-primary"], "size": 14}},
            "colorway": [palette[name] for name in _SERIES],
            "xaxis": axis(),
            "yaxis": axis(),
            "legend": {
                "font": {"color": palette["text-secondary"], "family": palette["font-ui"]},
                "bgcolor": palette["bg-plot-paper"],
                "bordercolor": palette["chart-border"],
            },
            "hoverlabel": {
                "bgcolor": palette["chart-hover-bg"],
                "bordercolor": palette["chart-hover-border"],
                "font": ink,
            },
            "modebar": {
                "bgcolor": palette["bg-plot-paper"],
                "color": palette["accent-steel"],
                "activecolor": palette["accent-brass"],
            },
            "coloraxis": {
                "colorbar": {
                    "tickfont": {"color": palette["chart-tick"]},
                    "outlinecolor": palette["chart-border"],
                }
            },
            "colorscale": {
                "sequential": [
                    [0.0, palette["bg-deep-mid"]],
                    [0.5, palette["accent-steel"]],
                    [1.0, palette["accent-brass"]],
                ],
                "diverging": [
                    [0.0, palette["chart-down"]],
                    [0.5, palette["text-primary"]],
                    [1.0, palette["chart-up"]],
                ],
            },
            "annotationdefaults": {"font": {"color": palette["text-secondary"]}},
        },
        "data": {
            "candlestick": [candle],
            "ohlc": [ohlc],
        },
    }


def build_template(tokens: Mapping[str, str] | None = None) -> Any:
    """Return a plotly Template built from tokens.css."""
    import plotly.graph_objects as go

    theme = chart_theme(tokens)
    return go.layout.Template(layout=theme["layout"], data=theme["data"])


def register_template(*, default: bool = True) -> str:
    """Register the template with Plotly. Makes it the default when asked."""
    import plotly.io as pio

    pio.templates[TEMPLATE_NAME] = build_template()
    if default:
        pio.templates.default = TEMPLATE_NAME
    return TEMPLATE_NAME
