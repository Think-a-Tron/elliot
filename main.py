import argparse
import difflib
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from agents import Agent, Runner, function_tool, set_tracing_disabled
from rich.console import Console
from rich.markdown import Markdown

MODEL = "gpt-5"
set_tracing_disabled(True)

console = Console()


def _format_value(value: Any) -> str:
    """Format values for logging in a markdown-friendly way."""

    if isinstance(value, str):
        return f"`{value}`" if value else "`''`"
    if isinstance(value, (list, tuple)):
        rendered = ", ".join(_format_value(item) for item in value)
        return f"[{rendered}]"
    if isinstance(value, dict):
        rendered = ", ".join(
            f"{_format_value(key)}: {_format_value(val)}" for key, val in value.items()
        )
        return f"{{{rendered}}}"
    return f"`{value!r}`"


def log_markdown(message: str) -> None:
    """Render log output as simple Markdown with a trailing spacer."""

    console.print(Markdown(message))
    console.print()


def log_tool_event(
    tool: str, status: str, params: Dict[str, Any], detail: Optional[str] = None
) -> None:
    """Emit a single markdown log entry describing a tool invocation."""

    parameters = (
        ", ".join(f"{key}={_format_value(value)}" for key, value in params.items())
        or "none"
    )
    blocks = [f"**[elliot][tool {tool}] {status.upper()}**"]
    if detail:
        blocks.append(detail)
    blocks.append(f"params: {parameters}")
    log_markdown("\n".join(blocks))


def confirm_write_action(description: str) -> bool:
    """Prompt the user for permission before performing a write action."""

    prompt = f"[elliot] {description}\nProceed? [y/N]: "
    try:
        response = input(prompt)
    except EOFError:
        log_markdown(
            "**[elliot]** unable to prompt for confirmation (EOF). Denying by default."
        )
        return False

    allow = response.strip().lower() in {"y", "yes"}
    if allow:
        log_markdown("**[elliot]** permission granted.")
    else:
        log_markdown("**[elliot]** permission denied.")
    return allow


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
    params = {
        "pattern": pattern,
        "lang": lang or "auto",
        "paths": paths or ["."],
        "globs": globs or [],
        "context": context,
    }
    status = "success"
    detail: Optional[str] = None
    output_text = ""
    command = ["ast-grep", "run", "--pattern", pattern]

    if lang:
        command.extend(["--lang", lang])

    if context:
        command.extend(["--context", str(context)])

    for glob in globs or []:
        command.extend(["--globs", glob])

    command.extend(paths or ["."])

    try:
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
        if result.returncode != 0:
            status = "error"
            detail = f"ast-grep exited with return code `{result.returncode}`"
            if not output:
                output.append(f"ast-grep exited with return code {result.returncode}.")
        else:
            detail = "ast-grep completed successfully"
        output_text = "\n".join(output)
    except Exception as error:
        status = "error"
        detail = f"failed to invoke ast-grep: {error}"
        output_text = (
            f"[elliot][tool ast_grep_run_search] unable to execute ast-grep: {error}"
        )
    finally:
        log_tool_event("ast_grep_run_search", status, params, detail)

    return output_text


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

    params = {
        "pattern": pattern,
        "rewrite": rewrite,
        "lang": lang or "auto",
        "paths": paths or ["."],
    }
    status = "success"
    detail: Optional[str] = None
    output_text = ""

    if not confirm_write_action(
        "ast_grep_run_rewrite will modify files in-place using ast-grep."
    ):
        status = "skipped"
        detail = "write permission denied"
        output_text = "[elliot][tool ast_grep_run_rewrite] write permission denied."
        log_tool_event("ast_grep_run_rewrite", status, params, detail)
        return output_text

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

    try:
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

        if result.returncode != 0:
            status = "error"
            detail = f"ast-grep exited with return code `{result.returncode}`"
            if not output:
                output.append(f"ast-grep exited with return code {result.returncode}.")
        else:
            detail = "ast-grep rewrite completed successfully"

        output_text = "\n".join(output)
    except Exception as error:
        status = "error"
        detail = f"failed to invoke ast-grep: {error}"
        output_text = (
            f"[elliot][tool ast_grep_run_rewrite] unable to execute ast-grep: {error}"
        )
    finally:
        log_tool_event("ast_grep_run_rewrite", status, params, detail)

    return output_text


