from __future__ import annotations

from typing import Any

from .patch_recovery import patch_failure_recovery
from .repair_strategy import classify_failure


def is_tool_failure(name: str, result: dict[str, Any]) -> bool:
    if result.get("rejected"):
        return True
    if result.get("error"):
        return True
    if name == "run_command":
        if result.get("timed_out"):
            return True
        return int(result.get("returncode", 0) or 0) != 0
    return False


def recovery_hint_for_tool(name: str, result: dict[str, Any]) -> dict[str, Any] | None:
    if not is_tool_failure(name, result):
        return None

    text = _failure_text(result)
    lower = text.lower()

    if name == "apply_patch":
        recovery = patch_failure_recovery(
            result,
            change_plan=result.get("change_plan") if isinstance(result.get("change_plan"), dict) else None,
        )
        if recovery:
            return recovery
    if result.get("rejected"):
        return _hint(
            "user_rejected",
            "Do not retry the same action automatically. Choose a safer read-only step or explain what approval is needed.",
            retryable=False,
        )
    if "invalid json arguments" in lower:
        return _hint(
            "invalid_arguments",
            "Fix the tool arguments as valid JSON that matches the tool schema, then retry once.",
        )
    if "timed out" in lower or result.get("timed_out"):
        return _hint(
            "timeout",
            "Use a narrower command, reduce scope, or increase timeout only if the command is known to be safe.",
        )
    if _contains_any(lower, ["path is required", "query is required", "command is required"]):
        return _hint(
            "missing_required_argument",
            "Provide the required argument from the tool schema before retrying.",
        )
    if _contains_any(lower, ["outside allowed", "permission", "access is denied", "denied"]):
        return _hint(
            "permission_scope",
            "Stay inside the allowed workspace scope or ask the user before using an out-of-scope path.",
            retryable=False,
        )
    if _contains_any(lower, ["not found", "does not exist", "cannot find path", "no such file"]):
        return _hint(
            "path_not_found",
            "List or search nearby files first, then retry with the exact existing path.",
        )
    if "expected a file but found a directory" in lower:
        return _hint(
            "expected_file",
            "List the directory and read a specific file inside it instead.",
        )
    if "expected a directory but found a file" in lower or "working directory must be a directory" in lower:
        return _hint(
            "expected_directory",
            "Use the parent directory as cwd/path, or operate on the file with a file tool.",
        )
    if "not valid utf-8" in lower:
        return _hint(
            "non_text_file",
            "Do not read this as text. Use metadata, file listing, or ask before adding binary handling.",
            retryable=False,
        )
    if name == "run_command":
        return _command_failure_hint(lower)
    return _hint(
        "tool_failed",
        "Inspect the error, adjust arguments or gather more context, then retry only if the cause is clear.",
    )


def _command_failure_hint(lower: str) -> dict[str, Any]:
    strategy = classify_failure(lower)
    return _hint(str(strategy["category"]), str(strategy["next_step"]))


def _failure_text(result: dict[str, Any]) -> str:
    parts = [
        result.get("error"),
        result.get("summary"),
        result.get("stderr"),
        result.get("stdout"),
    ]
    return "\n".join(str(part) for part in parts if part)


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _hint(category: str, next_step: str, *, retryable: bool = True) -> dict[str, Any]:
    return {
        "category": category,
        "retryable": retryable,
        "next_step": next_step,
    }
