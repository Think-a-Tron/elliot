import argparse
import json
from os import environ
from pathlib import Path
from typing import Any, Dict, List, TypedDict

import requests
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from tools import finish_spec, rg, rg_spec, sed, sed_spec

MODEL_NAME = environ.get("MODEL_NAME", "openai/gpt-5")
BASE_URL = environ.get("BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
API_KEY = environ.get("OPENAI_API_KEY", "")
HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

client = OpenAI(base_url=BASE_URL)


class InputState(TypedDict):
    issue: str


class ContextSchema(TypedDict):
    repo_root: str


class State(TypedDict):
    issue_understanding: str
    context: List[str]
    feedback_to_scout: List[str]
    plan: Dict[str, Any]


console = Console()


def create_understanding(state: InputState):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": f"""
You are analyzing a GitHub issue.

Issue:
{state.get("issue")}

Task:
Create a clear, minimal but complete understanding of the issue.

Include:
- Restate the issue in plain terms (what it is really about).
- Clarify its type (bug, feature request, question, refactor, docs, etc.).
- Expand briefly on the implications or motivation behind it.
- If examples or code are given, explain what they show.
- List what is clear and what is missing/ambiguous.
- Describe what “solved” or "completed" would look like (the problem or request is precise and unambiguous).

Do not propose fixes or plans.
Keep it concise and technical, but make sure no important detail is lost.""",
            }
        ],
        "reasoning": {"enabled": True},
    }

    response = requests.post(BASE_URL, headers=HEADERS, data=json.dumps(payload))
    completion = response.json()

    issue_understanding = completion["choices"][0]["message"]["content"]
    total_tokens = completion["usage"]["total_tokens"]

    console.print(
        Panel(
            Markdown(issue_understanding),
            title="Issue Understanding",
            subtitle=f"Tokens {total_tokens}",
            border_style="cyan",
        )
    )

    return {"issue_understanding": issue_understanding}


def context_coverage(state: State):
    issue_understanding = state.get("issue_understanding")
    context = state.get("context")

    tools = [
        {
            "type": "function",
            "function": {
                "name": "analyze_context_coverage",
                "description": "Analyze if the current codebase context is sufficient for solving the GitHub issue"
                " and provide specific code searches if needed",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "has_sufficient_context": {
                            "type": "boolean",
                            "description": "Whether current context is sufficient for issue planning",
                        },
                        "required_searches": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 5,
                            "description": "Specific, detailed (2-3 lines), and atomic code searches needed within the repository "
                            "(empty array if context is sufficient). Focus on files, functions, classes, or tests - no external resources.",
                        },
                    },
                    "required": ["has_sufficient_context", "required_searches"],
                    "additionalProperties": False,
                },
            },
        }
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": f"""
Analyze this GitHub issue understanding to determine if we have sufficient codebase context for solving.

If context is insufficient, suggest relevant and specific code searches (each 2-3 lines).
Focus on files, functions, classes, or tests — no external resources.
Only provide as many searches as are truly useful (could be none, one, or several, but usually not more than five).

Issue Understanding:
{issue_understanding}

Context:
{(chr(10) + chr(10)).join(context) if context else "No context provided"}""",
            }
        ],
        "reasoning": {"enabled": True},
        "tools": tools,
        "tool_choice": "required",
    }

    response = requests.post(BASE_URL, headers=HEADERS, data=json.dumps(payload))
    completion = response.json()

    message = completion["choices"][0]["message"]
    tool_calls = message.get("tool_calls", [])

    if not tool_calls:
        print("No tool calls found in response")
        return {"feedback_to_scout": []}

    tool_call = tool_calls[0]
    function_args = json.loads(tool_call["function"]["arguments"])

    coverage = {
        "has_sufficient_context": function_args["has_sufficient_context"],
        "required_searches": function_args["required_searches"],
    }

    total_tokens = completion["usage"]["total_tokens"]

    if not coverage["has_sufficient_context"]:
        console.print(
            Panel(
                Markdown(
                    "\n".join(f"- {item}" for item in coverage["required_searches"])
                ),
                title="Context Coverage",
                subtitle=f"Tokens {total_tokens}",
                border_style="yellow",
            )
        )

        return {"feedback_to_scout": coverage["required_searches"]}

    return {"feedback_to_scout": []}


def scout(state: State, runtime: Runtime[ContextSchema]):
    feedback_items = state.get("feedback_to_scout")

    if len(feedback_items) == 0:
        return Command(goto="build_plan")

    context = state.get("context") or []
    item_contexts = []

    for item in feedback_items:
        console.print(Panel(Text(item), title="Gathering Context", border_style="blue"))

        item_context = ""

        messages = [
            {
                "role": "user",
                "content": "You are a code scout with access to ripgrep and sed tools to gather context "
                "for GitHub issues. When you have sufficient context about the requested "
                "item, call finish with the gathered context.\n\n"
                f"Gather detailed code context about: {item}",
            }
        ]

        while item_context == "":
            payload = {
                "model": MODEL_NAME,
                "messages": messages,
                "tools": [rg_spec, sed_spec, finish_spec],
                "reasoning": {"enabled": True},
                "tool_choice": "required",
            }

            response = requests.post(
                BASE_URL, headers=HEADERS, data=json.dumps(payload)
            )
            completion = response.json()
            messages.append(completion["choices"][0]["message"])

            if completion["choices"][0]["finish_reason"] == "tool_calls":
                for tool_call in completion["choices"][0]["message"]["tool_calls"]:
                    args = json.loads(tool_call["function"]["arguments"])

                    match tool_call["function"]["name"]:
                        case "rg":
                            try:
                                result = rg(args, runtime.context["repo_root"])
                            except Exception as e:
                                result = f"Error occured: {e}"
                        case "sed":
                            try:
                                result = sed(args, runtime.context["repo_root"])
                            except Exception as e:
                                result = f"Error occured: {e}"
                        case "finish":
                            item_context = args.get("answer")
                            result = item_context
                        case _:
                            result = ""

                    console.print(
                        Panel(
                            Text(result),
                            title="Tool Call",
                            border_style="magenta",
                        )
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result,
                        }
                    )

        item_contexts.append(item_context)

    context.extend(item_contexts)

    return Command(update={"context": context}, goto="context_coverage")


def build_plan(state: State):
    issue_understanding = state.get("issue_understanding")
    context = state.get("context")

    tools = [
        {
            "type": "function",
            "function": {
                "name": "emit_plan",
                "description": "Emit an ordered list of steps (each a string). "
                "Each step should be a single rg or sed command "
                "with a short rationale inline.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "List of steps, each like:\n"
                                "- SEARCH: rg --color never --line-number -n 'pattern' path  # rationale\n"
                                "- EDIT: sed -i 's/old/new/' file.py  # rationale"
                            ),
                        }
                    },
                    "required": ["steps"],
                },
            },
        }
    ]

    system_rules = """
You are a planner that outputs a series of shell commands for addressing a GitHub issue.

Constraints:
- Use ONLY rg (for searches) and sed (for edits).
- Each step = one command + inline comment rationale.
- Keep steps atomic and ordered.
- Use -n and -C N flags for rg to show line numbers/context.
- For sed: prefer narrow ranges or anchored substitutions; add comments explaining intent.
- Avoid vague repo-wide replacements unless you already narrowed with rg.
- Output only through the emit_plan tool.
"""

    user_prompt = f"""
Issue Understanding:
{issue_understanding}

Context (if any):
{(chr(10) + chr(10)).join(context)}

Task:
Write a clear, ordered plan of rg and sed commands to tackle the issue.
Each step should look like:

rg -n -C 2 "WidgetX" src/widgets/*.py   # locate class definition
sed -i '120,125s/timeout=10/timeout=30/' src/widgets/widget_x.py   # change default timeout

Be explicit and comprehensive.
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": user_prompt},
        ],
        "tools": tools,
        "tool_choice": "required",
        "reasoning": {"enabled": True},
    }

    response = requests.post(BASE_URL, headers=HEADERS, data=json.dumps(payload))
    completion = response.json()

    total_tokens = completion["usage"]["total_tokens"]

    tool_calls = completion["choices"][0]["message"]["tool_calls"]
    args = json.loads(tool_calls[0]["function"]["arguments"])
    steps = args["steps"]

    console.print(
        Panel(
            Markdown("\n".join(f"- {s}" for s in steps)),
            title="Work Plan",
            subtitle=f"Tokens {total_tokens}",
            border_style="green",
        )
    )

    return {"plan": {"steps": steps}}


builder = StateGraph(State, input_schema=InputState, context_schema=ContextSchema)
builder.add_node(create_understanding)
builder.add_node(context_coverage)
builder.add_node(scout)
builder.add_node(build_plan)


builder.add_edge(START, "create_understanding")
builder.add_edge("create_understanding", "context_coverage")
builder.add_edge("context_coverage", "scout")
builder.add_edge("build_plan", END)


graph = builder.compile()


def main():
    parser = argparse.ArgumentParser(description="`elliot` a Simple Coder")
    parser.add_argument("issue_file", type=str, help="Issue File")
    parser.add_argument("--repo", type=Path, default=Path("."), help="Path to Repo")
    args = parser.parse_args()

    with open(args.issue_file) as file:
        issue = file.read()

    graph.invoke({"issue": issue}, context={"repo_root": args.repo.resolve()})


if __name__ == "__main__":
    main()