@function_tool
def list_directory(path: str = ".", show_hidden: bool = False) -> str:
    """List files and directories within a path."""

    target_path = path or "."
    params = {"path": target_path, "show_hidden": show_hidden}
    status = "success"
    detail: Optional[str] = None
    result = ""

    try:
        entries = sorted(os.listdir(target_path))
    except Exception as error:
        status = "error"
        detail = str(error)
        result = (
            f"[elliot][tool list_directory] unable to list {target_path!r}: {error}"
        )
    else:
        filtered = [
            entry for entry in entries if show_hidden or not entry.startswith(".")
        ]
        detail = f"returned {len(filtered)} entries"
        result = "\n".join(filtered)
    finally:
        log_tool_event("list_directory", status, params, detail)

    return result


@function_tool
def read_slice(path: str, start: int = 1, end: Optional[int] = None) -> str:
    """Return a slice of a file using sed (inclusive start/end line numbers)."""

    params = {"path": path, "start": start, "end": end}
    status = "success"
    detail: Optional[str] = None
    output_text = ""

    if not path:
        status = "error"
        detail = "no path provided"
        output_text = "[elliot][tool read_slice] no path provided."
        log_tool_event("read_slice", status, params, detail)
        return output_text

    if start <= 0 or (end is not None and end < start):
        status = "error"
        detail = "invalid line range"
        output_text = "[elliot][tool read_slice] invalid line range."
        log_tool_event("read_slice", status, params, detail)
        return output_text

    if end is not None:
        range_spec = f"{start},{end}p"
    else:
        range_spec = f"{start},$p"

    command = ["sed", "-n", range_spec, path]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except Exception as error:
        status = "error"
        detail = f"unable to execute sed: {error}"
        output_text = f"[elliot][tool read_slice] unable to execute sed: {error}"
    else:
        if result.returncode != 0:
            status = "error"
            detail = f"sed failed with return code `{result.returncode}`"
            output_text = (
                f"[elliot][tool read_slice] command failed (returncode={result.returncode}). "
                f"{result.stderr.strip() or 'Unknown error.'}"
            )
        else:
            detail = "slice read successfully"
            output_text = result.stdout
    finally:
        log_tool_event("read_slice", status, params, detail)

    return output_text


@function_tool
def tail(path: str, lines: int = 50) -> str:
    """Return the last N lines from a file, similar to the Unix `tail` command."""

    params = {"path": path, "lines": lines}
    status = "success"
    detail: Optional[str] = None
    output_text = ""

    if not path:
        status = "error"
        detail = "no path provided"
        output_text = "[elliot][tool tail] no path provided."
        log_tool_event("tail", status, params, detail)
        return output_text

    if lines <= 0:
        status = "error"
        detail = "non-positive line count"
        output_text = "[elliot][tool tail] number of lines must be positive."
        log_tool_event("tail", status, params, detail)
        return output_text

    command = ["tail", "-n", str(lines), path]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except Exception as error:
        status = "error"
        detail = f"unable to execute tail: {error}"
        output_text = f"[elliot][tool tail] unable to execute tail: {error}"
    else:
        if result.returncode != 0:
            status = "error"
            detail = f"tail failed with return code `{result.returncode}`"
            output_text = (
                f"[elliot][tool tail] command failed (returncode={result.returncode}). "
                f"{result.stderr.strip() or 'Unknown error.'}"
            )
        else:
            detail = f"read {lines} line(s)"
            output_text = result.stdout
    finally:
        log_tool_event("tail", status, params, detail)

    return output_text


@function_tool
def sed_write(path: str, command: str) -> str:
    """Apply a sed command to a file with a diff preview and confirmation, then write changes atomically."""

    if not path or not os.path.isfile(path):
        return "[elliot][sed_write] error: invalid path."

    if not command:
        return "[elliot][sed_write] error: no sed command provided."

    with open(path, encoding="utf-8") as f:
        before = f.readlines()

    result = subprocess.run(
        ["sed", command, path],
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
    )

    if result.returncode != 0:
        return f"[elliot][sed_write] sed failed: {result.stderr.strip() or 'unknown error'}"

    after = result.stdout.splitlines(keepends=True)

    diff = "".join(
        difflib.unified_diff(before, after, fromfile=path, tofile=f"{path} (edited)")
    )

    if not diff.strip():
        return "[elliot][sed_write] no changes detected."

    print(diff)

    if not confirm_write_action("Apply above diff?"):
        return "[elliot][sed_write] edit cancelled."

    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
        tmp.writelines(after)
        tmp_path = tmp.name
    os.replace(tmp_path, path)

    return "[elliot][sed_write] edit applied successfully."


