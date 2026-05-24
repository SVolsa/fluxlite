"""Task planner + self-review tools for structured AI workflows.

Forces the AI to explicitly plan before executing and review after
completing, reducing rework on complex tasks.
"""

import uuid
import json
from datetime import datetime

_plans: dict[str, dict] = {}


def task_planner_handler(goal: str = "", steps: str = "", context: str = "") -> str:
    if not goal:
        return "Please provide a goal for the plan."

    if not steps:
        return (
            "Please provide steps for the plan, one per line. Example:\n"
            "1. Create the project structure\n"
            "2. Implement the core logic\n"
            "3. Write tests"
        )

    pid = f"plan_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:4]}"

    step_list = []
    for line in steps.split("\n"):
        line = line.strip()
        if not line:
            continue
        clean = line.lstrip("0123456789. )-* \t")
        if clean:
            step_list.append(clean)

    plan = {
        "id": pid,
        "goal": goal,
        "context": context,
        "steps": [{"desc": s, "status": "pending"} for s in step_list],
        "created_at": datetime.now().isoformat(),
    }
    _plans[pid] = plan

    lines = [
        f"=== Plan: {pid} ===",
        f"Goal: {goal}",
        "",
        "Steps:",
    ]
    for i, s in enumerate(plan["steps"]):
        lines.append(f"  [{i+1}] . {s['desc']}")
    lines.append("")
    lines.append("Call self_review when done to verify the result.")
    return "\n".join(lines)


def self_review_handler(
    plan_id: str = "",
    result_summary: str = "",
    completed_steps: str = "",
) -> str:
    if not plan_id:
        return "Please provide the plan_id from task_planner."

    lines = [
        "=== Self Review ===",
        f"Plan: {plan_id}",
        "",
    ]

    if plan_id in _plans:
        plan = _plans[plan_id]
        lines.append(f"Goal: {plan['goal']}")
        lines.append("")

        done_set = set()
        for part in completed_steps.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(plan["steps"]):
                    plan["steps"][idx]["status"] = "done"
                    done_set.add(idx)

        lines.append("Progress:")
        for i, s in enumerate(plan["steps"]):
            if s["status"] == "done":
                lines.append(f"  [x] Step {i+1}: {s['desc']}")
            else:
                lines.append(f"  [ ] Step {i+1}: {s['desc']}")
        lines.append("")
    else:
        lines.append(f"(Plan {plan_id} not found in working memory)")
        lines.append("")

    if result_summary:
        lines.append("Result:")
        lines.append(f"  {result_summary}")
        lines.append("")

    lines.append("Checklist:")
    lines.append("  [ ] Does the result match the original goal?")
    lines.append("  [ ] Are all edge cases handled?")
    lines.append("  [ ] Is the code/test quality acceptable?")
    lines.append("  [ ] Any regressions introduced?")
    lines.append("  [ ] Is there anything missed?")
    lines.append("")
    lines.append("Reply with Pass or mark specific items as Fail to trigger rework.")

    return "\n".join(lines)
