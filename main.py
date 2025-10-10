import argparse
import os
import subprocess
from typing import List, Optional

from agents import Agent, Runner, function_tool

MODEL = "gpt-5"


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
    print(
        "[elliot][tool ast_grep_run_search] "
        f"pattern={pattern!r}, lang={lang or 'auto'}, "
        f"paths={paths or ['.']}, globs={globs or []}, context={context}"
    )
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

    print(
        f"[elliot][tool ast_grep_run_search] completed (returncode={result.returncode})"
    )
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

    print(
        "[elliot][tool ast_grep_run_rewrite] "
        f"pattern={pattern!r}, rewrite={rewrite!r}, "
        f"lang={lang or 'auto'}, paths={paths or ['.']}"
    )
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

    print(
        "[elliot][tool ast_grep_run_rewrite] "
        f"completed (returncode={result.returncode})"
    )
    return "\n".join(output)


@function_tool
def list_directory(path: str = ".", show_hidden: bool = False) -> str:
    """List files and directories within a path."""

    print(f"[elliot][tool list_directory] path={path!r}, show_hidden={show_hidden}")
    target_path = path or "."

    try:
        entries = sorted(os.listdir(target_path))
    except Exception as error:
        message = (
            f"[elliot][tool list_directory] unable to list {target_path!r}: {error}"
        )
        print(message)
        return message

    filtered = [entry for entry in entries if show_hidden or not entry.startswith(".")]

    result = "\n".join(filtered)
    print("[elliot][tool list_directory] completed.")
    return result


@function_tool
def head(path: str, lines: int = 50) -> str:
    """Return the first N lines from a file, similar to the Unix `head` command."""

    print(f"[elliot][tool head] path={path!r}, lines={lines}")
    if not path:
        message = "[elliot][tool head] no path provided."
        print(message)
        return message

    if lines <= 0:
        message = "[elliot][tool head] number of lines must be positive."
        print(message)
        return message

    command = ["head", "-n", str(lines), path]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except FileNotFoundError:
        message = "[elliot][tool head] 'head' command not found."
        print(message)
        return message
    except Exception as error:
        message = f"[elliot][tool head] unable to execute head: {error}"
        print(message)
        return message

    if result.returncode != 0:
        message = (
            f"[elliot][tool head] command failed (returncode={result.returncode}). "
            f"{result.stderr.strip() or 'Unknown error.'}"
        )
        print(message)
        return message

    print("[elliot][tool head] completed.")
    return result.stdout


@function_tool
def tail(path: str, lines: int = 50) -> str:
    """Return the last N lines from a file, similar to the Unix `tail` command."""

    print(f"[elliot][tool tail] path={path!r}, lines={lines}")
    if not path:
        message = "[elliot][tool tail] no path provided."
        print(message)
        return message

    if lines <= 0:
        message = "[elliot][tool tail] number of lines must be positive."
        print(message)
        return message

    command = ["tail", "-n", str(lines), path]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except FileNotFoundError:
        message = "[elliot][tool tail] 'tail' command not found."
        print(message)
        return message
    except Exception as error:
        message = f"[elliot][tool tail] unable to execute tail: {error}"
        print(message)
        return message

    if result.returncode != 0:
        message = (
            f"[elliot][tool tail] command failed (returncode={result.returncode}). "
            f"{result.stderr.strip() or 'Unknown error.'}"
        )
        print(message)
        return message

    print("[elliot][tool tail] completed.")
    return result.stdout


TOOLS = {
    "ast_grep_run_search": ast_grep_run_search,
    "ast_grep_run_rewrite": ast_grep_run_rewrite,
    "list_directory": list_directory,
    "tail": tail,
    "head": head,
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
    print(
        f"[elliot] spawning sub-agent '{name}' "
        f"(tools: {', '.join(tools) or 'none'}; max_turns={max_turns})"
    )

    result = await Runner.run(subagent, task, max_turns=max_turns)

    print(f"[elliot] sub-agent '{name}' completed.")
    print(result.final_output)

    return result.final_output


ELLIOT_INSTRUCTIONS = f"""You are Elliot, the orchestrator agent for a team of specialist coding agents.
Your responsibilities:
- Understand the user's goal, clarify missing information, and structure the work.
- Break the goal into concrete sub-tasks when it adds value. Keep tasks focused and deliverable-based.
- For each sub-task, spawn a sub-agent with clear instructions, success criteria, relevant constraints, and only the tools the agent needs. The allowed tool names are: {TOOLS.keys()}.
- Configure max_turns thoughtfully based on task complexity (default to 15 if unsure).
- When a task is tiny or purely explanatory, you may answer directly without spawning a subagent.
- Integrate sub-agent outputs into a cohesive final response that resolves the user's original request.
- Escalate uncertainties back to the user instead of guessing.
- Track dependencies between tasks and run them sequentially if required.
- Be deliberate: outline your plan before executing, note what each subagent should produce, and summarize how their outputs combine in the final answer.
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
    print(final_output)


if __name__ == "__main__":
    main()
