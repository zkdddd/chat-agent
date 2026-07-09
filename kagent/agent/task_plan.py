from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


PlanStatus = Literal["pending", "active", "done", "skipped", "failed"]


@dataclass
class PlanStep:
    step_id: str
    title: str
    status: PlanStatus = "pending"
    detail: str | None = None


def build_task_plan(
    user_task: str,
    *,
    requires_tools: bool,
    requires_code_edit: bool,
) -> list[PlanStep]:
    steps = [
        PlanStep("understand_task", "Understand the user request", "done"),
    ]
    if requires_tools:
        steps.append(PlanStep("inspect_context", "Inspect relevant project context", "active"))
    if requires_code_edit:
        steps.append(PlanStep("make_changes", "Make the required workspace changes"))
        steps.append(PlanStep("validate_changes", "Validate changed code"))
    steps.append(PlanStep("final_answer", "Summarize outcome for the user"))

    if not requires_tools and len(steps) > 1:
        steps[1].status = "active"
    return steps


def set_plan_step(
    steps: list[PlanStep],
    step_id: str,
    status: PlanStatus,
    detail: str | None = None,
) -> bool:
    for step in steps:
        if step.step_id != step_id:
            continue
        changed = step.status != status or step.detail != detail
        step.status = status
        if detail is not None or changed:
            step.detail = detail
        return changed
    return False


def plan_to_dicts(steps: list[PlanStep]) -> list[dict[str, str | None]]:
    return [
        {
            "id": step.step_id,
            "title": step.title,
            "status": step.status,
            "detail": step.detail,
        }
        for step in steps
    ]


def plan_for_model(steps: list[PlanStep]) -> str:
    lines = ["Execution checklist:"]
    for step in steps:
        detail = f" - {step.detail}" if step.detail else ""
        lines.append(f"- [{step.status}] {step.step_id}: {step.title}{detail}")
    lines.append(
        "Use this checklist to stay on track. Update your behavior based on completed, failed, or pending steps."
    )
    return "\n".join(lines)


def plan_summary_text(steps: list[PlanStep]) -> str:
    return "; ".join(f"{step.step_id}={step.status}" for step in steps)
