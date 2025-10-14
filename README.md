# Elliot — Orchestrator for Specialist Coding Agents

## Overview
Elliot is a Python package and CLI that orchestrates a team of specialist coding agents powered by [`openai-agents`](https://github.com/openai/openai-agents). It produces rich Markdown output in the terminal, builds and maintains project plans, and dispatches focused helper agents with a curated toolbelt for code search, editing, linting, git operations, and more.

Elliot targets Python 3.12+, runs entirely locally, and only requires network access to the OpenAI-compatible endpoint you configure.

## Key Capabilities
- **Collaborative planning** — maintains a live task plan and surfaces updates in-line.
- **Sub-agent delegation** — spawns helper agents with scoped instructions and tools.
- **Tooling safeguards** — confirms before performing write operations or running external commands.
- **Markdown-first logs** — readable console output powered by `rich`.
- **Extensible package layout** — core pieces live in the `elliot/` package (`agent`, `plan`, `tools`, `cli`, `output`) with a thin compatibility `main.py`.

## Installation & Execution

### Quick one-off run (no checkout required)
```bash
uvx --from git+https://github.com/Think-a-Tron/elliot.git elliot "help me refactor foo.py"
```
`uvx` builds a temporary environment, runs Elliot, then cleans up.

### Install from Git
```bash
uv pip install git+https://github.com/Think-a-Tron/elliot.git
uv run elliot "document the API"
```
You can swap `uv pip` for `pip install` or `pipx install` if you prefer other tooling.

### Local development workflow
```bash
git clone https://github.com/Think-a-Tron/elliot.git
cd elliot
uv sync                       # create .venv and install deps
uv run -- python -m elliot "hello there"
# optional: expose console script inside venv
uv pip install -e .
uv run elliot "summarize the repo"
```
Stick with `uv run -- python -m elliot ...` if you do not want to install the package locally.

## Configuration
Set environment variables before invoking Elliot:

- `OPENAI_API_KEY` (required): API key for the OpenAI-compatible provider.
- `OPENAI_BASE_URL` (optional): override to target a different host (e.g., Azure, local gateway).
- `OPENAI_DEFAULT_MODEL` (optional): model identifier; defaults to `gpt-5`.

Example `.env` snippet:
```bash
export OPENAI_API_KEY="sk-***"
# export OPENAI_BASE_URL="https://api.your-provider.tld/v1"
# export OPENAI_DEFAULT_MODEL="gpt-4o"
```

## CLI Usage
```bash
elliot "write release notes for v1.2"
# or with module invocation:
python -m elliot.cli --max-turns 40 "add async support"
```
If you omit the task argument, Elliot prompts for input interactively. Adjust `--max-turns` to cap the orchestrator’s conversation length.

## Tool Reference
Sub-agents can access a curated toolset:

- `code_search` — structural code search via `ast-grep`.
- `code_rewrite` — structural rewrites with `ast-grep`.
- `list_dir` — directory listings (with optional hidden files).
- `file_tail` — the last *N* lines of a file.
- `read_slice` — file slices via `sed`.
- `sed_inplace_edit` — previewable `sed` edits (writes after confirmation).
- `git_command` — `git` invocations with confirmation.
- `python_run` — execute Python snippets in a subprocess.
- `ruff_check` / `ruff_format` — lint or format using Ruff.
- `ask_user` — request clarification from the human operator.
- `ask_expert` — get concise design/implementation guidance via the OpenAI Responses API.

Every tool logs inputs/outputs in Markdown and confirms before mutating files or running arbitrary commands.

## License
MIT License — see `LICENSE` for details.
