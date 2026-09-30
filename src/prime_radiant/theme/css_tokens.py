"""Load palette custom properties from tokens.css.

tokens.css is the only place color literals live. Callers receive resolved
values, so a `var(--accent-brass)` alias becomes the brass hex Plotly can use.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

THEME_DIR = Path(__file__).resolve().parent
TOKENS_PATH = THEME_DIR / "tokens.css"
APP_PATH = THEME_DIR / "app.css"

_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_TOKEN_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);")
_VAR_RE = re.compile(r"var\(\s*--([a-z0-9-]+)\s*(?:,\s*([^)]*?)\s*)?\)")
_IMPORT_TOKENS_RE = re.compile(
    r"""@import\s+(?:url\(\s*)?["']tokens\.css["']\s*\)?\s*;""",
    re.IGNORECASE,
)


def load_tokens(path: str | Path | None = None) -> Mapping[str, str]:
    """Return resolved custom properties from a :root block."""
    css_path = TOKENS_PATH if path is None else Path(path)
    text = css_path.read_text(encoding="utf-8")
    resolved = _resolve(_parse_root_tokens(text))
    return MappingProxyType(resolved)


def theme_stylesheet() -> str:
    """Inline tokens.css and app.css for hosts that inject one stylesheet."""
    tokens = TOKENS_PATH.read_text(encoding="utf-8").rstrip()
    app = _IMPORT_TOKENS_RE.sub("", APP_PATH.read_text(encoding="utf-8")).strip()
    return f"{tokens}\n\n{app}\n"


def _parse_root_tokens(css: str) -> dict[str, str]:
    body = _root_body(_COMMENT_RE.sub("", css))
    found: dict[str, str] = {}
    for name, value in _TOKEN_RE.findall(body):
        if name in found:
            raise ValueError(f"duplicate token --{name}")
        found[name] = " ".join(value.strip().split())
    if not found:
        raise ValueError("tokens.css has no custom properties in :root")
    return found


def _root_body(css: str) -> str:
    parts: list[str] = []
    for match in re.finditer(r":root\s*\{", css):
        depth = 1
        index = match.end()
        while index < len(css) and depth:
            char = css[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            index += 1
        if depth != 0:
            raise ValueError("unclosed :root block in tokens.css")
        parts.append(css[match.end() : index - 1])
    if not parts:
        raise ValueError("tokens.css has no :root block")
    return "\n".join(parts)


def _resolve(raw: dict[str, str]) -> dict[str, str]:
    resolved: dict[str, str] = {}

    def walk(name: str, stack: tuple[str, ...]) -> str:
        if name in resolved:
            return resolved[name]
        if name not in raw:
            raise ValueError(f"undefined token --{name}")
        if name in stack:
            cycle = " -> ".join(f"--{part}" for part in (*stack, name))
            raise ValueError(f"token cycle: {cycle}")

        def replace(match: re.Match[str]) -> str:
            ref = match.group(1)
            fallback = match.group(2)
            if ref not in raw:
                if fallback is not None and fallback.strip():
                    return fallback.strip()
                raise ValueError(f"undefined token --{ref} referenced by --{name}")
            return walk(ref, (*stack, name))

        resolved[name] = _VAR_RE.sub(replace, raw[name])
        return resolved[name]

    for name in raw:
        walk(name, ())
    return resolved
