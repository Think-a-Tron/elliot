from typing import TypedDict
from os import environ

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

model = ChatOpenAI(
    model=environ.get("MODEL_NAME", "gpt-oss-120b"),
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
            "- Summary: one sentence summary.\n"
            "- Goals: 2-5 concrete goals.\n"
            "- Constraints: tech, env, performance, security, or deadlines.\n"
            "- Assumptions: any inferred context.\n"
            "- Risks/Unknowns: questions to resolve.\n"
            "- Next Steps: 3-6 actionable steps.\n\n"
            f"Issue: {state['problem']}"
        )
    )
    return {"problem_understanding": str(response.content)}


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
    return {"checkout_branch": str(response.content)}


builder = StateGraph(State, input_schema=InputState)
builder.add_node("understand_problem", understand_problem)
builder.add_node("checkout_branch", checkout_branch)

builder.add_edge(START, "understand_problem")
builder.add_edge(START, "checkout")
builder.add_edge("checkout", END)
builder.add_edge("understand_problem", END)

graph = builder.compile()
