import argparse
import json
import requests
from os import environ
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from rich import print
from rich.markdown import Markdown
from rich.panel import Panel

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
    understanding: str
    context: str
    feedback_to_scout: str


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

    understanding = completion["choices"][0]["message"]["content"]
    total_tokens = completion["usage"]["total_tokens"]

    print(
        Panel(
            Markdown(understanding),
            title="Issue Understanding",
            subtitle=f"Tokens {total_tokens}",
            border_style="blue",
        )
    )

    return {"understanding": understanding}


def context_coverage(state: State):
    understanding = state.get("understanding")
    context = state.get("context", "none")

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Given an understanding of a GitHub issue, "
                    "check if we have enough information/context from the codebase itself "
                    "to plan for this issue. "
                    "If the current context isn't enough, give feedback as a list of "
                    "targeted code searches within the repo (e.g. specific files, "
                    "functions, classes, or tests) and their justifications. "
                    "Do not request external sources like RFCs, PRs, or issue pages. "
                    f"Issue Understanding: {understanding}\n\n"
                    f"Current Context about the Code: {context}"
                ),
            }
        ],
        "reasoning": {"enabled": True},
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
        print(
            Panel(
                Markdown("\n".join(f"- {item}" for item in coverage["feedback"])),
                title="Context Coverage",
                subtitle=f"Tokens {total_tokens}",
                border_style="yellow",
            )
        )

        return {"feedback_to_scout": coverage["feedback"]}

    return {"feedback_to_scout": []}


builder = StateGraph(State, input_schema=InputState, context_schema=ContextSchema)
builder.add_node(create_understanding)
builder.add_node(context_coverage)

builder.add_edge(START, "create_understanding")
builder.add_edge("create_understanding", "context_coverage")
builder.add_edge("context_coverage", END)

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
