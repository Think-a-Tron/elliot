import argparse
from os import environ
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from openai import OpenAI
from rich import print
from rich.markdown import Markdown
from rich.panel import Panel

from tools import ripgrep_spec

MODEL_NAME = environ.get("MODEL_NAME", "openai/gpt-oss-120b")
BASE_URL = environ.get("BASE_URL", "https://openrouter.ai/api/v1")

client = OpenAI(base_url=BASE_URL)


class InputState(TypedDict):
    issue: str
    repo_path: str


class State(TypedDict):
    understanding: str


def create_understanding(state: InputState):
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": f"""
You are analyzing a GitHub issue.

Issue:
{state["issue"]}

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
    )

    understanding = str(completion.choices[0].message.content)
    total_tokens = completion.usage.total_tokens if completion.usage else 0

    print(
        Panel(
            Markdown(understanding),
            title="Understanding",
            subtitle=f"Tokens {total_tokens}",
            border_style="blue",
        )
    )

    return {"understanding": completion.choices[0].message.content}


def create_code_scan_actions(state: State):
    client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": ""}],
        tools=[ripgrep_spec],
    )


builder = StateGraph(State, input_schema=InputState)
builder.add_node(create_understanding)

builder.add_edge(START, "create_understanding")
builder.add_edge("create_understanding", END)

graph = builder.compile()


def main():
    parser = argparse.ArgumentParser(description="`elliot` a Simple Coder")
    parser.add_argument("issue_file", type=str, help="Issue File")
    parser.add_argument("--repo", type=Path, default=Path("."), help="Path to Repo")
    args = parser.parse_args()

    with open(args.issue_file) as file:
        issue = file.read()

    graph.invoke({"issue": issue, "repo_path": str(args.repo.resolve())})


if __name__ == "__main__":
    main()
