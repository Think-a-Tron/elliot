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

fd_spec: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "fd",
        "description": "List files and directories with fd (fast find)",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex or glob to match file names. Leave empty to list everything",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in, defaults to current directory",
                    "default": ".",
                },
                "extensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Match by file extension e.g. ['py', 'js']",
                },
                "type": {
                    "type": "string",
                    "enum": ["file", "directory"],
                    "description": "Restrict results to files or directories",
                },
                "hidden": {
                    "type": "boolean",
                    "description": "Include hidden files and directories",
                    "default": False,
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Limit directory recursion depth",
                },
            },
        },
    },
}


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

    return f"""
cmd: {" ".join(cmd)}

stdout:
{result.stdout}

stderror:
{result.stderr}"""


def fd(args: dict, root: str):
    abs_root = os.path.abspath(root)

    cmd = ["fd", "--color", "never"]

    if args.get("hidden", False):
        cmd.append("--hidden")

    t = args.get("type")
    if t == "file":
        cmd.extend(["-t", "f"])
    elif t == "directory":
        cmd.extend(["-t", "d"])

    max_depth = args.get("max_depth", 0)
    if isinstance("max_depth", int) and max_depth > 0:
        cmd.extend(["-d", str(max_depth)])

    exts = args.get("extensions") or []
    for ext in exts:
        cmd.extend(["-e", ext])

    pattern = args.get("pattern", "")
    cmd.append(pattern)

    path = args.get("path") or "."
    abs_path = os.path.join(abs_root, path)
    cmd.append(abs_path)

    result = subprocess.run(cmd, capture_output=True, text=True)

    return f"""
cmd: {" ".join(cmd)}

stdout:
{result.stdout}

stderror:
{result.stderr}"""
