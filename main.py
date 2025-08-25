import argparse
import json
from os import environ
from pathlib import Path
from typing import List, TypedDict

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

MODEL_NAME = environ.get("MODEL_NAME", "z-ai/glm-4.5")
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
    context = state.get("context") or []

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Given an understanding of a GitHub issue, "
                    "check if we have enough information/context from the current codebase itself "
                    "to plan for this issue. "
                    "If the context is enough, just decide 'enough_context'. "
                    "If the current context isn't enough, give feedback as a list of <5 "
                    "targeted, detailed, and atomic code searches within the repo (e.g. specific files, "
                    "functions, classes, or tests). "
                    "Do not request or suggest external sources such as RFCs, PRs, issue pages, "
                    "or git commit history. Stay strictly within the present codebase snapshot.\n"
                    f"Issue Understanding: {issue_understanding}\n\n"
                    f"Current Context about the Code: {chr(10) + chr(10).join(context)}"
                ),
            }
        ],
        "reasoning": {"enabled": True if MODEL_NAME == "openai/gpt-5" else False},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "coverage_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "decision": {
                            "type": "string",
                            "enum": ["more_context_needed", "enough_context"],
                            "description": "Decision about whether more context is needed or not",
                        },
                        "feedback": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of search items to scout for",
                        },
                    },
                    "required": ["decision", "feedback"],
                    "additionalProperties": False,
                },
            },
        },
    }

    response = requests.post(BASE_URL, headers=HEADERS, data=json.dumps(payload))
    completion = response.json()

    coverage = json.loads(completion["choices"][0]["message"]["content"])
    total_tokens = completion["usage"]["total_tokens"]

    if coverage["decision"] == "more_context_needed":
        console.print(
            Panel(
                Markdown("\n".join(f"- {item}" for item in coverage["feedback"])),
                title="Context Coverage",
                subtitle=f"Tokens {total_tokens}",
                border_style="yellow",
            )
        )

        return {"feedback_to_scout": coverage["feedback"]}

    return {"feedback_to_scout": []}


def scout(state: State, runtime: Runtime[ContextSchema]):
    feedback_items = state.get("feedback_to_scout")

    if len(feedback_items) == 0:
        return Command(goto=END)

    context = state.get("context") or []
    item_contexts = []

    for item in feedback_items:
        console.print(Panel(Text(item), title="Gathering Context", border_style="blue"))

        item_context = ""

        messages = [
            {
                "role": "user",
                "content": "You are a code scout with access to "
                "ripgrep and sed to gather context to work on GitHub issues. "
                "When you have gathered enough context about asked item, call finish with context.\n"
                f"Gather detailed code context about {item}",
            }
        ]

        while item_context == "":
            payload = {
                "model": MODEL_NAME,
                "messages": messages,
                "tools": [rg_spec, sed_spec, finish_spec],
                "reasoning": {
                    "enabled": True if MODEL_NAME == "openai/gpt-5" else False
                },
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

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": "Pack the following individual context items about "
                "a code issue into a single concise context report. "
                "Don't oversummarize and miss information. \n"
                f"{(chr(10) + '-----' + chr(10)).join(item_contexts)}",
            }
        ],
        "reasoning": {"enabled": True},
    }

    response = requests.post(BASE_URL, headers=HEADERS, data=json.dumps(payload))
    completion = response.json()
    context.append(completion["choices"][0]["message"]["content"])

    console.print(
        Panel(
            Markdown(context[-1]),
            title="Packed Context",
            subtitle=f"Tokens {completion['usage']['total_tokens']}",
            border_style="blue",
        )
    )

    return Command(update={"context": context}, goto="context_coverage")


builder = StateGraph(State, input_schema=InputState, context_schema=ContextSchema)
builder.add_node(create_understanding)
builder.add_node(context_coverage)
builder.add_node(scout)

builder.add_edge(START, "create_understanding")
builder.add_edge("create_understanding", "context_coverage")
builder.add_edge("context_coverage", "scout")

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
