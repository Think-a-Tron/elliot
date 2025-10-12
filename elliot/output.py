"""Utilities for rendering Elliot output consistently."""

from __future__ import annotations

from typing import Any, Dict, Optional

from rich.console import Console
from rich.markdown import Markdown

console = Console()


def _format_value(value: Any) -> str:
    """Render values in a markdown-friendly way for logs."""

    if isinstance(value, str):
        return f"`{value}`" if value else "`''`"
    if isinstance(value, (list, tuple)):
        rendered = ", ".join(_format_value(item) for item in value)
        return f"[{rendered}]"
    if isinstance(value, dict):
        rendered = ", ".join(
            f"{_format_value(key)}: {_format_value(val)}"
            for key, val in value.items()
        )
        return f"{{{rendered}}}"
    return f"`{value!r}`"


def log_markdown(message: str) -> None:
    """Print log output using the shared console as markdown."""

    console.print(Markdown(message))
    console.print()


def log_tool_event(
    tool: str, status: str, params: Dict[str, Any], detail: Optional[str] = None
) -> None:
    """Emit a Markdown entry describing a tool invocation."""

    parameters = (
        ", ".join(f"{key}={_format_value(value)}" for key, value in params.items())
        or "none"
    )
    blocks = [f"**[elliot][tool {tool}] {status.upper()}**"]
    if detail:
        blocks.append(detail)
    blocks.append(f"params: {parameters}")
    log_markdown("\n".join(blocks))
