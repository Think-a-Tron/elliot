from openai.types.chat import ChatCompletionToolParam


ripgrep_spec: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "ripgrep",
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
                "extensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File extensions to include e.g. ['py', 'js']; passed as -t",
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
                    "description": "Match by file extension e.g. ['.py', '.js']",
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
