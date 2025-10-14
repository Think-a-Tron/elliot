"""Tool implementations that Elliot and its sub-agents can invoke."""

from __future__ import annotations

import difflib
import os
import shlex
import subprocess
import sys
import tempfile
from typing import List, Optional

from agents import function_tool
from openai import OpenAI

from .output import log_markdown, log_tool_event


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
    """Search code structurally with ast-grep."""

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
    if not pattern or not pattern.strip():
        status = "error"
        detail = "no pattern provided"
        output_text = "[elliot][tool ast_grep_run_search] no pattern provided."
        log_tool_event("ast_grep_run_search", status, params, detail)
        return output_text
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
    except Exception as error:  # pragma: no cover - subprocess defensive
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
    """Rewrite code structurally with ast-grep."""

    params = {
        "pattern": pattern,
        "rewrite": rewrite,
        "lang": lang or "auto",
        "paths": paths or ["."],
    }
    status = "success"
    detail: Optional[str] = None
    output_text = ""
    if not pattern or not pattern.strip():
        status = "error"
        detail = "no pattern provided"
        output_text = "[elliot][tool ast_grep_run_rewrite] no pattern provided."
        log_tool_event("ast_grep_run_rewrite", status, params, detail)
        return output_text
    if not rewrite or not rewrite.strip():
        status = "error"
        detail = "no rewrite provided"
        output_text = "[elliot][tool ast_grep_run_rewrite] no rewrite provided."
        log_tool_event("ast_grep_run_rewrite", status, params, detail)
        return output_text

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
    except Exception as error:  # pragma: no cover - subprocess defensive
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
    except Exception as error:  # pragma: no cover - os interaction
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
    except Exception as error:  # pragma: no cover - subprocess defensive
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
        detail = "lines must be positive"
        output_text = "[elliot][tool tail] lines must be positive."
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
    except Exception as error:  # pragma: no cover - subprocess defensive
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
    """Apply a sed command to a file with a diff preview and confirmation."""

    if not path or not os.path.isfile(path):
        return "[elliot][sed_write] error: invalid path."

    if not command:
        return "[elliot][sed_write] error: no sed command provided."

    with open(path, encoding="utf-8") as file:
        before = file.readlines()

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

    try:
        parsed_args = shlex.split(args)
    except ValueError as error:
        status = "error"
        detail = f"unable to parse arguments: {error}"
        output_text = f"[elliot][tool git_run] unable to parse arguments: {error}"
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
            ["git", *parsed_args],
            cwd=cwd,
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except Exception as error:  # pragma: no cover - subprocess defensive
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


@function_tool
def python_run(code: str, cwd: Optional[str] = None) -> str:
    """Execute Python code in a subprocess."""

    params = {"code": code, "cwd": cwd}
    status = "success"
    detail: Optional[str] = None
    output_text = ""

    if not code:
        status = "error"
        detail = "no code provided"
        output_text = "[elliot][tool python_run] no code provided."
        log_tool_event("python_run", status, params, detail)
        return output_text

    if not confirm_write_action(
        f"python_run will execute the following Python code in a subprocess:\n{code}"
    ):
        status = "skipped"
        detail = "execution denied"
        output_text = "[elliot][tool python_run] execution denied."
        log_tool_event("python_run", status, params, detail)
        return output_text

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=cwd,
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
        if result.returncode != 0:
            status = "error"
            detail = f"python exited with return code `{result.returncode}`"
            output_text = result.stderr or (
                f"[elliot][tool python_run] command failed (returncode={result.returncode})."
            )
        else:
            detail = "python code executed successfully"
            output_text = result.stdout
    except Exception as error:  # pragma: no cover - subprocess defensive
        status = "error"
        detail = f"failed to execute python: {error}"
        output_text = f"[elliot][tool python_run] unable to execute: {error}"
    finally:
        log_tool_event("python_run", status, params, detail)

    return output_text


@function_tool
def ruff_check(targets: str, cwd: Optional[str] = None) -> str:
    """Run `ruff check` on the provided targets."""

    params = {"targets": targets, "cwd": cwd}
    status = "success"
    detail: Optional[str] = None
    output_text = ""

    if not targets or not targets.strip():
        status = "error"
        detail = "no targets provided"
        output_text = "[elliot][tool ruff_check] no targets provided."
        log_tool_event("ruff_check", status, params, detail)
        return output_text

    command = ["ruff", "check", *shlex.split(targets)]

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except Exception as error:  # pragma: no cover - subprocess defensive
        status = "error"
        detail = f"failed to execute ruff check: {error}"
        output_text = f"[elliot][tool ruff_check] unable to execute: {error}"
    else:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        combined_output = "\n".join(part for part in [stdout, stderr] if part)
        if result.returncode != 0:
            status = "error"
            detail = f"ruff exited with return code `{result.returncode}`"
            output_text = combined_output or (
                f"[elliot][tool ruff_check] command failed (returncode={result.returncode})."
            )
        else:
            detail = "ruff check completed successfully"
            output_text = (
                combined_output or "[elliot][tool ruff_check] no issues found."
            )
    finally:
        log_tool_event("ruff_check", status, params, detail)

    return output_text


@function_tool
def ruff_format(targets: str, cwd: Optional[str] = None) -> str:
    """Run `ruff format` on the provided targets."""

    params = {"targets": targets, "cwd": cwd}
    status = "success"
    detail: Optional[str] = None
    output_text = ""

    if not targets or not targets.strip():
        status = "error"
        detail = "no targets provided"
        output_text = "[elliot][tool ruff_format] no targets provided."
        log_tool_event("ruff_format", status, params, detail)
        return output_text

    if not confirm_write_action(
        f"ruff_format will execute 'ruff format {targets}' and may modify files."
    ):
        status = "skipped"
        detail = "write permission denied"
        output_text = "[elliot][tool ruff_format] write permission denied."
        log_tool_event("ruff_format", status, params, detail)
        return output_text

    command = ["ruff", "format", *shlex.split(targets)]

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except Exception as error:  # pragma: no cover - subprocess defensive
        status = "error"
        detail = f"failed to execute ruff format: {error}"
        output_text = f"[elliot][tool ruff_format] unable to execute: {error}"
    else:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        combined_output = "\n".join(part for part in [stdout, stderr] if part)
        if result.returncode != 0:
            status = "error"
            detail = f"ruff exited with return code `{result.returncode}`"
            output_text = combined_output or (
                f"[elliot][tool ruff_format] command failed (returncode={result.returncode})."
            )
        else:
            detail = "ruff format completed successfully"
            output_text = (
                combined_output or "[elliot][tool ruff_format] format complete."
            )
    finally:
        log_tool_event("ruff_format", status, params, detail)

    return output_text


@function_tool
def ask_user(question: str) -> str:
    """Prompt the user for input via the terminal."""

    params = {"question": question}
    status = "success"
    detail: Optional[str] = None
    response = ""
    try:
        response = input(f"[elliot] {question}\nResponse: ")
        detail = "user provided response"
    except EOFError:
        status = "error"
        detail = "unable to prompt for input (EOF)"
        response = "[elliot][tool ask_user] unable to prompt for input (EOF)."
    finally:
        log_tool_event("ask_user", status, params, detail)

    return response


@function_tool
def ask_expert(
    question: str,
    context: str = "",
    system: str | None = None,
) -> str:
    """Proxy to the OpenAI Responses API to get design/implementation advice.
    Returns a plain string.
    """

    # Determine model from environment with a sensible default.
    model = os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-5")

    # Default system prompt if not provided.
    if system is None:
        system = (
            "You are a senior software engineering mentor. Provide concise, "
            "actionable guidance. Prefer minimal examples over verbose prose. "
            "Call out trade-offs and risks."
        )

    # Compose the prompt, including context only when provided.
    question_text = (question or "").strip()
    context_text = (context or "").strip()
    parts: list[str] = []
    if context_text:
        parts.append(f"Context:\n{context_text}")
    parts.append(f"Question:\n{question_text}")
    prompt = "\n\n".join(parts)

    try:
        client = OpenAI()

        response = client.responses.create(
            model=model,
            input=prompt,
            instructions=system,
        )
    except Exception as error:  # pragma: no cover - network/API defensive
        return f"ERROR: {error}"

    return response.output_text


SUBAGENT_TOOLS = {
    "code_search": ast_grep_run_search,
    "code_rewrite": ast_grep_run_rewrite,
    "list_dir": list_directory,
    "file_tail": tail,
    "read_slice": read_slice,
    "sed_inplace_edit": sed_write,
    "ask_expert": ask_expert,
    "git_command": git_run,
    "python_run": python_run,
    "ruff_check": ruff_check,
    "ruff_format": ruff_format,
    "ask_user": ask_user,
}

SUBAGENT_TOOL_NAMES = ", ".join(SUBAGENT_TOOLS.keys())
