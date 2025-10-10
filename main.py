import os
import subprocess
from typing import List

from agents import Agent, Runner, function_tool

MODEL = "grok-code-fast-1"


@function_tool
def ast_grep_run_search(
    pattern: str, lang: str, paths: List[str], globs: List[str], context: int
) -> str:
    """Search code structurally with ast-grep.

    Args:
        pattern: AST pattern to match
        lang: Language of the pattern (e.g., ts, py, rust, go)
        paths: Files or directories to search
        globs: Include/exclude file globs
        context: Number of lines of context to show around each match
    """
    command = ["ast-grep", "run", "--pattern", pattern]

    if lang:
        command.extend(["--lang", lang])

    if context:
        command.extend(["--context", str(context)])

    for glob in globs or []:
        command.extend(["--globs", glob])

    command.extend(paths or ["."])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
    )

    output = []
    if result.stdout:
        output.append(result.stdout.rstrip())
    if result.stderr:
        output.append(result.stderr.rstrip())

    if result.returncode != 0 and not output:
        output.append(f"ast-grep exited with return code {result.returncode}.")

    return "\n".join(output)


@function_tool
def ast_grep_run_rewrite(
    pattern: str, rewrite: str, lang: str, paths: List[str]
) -> str:
    """Rewrite code structurally with ast-grep.

    Args:
        pattern: AST pattern to match
        rewrite: Replacement template for the matched AST node
        lang: Language of the pattern (e.g., ts, py, rust, go)
        paths: Files or directories to apply the rewrite
    """

    command = [
        "ast-grep",
        "run",
        "--pattern",
        pattern,
        "--rewrite",
        rewrite,
        "--update-all",
    ]

    if lang:
        command.extend(["--lang", lang])

    command.extend(paths or ["."])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
    )

    output = []
    if result.stdout:
        output.append(result.stdout.rstrip())
    if result.stderr:
        output.append(result.stderr.rstrip())

    if result.returncode != 0 and not output:
        output.append(f"ast-grep exited with return code {result.returncode}.")

    return "\n".join(output)


TOOLS = {
    "ast_grep_run_search": ast_grep_run_search,
    "ast_grep_run_rewrite": ast_grep_run_rewrite,
}


@function_tool
def spawn_subagent(
    name: str, instructions: str, task: str, tools: List[str], max_turns: int
) -> str:
    """Spins up a focused helper agent with its own toolset, instructions, and turn budget.
    Include agent behavior, deliverables, additional context, etc. in the instructions."""

    subagent = Agent(
        name=name,
        instructions=instructions,
        model=MODEL,
        tools=[TOOLS[tool] for tool in tools],
    )
    result = Runner.run_sync(subagent, task, max_turns=max_turns)

    return result.final_output
