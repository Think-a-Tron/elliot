import argparse
from os import environ
from pathlib import Path
from typing import Literal, TypedDict, List

from langgraph.graph import END, START, StateGraph
from openai import OpenAI
from pydantic import BaseModel, Field
from rich import print
from rich.markdown import Markdown
from rich.panel import Panel

MODEL_NAME = environ.get("MODEL_NAME", "mistralai/mistral-medium-3.1")
BASE_URL = environ.get("BASE_URL", "https://openrouter.ai/api/v1")

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
            title="Issue Understanding",
            subtitle=f"Tokens {total_tokens}",
            border_style="blue",
        )
    )

    return {"understanding": completion.choices[0].message.content}


class CoverageResponse(BaseModel):
    decision: Literal["more_context_needed", "enough_context"] = Field(
        default="more_context_needed"
    )
    feedback: List[str] = Field(description="List of search items to scout for")


def context_coverage(state: State):
    understanding = state.get("understanding")
    context = state.get("context", "none")

    completion = client.chat.completions.parse(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": "Given an understanding of a GitHub issue,"
                "check if we have enough information/context about the codebase to plan for this issue. "
                "Give feedback of what else we need from the repo, if current context isn't enough. "
                "Feedback should be a list of targeted search items and their justifications."
                f"Issue Understanding: {understanding}\n\n"
                f"Current Context about the Code: {context}",
            }
        ],
        response_format=CoverageResponse,
    )

    coverage = completion.choices[0].message.parsed
    total_tokens = completion.usage.total_tokens if completion.usage else 0

    if isinstance(coverage, CoverageResponse):
        if coverage.decision == "more_context_needed":
            print(
                Panel(
                    Markdown("\n".join(f"- {item}" for item in coverage.feedback)),
                    title="Context Coverage",
                    subtitle=f"Tokens {total_tokens}",
                    border_style="yellow",
                )
            )

            return {"feedback_to_scout": coverage.feedback}

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
