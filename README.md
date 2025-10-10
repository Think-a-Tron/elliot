# Elliot — Coding Agents Orchestrator

A minimal Python 3.12 CLI that orchestrates task‑focused coding agents and safely grants them a small toolbox (ast-grep, file peek, and guarded in‑place edits).

## Highlights
- Spawn scoped sub‑agents with explicit tools and turn budgets
- Structural code search/rewrites via ast‑grep
- Read‑only helpers: list files, head, tail
- Guarded edits with confirmation prompts

## Requirements
- Python 3.12+
- Optional: uv (recommended)
- Environment: set OPENAI_API_KEY (and optionally OPENAI_BASE_URL)

## Install
- Using uv:
  - uv sync
- Using pip (venv recommended):
  - python -m venv .venv && source .venv/bin/activate
  - pip install ast-grep-cli openai openai-agents rich

## Run
- Provide a task directly:
  - uv run python main.py "Your task"
  - python main.py "Your task"
- Control the turn budget:
  - python main.py --max-turns 60 "Refactor duplicated code using ast-grep"
- Interactive mode (no task arg):
  - python main.py

## Configuration
- export OPENAI_API_KEY="your-key"
- Optional:
  - export OPENAI_BASE_URL="https://api.x.ai/v1"

## Built‑in tools
- ast_grep_run_search, ast_grep_run_rewrite
- list_directory, head, tail
- sed_write
- spawn_subagent (to create focused helpers)

## Notes
- Requires the ast-grep CLI (installed via ast-grep-cli)
- Default model: gpt-5 (see main.py)
- License: MIT
- Author: ExpressGradient
