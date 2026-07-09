from __future__ import annotations

import re
from typing import Any


def patch_failure_recovery(
    result: dict[str, Any],
    *,
    change_plan: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    error = str(result.get("error") or result.get("summary") or "")
    if not error.strip():
        return None
    paths = _paths_from_change_plan(change_plan)
    paths.extend(_paths_from_error(error))
    paths = _dedupe(paths)
    if not paths:
        return {
            "category": "patch_failed",
            "retryable": True,
            "next_step": (
                "Read the target file around the intended edit location, then generate a smaller patch "
                "with exact current context."
            ),
            "read_targets": [],
        }
    return {
        "category": "patch_failed",
        "retryable": True,
        "next_step": (
            "Read the listed target files, compare them with the failed patch context, then retry with a "
            "smaller patch that uses exact current lines."
        ),
        "read_targets": [
            {
                "path": path,
                "start_line": 1,
                "end_line": 220,
                "max_chars": 20000,
                "reason": "Refresh current file context after patch failure.",
            }
            for path in paths[:3]
        ],
    }


def patch_recovery_prompt(recovery: dict[str, Any] | None) -> str:
    if not recovery:
        return ""
    targets = recovery.get("read_targets") if isinstance(recovery.get("read_targets"), list) else []
    lines = [
        "The last apply_patch failed.",
        str(recovery.get("next_step") or "Retry with a smaller patch using exact current context."),
    ]
    if targets:
        lines.append("I refreshed these files for patch recovery:")
        for idx, target in enumerate(targets, start=1):
            lines.append(f"{idx}. {target.get('path')}:{target.get('start_line')}-{target.get('end_line')}")
    return "\n".join(lines)


def _paths_from_change_plan(change_plan: dict[str, Any] | None) -> list[str]:
    if not isinstance(change_plan, dict):
        return []
    paths = change_plan.get("paths") if isinstance(change_plan.get("paths"), list) else []
    return [str(path) for path in paths if str(path).strip()]


def _paths_from_error(error: str) -> list[str]:
    paths: list[str] = []
    for match in re.finditer(r"(?P<path>[\w./\\-]+\.(?:py|md|txt|json|toml|yaml|yml|js|ts|tsx|jsx))", error):
        paths.append(match.group("path").replace("\\", "/"))
    return paths


def _dedupe(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for path in paths:
        normalized = path.strip().replace("\\", "/")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique
