import os
import subprocess

from openai.types.chat import ChatCompletionToolParam

rg_spec: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "rg",
        "description": "Search for patterns in files using ripgrep",
        "parameters": {
            "type": "object",
            "required": ["pattern"],
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex or string to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file path to search",
                },
                "file_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File types to include e.g. ['rust', 'py']; passed as -t",
                },
                "glob": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Shell globs for including files, e.g. ['*.py', 'src/**']; passed as --glob",
                },
                "ignore_case": {
                    "type": "boolean",
                    "description": "Perform case-insensitive search; passed as -i",
                    "default": False,
                },
                "word_regexp": {
                    "type": "boolean",
                    "description": "Only match whole words; passed as -w",
                    "default": False,
                },
                "context": {
                    "type": "integer",
                    "description": "Show NUM lines of context around matches; passed as -C NUM",
                    "default": 0,
                },
            },
        },
    },
}

sed_spec: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "sed",
        "description": "Fetch specific lines from a text file using sed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the input file.",
                },
                "line_range": {
                    "type": "string",
                    "description": "Line numbers or range in sed format (e.g., '5', '10,20', '5,+3').",
                },
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to match lines. If provided, sed will print matching lines.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
}


finish_spec: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "finish",
        "description": "Call this function when you have the answer",
        "parameters": {
            "type": "object",
            "required": ["answer"],
            "properties": {"answer": {"type": "string"}},
        },
    },
}

plan_spec: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "propose_plan",
        "description": (
            "Create a concrete, step-by-step plan to resolve the issue using the available "
            "code context. Include searches (rg), edits (sed/manual), and validations. "
            "Prefer precise, atomic steps and runnable commands/examples."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Concise summary of the approach.",
                },
                "steps": {
                    "type": "array",
                    "description": "Ordered steps from searches to edits",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Short stable id, e.g. S1, E2",
                            },
                            "kind": {
                                "type": "string",
                                "enum": ["search", "edit"],
                                "description": "What type of action this is.",
                            },
                            "why": {
                                "type": "string",
                                "description": "Rationale for this step.",
                            },
                            "what": {
                                "type": "string",
                                "description": "Exactly what to do/inspect/change.",
                            },
                            "tool": {
                                "type": "string",
                                "enum": ["rg", "sed"],
                                "description": "Primary tool to use.",
                            },
                            "targets": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "File globs or concrete paths/functions.",
                            },
                        },
                        "required": ["id", "kind", "what"],
                    },
                },
            },
            "required": ["summary", "steps"],
            "additionalProperties": False,
        },
    },
}


def _truncate_output(output: str, max_lines: int = 100) -> str:
    lines = output.splitlines()

    if len(lines) > max_lines:
        truncated = "\n".join(lines[:max_lines])
        return f"{truncated}\n... [compressed: {len(lines) - max_lines} more lines]"

    return output


def rg(args: dict, root: str) -> str:
    abs_root = os.path.abspath(root)

    cmd = ["rg", "--color", "never", "--line-number"]

    if args.get("ignore_case", False):
        cmd.append("-i")

    if args.get("word_regexp", False):
        cmd.append("-w")

    context = args.get("context", 0)
    if context and isinstance(context, int) and context > 0:
        cmd.extend(["-C", str(context)])

    file_types = args.get("file_types") or []
    for ft in file_types:
        cmd.extend(["-t", ft])

    globs = args.get("glob") or []
    for g in globs:
        cmd.extend(["--glob", g])

    pattern = args.get("pattern", "")
    cmd.append(pattern)

    path = args.get("path") or "."
    abs_path = os.path.join(abs_root, path)
    cmd.append(abs_path)

    result = subprocess.run(cmd, capture_output=True, text=True)

    stdout = _truncate_output(result.stdout)

    return f"""cmd: {" ".join(cmd)}

stdout:
{stdout}

stderr:
{result.stderr}"""


def sed(args: dict, root: str):
    abs_root = os.path.abspath(root)
    cmd = ["sed", "-n"]

    line_range = args.get("line_range")
    pattern = args.get("pattern")

    if bool(line_range) == bool(pattern):
        return "Error: provide exactly one of 'pattern' or 'line_range'."

    if pattern:
        cmd.append(f"/{pattern}/p")
    else:
        cmd.append(f"{line_range}p")

    path = args.get("path") or "."
    abs_path = os.path.join(abs_root, path)
    cmd.append(abs_path)

    result = subprocess.run(cmd, capture_output=True, text=True)

    stdout = _truncate_output(result.stdout)

    return f"""cmd: {" ".join(cmd)}

stdout:
{stdout}

stderr:
{result.stderr}"""
