"""Command-line interface entry point for Elliot."""

from __future__ import annotations

import argparse
from typing import List, Optional

from .agent import run_elliot
from .output import log_markdown


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments for launching Elliot."""

    parser = argparse.ArgumentParser(
        description="Elliot, the coding agents orchestrator."
    )
    parser.add_argument(
        "task",
        type=str,
        nargs="?",
        help="User request for Elliot to solve. If omitted, read from stdin.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Maximum turns for Elliot's top-level run (default: 30).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    """Entry point for running Elliot from the CLI."""

    args = parse_args(argv)

    if args.task is not None:
        user_task = args.task
    else:
        user_task = input("What should Elliot work on?").strip()

    final_output = run_elliot(user_task, max_turns=args.max_turns)
    log_markdown(final_output)


if __name__ == "__main__":  # pragma: no cover - direct CLI invocation
    main()