@function_tool
def git_run(args: str, cwd: Optional[str] = None) -> str:
    """Run git commands. Just specify the args after `git`."""

    params = {"args": args, "cwd": cwd}
    status = "success"
    detail: Optional[str] = None
    output_text = ""

    if not args:
        status = "error"
        detail = "no arguments provided"
        output_text = "[elliot][tool git_run] no arguments provided."
        log_tool_event("git_run", status, params, detail)
        return output_text

    if not confirm_write_action(f"git_run will execute 'git {args}' in a shell."):
        status = "skipped"
        detail = "write permission denied"
        output_text = "[elliot][tool git_run] write permission denied."
        log_tool_event("git_run", status, params, detail)
        return output_text

    try:
        result = subprocess.run(
            ["git", *args.split()],
            cwd=cwd,
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except Exception as error:
        status = "error"
        detail = f"failed to execute git: {error}"
        output_text = f"[elliot][tool git_run] unable to execute git: {error}"
    else:
        if result.returncode != 0:
            status = "error"
            detail = f"git exited with return code `{result.returncode}`"
            output_text = result.stderr or (
                f"[elliot][tool git_run] command failed (returncode={result.returncode})."
            )
        else:
            detail = "git command completed successfully"
            output_text = result.stdout
    finally:
        log_tool_event("git_run", status, params, detail)

    return output_text


TOOLS = {
    "ast_grep_run_search": ast_grep_run_search,
    "ast_grep_run_rewrite": ast_grep_run_rewrite,
    "list_directory": list_directory,
    "tail": tail,
    "read_slice": read_slice,
    "sed_write": sed_write,
    "git_run": git_run,
}


@function_tool
async def spawn_subagent(
    name: str, instructions: str, task: str, tools: List[str], max_turns: int
) -> str:
    """Spins up a focused helper agent with its own toolset, instructions, and turn budget.
    Include agent behavior, deliverables, additional context, etc. in the instructions."""

    unknown_tools = [tool for tool in tools if tool not in TOOLS]

    if unknown_tools:
        raise ValueError(
            f"Unknown tool(s): {', '.join(unknown_tools)}. "
            f"Available tools: {', '.join(sorted(TOOLS))}"
        )

    subagent = Agent(
        name=name,
        instructions=instructions,
        model=MODEL,
        tools=[TOOLS[tool] for tool in tools],
    )
    params = {
        "name": name,
        "tools": tools or [],
        "max_turns": max_turns,
    }
    status = "success"
    detail: Optional[str] = None
    final_output = ""

    tool_list = ", ".join(tools) if tools else "none"
    log_markdown(
        "\n".join(
            [
                f"**[elliot]** spawning sub-agent `{name}`",
                f"tools: {tool_list}",
                f"max_turns: {max_turns}",
            ]
        )
    )

    try:
        result = await Runner.run(subagent, task, max_turns=max_turns)
        final_output = result.final_output
        detail = "sub-agent completed successfully"
    except Exception as error:
        status = "error"
        detail = f"sub-agent failed: {error}"
        raise
    finally:
        log_tool_event("spawn_subagent", status, params, detail)

    if final_output:
        console.print(Markdown(final_output))

    return final_output


ELLIOT_INSTRUCTIONS = f"""You are Elliot, the orchestrator agent for a team of specialist coding agents.
Your responsibilities:
- Understand the user's goal, clarify missing information, and structure the work.
- Gather the necessary context before proposing plans or delegating: inspect prior outputs, review relevant files, and run read-only commands when helpful.
- Break the goal into concrete sub-tasks when it adds value. Keep tasks focused and deliverable-based.
- For each sub-task, spawn a sub-agent with clear instructions, success criteria, relevant constraints, and only the tools the agent needs. The allowed tool names are: {TOOLS.keys()}.
- Configure max_turns thoughtfully based on task complexity (default to 15 if unsure).
- When a task is tiny or purely explanatory, you may answer directly without spawning a subagent.
- Integrate sub-agent outputs into a cohesive final response that resolves the user's original request.
- Escalate uncertainties back to the user instead of guessing.
- Track dependencies between tasks and run them sequentially if required.
- Be deliberate: summarize the relevant context you collected, outline your plan before executing, note what each subagent should produce, and explain how their outputs combine in the final answer.
- Close with a concise summary of outcomes and next steps if they exist."""


def create_elliot_agent() -> Agent:
    """Build the main Elliot agent configured to orchestrate sub-agents."""

    return Agent(
        name="Elliot",
        instructions=ELLIOT_INSTRUCTIONS,
        model=MODEL,
        tools=[spawn_subagent],
    )


def run_elliot(task: str, max_turns: int = 30) -> str:
    """Execute the Elliot agent against the provided task."""

    elliot_agent = create_elliot_agent()
    result = Runner.run_sync(elliot_agent, task, max_turns=max_turns)
    return result.final_output


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
        default=40,
        help="Maximum turns for Elliot's top-level run (default: 40).",
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


if __name__ == "__main__":
    main()
