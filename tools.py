from openai.types.chat import ChatCompletionToolParam


ripgrep_spec: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "ripgrep",
        "description": "Search for patterns in files using ripgrep.",
        "parameters": {
            "type": "object",
            "required": ["pattern"],
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex or string to search for.",
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file path to search.",
                },
                "file_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File type filters, e.g. ['py', 'js']; passed as -t",
                },
                "exclude_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File types to exclude, e.g. ['md']; passed as -T",
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
                "line_number": {
                    "type": "boolean",
                    "description": "Show line numbers in results; passed as -n",
                    "default": True,
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
