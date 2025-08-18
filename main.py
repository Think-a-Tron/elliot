from os import environ
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

model = ChatOpenAI(
    model=environ.get("MODEL_NAME", "openai/gpt-oss-120b"),
    base_url=environ.get("BASE_URL", "https://openrouter.ai/api/v1"),
)


class InputState(TypedDict):
    problem: str


class State(TypedDict):
    checkout_branch: str
    problem_understanding: str


def understand_problem(state: InputState):
    response = model.invoke(
        (
            "You are a senior engineer helping clarify a coding task.\n"
            "Understand and expand the given issue and produce a concise, structured brief.\n\n"
            "Output format (use short bullets, no markdown headers):\n"
            "- Restatement: rewrite the problem in your own words.\n"
            "- Goals: 2-5 concrete goals.\n"
            "- Assumptions: any inferred context.\n"
            "- Risks/Unknowns: questions to resolve.\n\n"
            f"Issue: {state['problem']}"
        )
    )
    return {"problem_understanding": response.text()}


def checkout_branch(state: InputState):
    response = model.invoke(
        (
            "Generate a Git branch name for addressing this issue.\n"
            "Rules:\n"
            "- Use a suitable prefix: fix/, feat/, chore/, docs/, or refactor/.\n"
            "- Use lowercase kebab-case words (a-z, 0-9, -).\n"
            "- 3-6 short words that capture the task.\n"
            "- Max 40 characters total.\n"
            "- Return ONLY the branch name (no quotes, code fences, or extra text).\n\n"
            f"Issue: {state['problem']}"
        )
    )
    return {"checkout_branch": response.text()}


builder = StateGraph(State, input_schema=InputState)
builder.add_node("understand_problem", understand_problem)
builder.add_node("checkout_branch", checkout_branch)

builder.add_edge(START, "understand_problem")
builder.add_edge(START, "checkout_branch")
builder.add_edge("checkout_branch", END)
builder.add_edge("understand_problem", END)

graph = builder.compile()
