"""Plan management helpers exposed as Elliot tools."""

from __future__ import annotations

from itertools import count
from typing import Any, Dict, List, Optional

from agents import function_tool

from .output import log_markdown, log_tool_event

PLAN_STATUS_MARKERS = {
    "pending": "[ ]",
    "in_progress": "[~]",
    "completed": "[x]",
    "blocked": "[!]",
}
CURRENT_PLAN: List[Dict[str, Any]] = []
PLAN_ID_COUNTER = count(1)


def _render_plan() -> None:
    """Display the current plan using markdown checkboxes."""

    if not CURRENT_PLAN:
        log_markdown("**[elliot][plan]** *(plan is empty)*")
        return

    lines = ["**[elliot][plan]** current plan", ""]
    for item in CURRENT_PLAN:
        marker = PLAN_STATUS_MARKERS.get(item["status"], "[?]")
        last_reason = item["history"][-1]["reason"] if item["history"] else ""
        reason_suffix = f" — {last_reason}" if last_reason else ""
        lines.append(
            f"- {marker} **#{item['id']}** {item['title']} "
            f"(`{item['status']}`){reason_suffix}"
        )

    log_markdown("\n".join(lines))


@function_tool
def plan_manager(
    action: str,
    title: Optional[str] = None,
    item_id: Optional[int] = None,
    status: Optional[str] = None,
    reason: Optional[str] = None,
) -> str:
    """Manage Elliot's working plan. Supports CRUD operations with rich rendering."""

    params = {
        "action": action,
        "title": title,
        "item_id": item_id,
        "status": status,
        "reason": reason,
    }
    outcome = "success"
    detail: Optional[str] = None
    response_message = ""

    allowed_statuses = set(PLAN_STATUS_MARKERS.keys())

    def _normalize_id(raw_id: Optional[int]) -> int:
        if raw_id is None:
            raise ValueError("item_id is required for this action")
        if isinstance(raw_id, str):
            if not raw_id.isdigit():
                raise ValueError("item_id must be an integer")
            return int(raw_id)
        if isinstance(raw_id, int):
            return raw_id
        raise ValueError("item_id must be an integer")

    try:
        normalized_action = (action or "").strip().lower()
        if not normalized_action:
            raise ValueError("action is required")

        if status:
            status_value = status.strip().lower()
            if status_value not in allowed_statuses:
                raise ValueError(
                    f"invalid status '{status_value}'. "
                    f"Valid options: {', '.join(sorted(allowed_statuses))}"
                )
        else:
            status_value = None

        if normalized_action == "reset":
            CURRENT_PLAN.clear()
            response_message = "plan cleared."
        elif normalized_action == "add":
            if not title:
                raise ValueError("title is required to add a plan item")
            new_id = next(PLAN_ID_COUNTER)
            item = {
                "id": new_id,
                "title": title,
                "status": status_value or "pending",
                "history": [],
            }
            if reason:
                item["history"].append(
                    {"status": item["status"], "reason": reason.strip()}
                )
            CURRENT_PLAN.append(item)
            response_message = f"added plan item #{new_id}."
        elif normalized_action == "update":
            target_id = _normalize_id(item_id)
            if reason is None or not reason.strip():
                raise ValueError("reason is required when updating a plan item")
            for item in CURRENT_PLAN:
                if item["id"] == target_id:
                    if title:
                        item["title"] = title
                    if status_value:
                        item["status"] = status_value
                    item["history"].append(
                        {"status": item["status"], "reason": reason.strip()}
                    )
                    break
            else:
                raise ValueError(f"plan item #{target_id} not found")
            response_message = f"updated plan item #{target_id}."
        elif normalized_action == "remove":
            target_id = _normalize_id(item_id)
            for index, existing in enumerate(CURRENT_PLAN):
                if existing["id"] == target_id:
                    CURRENT_PLAN.pop(index)
                    response_message = f"removed plan item #{target_id}."
                    break
            else:
                raise ValueError(f"plan item #{target_id} not found")
        elif normalized_action == "show":
            response_message = "displayed current plan."
        else:
            raise ValueError(
                "invalid action. use one of: reset, add, update, remove, show."
            )

        _render_plan()
        detail = response_message
        response_message = f"[elliot][tool plan_manager] {response_message}"
    except Exception as error:  # pragma: no cover - defensive logging
        outcome = "error"
        detail = str(error)
        response_message = f"[elliot][tool plan_manager] error: {error}"
    finally:
        log_tool_event("plan_manager", outcome, params, detail)

    return response_message
