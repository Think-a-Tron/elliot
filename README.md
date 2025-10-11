Elliot — Orchestrator Agent CLI

Elliot is a small, focused command‑line orchestrator that manages a working plan and spawns specialist sub‑agents with only the tools they need. It logs plans and tool activity as readable Markdown in your terminal and returns a concise final outcome.

Highlights
- Clear plans: Elliot tracks a checklist of steps with statuses (pending, in_progress, completed, blocked).
- Sub‑agents with least‑privilege: each helper gets only the specific tools it needs and a turn budget.
- Powerful code/search tooling: ast‑grep search and safe rewrites, targeted file slicing and tailing, directory listing, and guarded edits.
- Guardrails for writes: any operation that changes files or runs git prompts for confirmation and shows previews/diffs first.

How it works (at a glance)
- Top‑level Elliot has two tools:
  - plan_manager: maintain a visible working plan (add/update/remove/show; statuses include pending, in_progress, completed, blocked).
  - spawn_subagent: spin up a focused helper with a custom instruction set, a limited toolset, and a max turn budget.
- Sub‑agents can be granted any of these tool keys (user‑facing names), mapped to underlying functions:
  - code_search → ast_grep_run_search
  - code_rewrite → ast_grep_run_rewrite
  - list_dir → list_directory
  - file_slice → read_slice
  - file_tail → tail
  - sed_edit → sed_write
  - git_command → git_run

Requirements
- Python: 3.12+
- Python packages: ast-grep-cli, openai, openai-agents, rich
- System executables on PATH: ast-grep, sed, tail, git
  - Note: sed and tail are standard on macOS/Linux. Windows users may need WSL or compatible tools.
- Environment:
  - OPENAI_API_KEY (required)
  - OPENAI_BASE_URL (optional; e.g., https://api.x.ai/v1)

Install
- With uv (recommended for exact locks):
  - uv sync
- Or with pip:
  - pip install ast-grep-cli openai openai-agents rich

Quick start
- Provide a task directly:
  - python main.py "Update the README to reflect the current tools"
- Increase the turn budget:
  - python main.py --max-turns 60 "Refactor the utils module"
- Interactive (will prompt for a task if omitted):
  - python main.py

What you’ll see
- A Markdown-rendered plan with checklist items and status updates.
- Tool call logs (parameters, results, confirmations) from Elliot and any spawned sub‑agents.
- A concise final output summarizing what was done and any next steps.

Tooling details
- Plan management
  - plan_manager(action, title?, item_id?, status?, reason?)
  - Actions: reset, add, update, remove, show
  - Statuses: pending, in_progress, completed, blocked
  - Updates require a reason; history is recorded.
- Sub‑agent tools (grant by key)
  - code_search: search code via ast-grep with patterns/globs.
  - code_rewrite: apply ast-grep structured rewrites (prompts before writing).
  - list_dir: list directory contents (optionally include hidden files).
  - file_slice: read arbitrary line ranges from a file.
  - file_tail: tail N lines from a file.
  - sed_edit: run sed to edit files; shows a unified diff and asks for confirmation.
  - git_command: run git commands (e.g., add/commit/push); asks for confirmation.
- Write safeguards
  - ast-grep rewrites, sed edits, and git commands all request interactive confirmation and preview output before proceeding.

Configuration notes
- Model is fixed in code to "gpt-5".
- Set OPENAI_API_KEY in your environment; optionally set OPENAI_BASE_URL to point to compatible endpoints.
- All subprocesses set NO_COLOR=1 to keep output parseable in logs.

Platform notes
- Ensure ast-grep, sed, tail, and git are available on your PATH.
- On Windows, consider using WSL or Git Bash for Unix utilities.

Security
- Do not commit secrets. Use environment variables or a .env file managed outside of version control. If you maintain example env files, use placeholders (e.g., YOUR_API_KEY_HERE) rather than real keys.

License
- MIT
