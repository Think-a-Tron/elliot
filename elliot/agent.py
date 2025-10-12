"""Core agent orchestration helpers for Elliot."""

from __future__ import annotations

import os
from typing import Optional

from agents import Agent, Runner, function_tool, set_tracing_disabled
from rich.markdown import Markdown

from .output import console, log_markdown, log_tool_event
from .plan import plan_manager
from .tools import SUBAGENT_TOOLS, SUBAGENT_TOOL_NAMES

set_tracing_disabled(True)
MODEL = os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-5")


@function_tool
async def spawn_subagent(
    name: str, instructions: str, task: str, tools: list[str], max_turns: int
) -> str:
    """Spin up a focused helper agent with a constrained toolset."""

    unknown_tools = [tool for tool in tools if tool not in SUBAGENT_TOOLS]

    if unknown_tools:
        raise ValueError(
            f"Unknown tool(s): {', '.join(unknown_tools)}. "
            f"Available tools: {', '.join(sorted(SUBAGENT_TOOLS))}"
        )

    subagent = Agent(
        name=name,
        instructions=instructions,
        model=MODEL,
        tools=[SUBAGENT_TOOLS[tool] for tool in tools],
    )
    params = {
        "name": name,
        "tools": tools or [],
        "max_turns": max_turns,
    }
    status = "success"
    detail: Optional[str] = None
    final_output = ""

    tool_list = ", ".join(tools) if tools else "none"
    log_markdown(
        "\n".join(
            [
                f"**[elliot]** spawning sub-agent `{name}`",
                f"tools: {tool_list}",
                f"max_turns: {max_turns}",
            ]
        )
    )

    try:
        result = await Runner.run(subagent, task, max_turns=max_turns)
        final_output = result.final_output
        detail = "sub-agent completed successfully"
    except Exception as error:  # pragma: no cover - defensive logging
        status = "error"
        detail = f"sub-agent failed: {error}"
        raise
    finally:
        log_tool_event("spawn_subagent", status, params, detail)

    if final_output:
        console.print(Markdown(final_output))

    return final_output


ELLIOT_INSTRUCTIONS = (
    "You are Elliot, the orchestrator agent for a team of specialist coding agents.\n"
    "Your responsibilities:\n"
    "- Understand the user's goal, clarify missing information, and structure the work.\n"
    "- Gather the necessary context before proposing plans or delegating: inspect prior outputs, review relevant files, and run read commands when helpful. Note what you learned.\n"
    "- For any multi-step effort, draft a concise plan up front and keep it updated as sub-tasks complete.\n"
    "- Maintain that plan with the `plan_manager` tool: add, update (with reasons), remove, or show steps so progress stays transparent.\n"
    "- Break the goal into concrete sub-tasks when it adds value. Keep tasks focused and deliverable-based.\n"
    "- For each sub-task, spawn a sub-agent with clear instructions, additional context, success criteria, relevant constraints, and only the tools the agent needs. "
    f"The allowed tool names are: {SUBAGENT_TOOL_NAMES}.\n"
    "- Configure max_turns thoughtfully based on task complexity. Default to 30 top-level turns, increasing when the plan predicts longer work.\n"
    "- When a task is tiny or purely explanatory, you may answer directly without spawning a subagent.\n"
    "- Whenever practical, validate deliverables (e.g., run tests, lint, or dry-run tools). If validation is impossible, call out the gap explicitly.\n"
    "- Integrate sub-agent outputs into a cohesive final response that resolves the user's original request.\n"
    "- Highlight follow-up work, risks, or outstanding questions in the final response when they exist.\n"
    "- Escalate uncertainties back to the user instead of guessing.\n"
    "- Track dependencies between tasks and run them sequentially if required.\n"
    "- Be deliberate: summarize the relevant context you collected, explain how each subagent's output fits the plan, and keep the narrative easy to follow.\n"
    "- Close with a concise summary of outcomes and next steps if they exist."
)


def create_elliot_agent() -> Agent:
    """Build the main Elliot agent configured to orchestrate sub-agents."""

    return Agent(
        name="Elliot",
        instructions=ELLIOT_INSTRUCTIONS,
        model=MODEL,
        tools=[plan_manager, spawn_subagent],
    )


def run_elliot(task: str, max_turns: int = 30) -> str:
    """Execute the Elliot agent against the provided task."""

    elliot_agent = create_elliot_agent()
    result = Runner.run_sync(elliot_agent, task, max_turns=max_turns)
    return result.final_output
