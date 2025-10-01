from openai import OpenAI
from openai.types.responses import ToolParam

client = OpenAI()

SPAWN_SUBAGENT: ToolParam = {
    "type": "function",
    "name": "spawn_subagent",
    "description": "",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "instructions": {"type": "string"},
            "task": {"type": "string"},
            "tools": {"type": "array", "items": {"type": "string"}},
            "max_turns": {"type": "number"},
        },
        "required": ["name", "instructions", "task", "tools", "max_turns"],
        "additionalProperties": False,
    },
    "strict": True,
}

AST_GREP_SEARCH: ToolParam = {
    "type": "function",
    "name": "ast_grep_run_search",
    "description": "Search code structurally with ast-grep",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "AST pattern to match"},
            "lang": {
                "type": "string",
                "description": "Language of the pattern (e.g., ts, py, rust, go)",
            },
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files or directories to search",
            },
            "globs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Include/exclude file globs",
            },
            "context": {
                "type": "integer",
                "description": "Number of lines of context to show around each match",
            },
        },
        "required": ["pattern"],
    },
    "strict": True,
}

AST_GREP_REWRITE: ToolParam = {
    "type": "function",
    "name": "ast_grep_run_rewrite",
    "description": "Rewrite code structurally with ast-grep",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "AST pattern to match",
            },
            "rewrite": {
                "type": "string",
                "description": "Replacement template for the matched AST node",
            },
            "lang": {
                "type": "string",
                "description": "Language of the pattern (e.g., ts, py, rust, go)",
            },
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files or directories to apply the rewrite",
            },
            "update_all": {
                "type": "boolean",
                "description": "Apply all rewrites without confirmation (-U)",
            },
        },
        "required": ["pattern", "rewrite"],
    },
    "strict": True,
}


client.responses.create(
    model="grok-code-fast-1",
    instructions="",
    tools=[SPAWN_SUBAGENT],
)
