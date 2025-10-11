# Elliot — Orchestrator for Specialist Coding Agents

## Overview
Elliot is a Python CLI that orchestrates specialist coding agents using the openai-agents library. It runs locally with rich Markdown console output, coordinates sub-agents for focused tasks, and exposes tools for structural code search/edits, filesystem inspection, and git operations. Elliot requires access to an OpenAI‑compatible API (OpenAI, or another provider via OPENAI_BASE_URL).

## Features
- Orchestrator agent that plans work and delegates to sub-agents
- Sub-agent toolset for code search, rewrites, file ops, and git
- Model/provider agnostic via OPENAI_BASE_URL
- Rich, readable Markdown logging in the terminal
- Interactive safety confirmations before write/edit operations
- Simple CLI workflow; no server to run

## Prerequisites
- Python 3.12+
- uv recommended for environment and dependency management
- External utilities (used by some tools):
  - ast-grep (installed via the ast-grep-cli Python wheel)
  - sed and tail (for file slicing/edits)
  - git (for repository operations)

## Installation

### Preferred: uv
- Create and activate a virtual environment:
  - uv venv
- Install dependencies from pyproject.toml:
  - uv sync
- Run:
  - uv run python main.py "your task here"

### Alternative: pip + venv
- Create and activate a virtual environment:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venvScriptsactivate)
- Install dependencies:
  - pip install ast-grep-cli>=0.39.5 openai>=2.0.0 openai-agents>=0.1.0 rich>=14.2.0
- Run:
  - python main.py "your task here"

## Configuration
Elliot reads configuration from environment variables:
- OPENAI_API_KEY (required) — API key for an OpenAI‑compatible API.
- OPENAI_BASE_URL (optional) — Base URL to target a non-OpenAI provider.
- MODEL_NAME (optional) — Model to use; defaults to "gpt-5" in code.

Minimal .env.example:
```
# Required: set to your API key
OPENAI_API_KEY=

# Optional: point to a compatible provider (e.g., x.ai, local gateway)
# OPENAI_BASE_URL=https://api.your-provider.tld/v1

# Optional: model name (default: gpt-5). Set to a model your provider supports.
# MODEL_NAME=
```

## Usage
- Basic:
  - python main.py "your task here" [--max-turns N]
- If you omit the task, Elliot will prompt interactively in the terminal.
- Elliot is a CLI, not a server.

Built-in sub-agent tools:
- code_search — structural search via ast-grep
- code_rewrite — structural rewrite via ast-grep
- list_dir — list directory contents
- file_tail — show last N lines of a file
- read_slice — read a file slice via sed
- sed_inplace_edit — preview+apply sed-based edits with confirmation
- git_command — run git commands with confirmation
- ask_user — prompt the human for input with an optional default

## Project structure
- main.py — CLI entry point; orchestrator, tools, and agent setup
- pyproject.toml — project metadata and dependencies
- uv.lock — lockfile for uv
- LICENSE — MIT License
- README.md — this document
- .python-version — pinned Python version for tooling
- .gitignore — standard Git ignores

## Testing & quality
No tests or linters are configured yet. Consider adding:
- pytest for unit tests
- ruff/black for linting/formatting
- pre-commit hooks to standardize checks

## Security
Important: a live API key is committed in env.sh.

- File: env.sh
- Variable: OPENAI_API_KEY

Immediate remediation steps:
1) Revoke/rotate the exposed API key in your provider dashboard now.
2) Remove the file from version control:
   - git rm --cached env.sh
   - Add a proper .env.example (do not commit secrets).
3) Add env.sh (and .env) to .gitignore to prevent future commits.
4) If this repository is public or has been shared, rewrite history to purge the secret:
   - Use git filter-repo (recommended) or the BFG Repo-Cleaner.
   - Force-push only if necessary and after rotating the key.
5) Audit usage logs with your provider to detect any misuse.

Never commit real secrets. Use environment variables or a local .env file excluded from Git.

## License
MIT License. See LICENSE.

## Acknowledgements/Notes
- The default MODEL_NAME is "gpt-5", which may not exist on all providers. Set MODEL_NAME and (if needed) OPENAI_BASE_URL to match a supported model on your chosen provider.
