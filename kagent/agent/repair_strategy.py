from __future__ import annotations

import re
from typing import Any


def classify_failure(result_or_text: dict[str, Any] | str) -> dict[str, Any]:
    text = _failure_text(result_or_text)
    lower = text.lower()

    if _contains_any(lower, ["no module named", "module not found", "modulenotfounderror"]):
        return _strategy(
            "missing_dependency",
            "Report or install the missing dependency only if dependency installation is allowed.",
        )
    if _contains_any(lower, ["is not recognized", "command not found", "not recognized as"]):
        return _strategy(
            "command_not_found",
            "Check available project scripts or use an available interpreter/command before retrying.",
        )
    if _contains_any(lower, ["timed out", "timeout"]):
        return _strategy(
            "timeout",
            "Reduce command scope, run a narrower test, or increase timeout only if the command is safe.",
        )
    if "syntaxerror" in lower:
        return _strategy(
            "syntax_error",
            "Open the syntax error location, fix the invalid code, then run py_compile or the focused test.",
        )
    if _contains_any(lower, ["importerror", "cannot import name", "imported module", "from partially initialized module"]):
        return _strategy(
            "import_error",
            "Inspect imports, module names, and circular dependencies before changing behavior.",
        )
    if _contains_any(lower, ["assertionerror", "assert ", "e       assert"]):
        return _strategy(
            "assertion_failure",
            "Compare expected vs actual values in the failing assertion and fix the smallest responsible logic.",
        )
    if _contains_any(lower, ["traceback", "exception", "runtimeerror", "valueerror", "typeerror", "keyerror"]):
        return _strategy(
            "runtime_error",
            "Use the traceback location and fix the runtime cause, not just the symptom.",
        )
    if re.search(r"\b\d+\s+failed\b|\bfailed\b|\bfailure\b", lower):
        return _strategy(
            "test_failure",
            "Use the failing test node and diagnostics to make a targeted fix, then rerun focused validation.",
        )
    return _strategy(
        "unknown_failure",
        "Inspect stderr/stdout and diagnostics, gather focused context, then retry with a targeted change.",
    )


def repair_strategy_prompt(summary: str | None) -> str:
    strategy = classify_failure(summary or "")
    return (
        f"Failure category: {strategy['category']}.\n"
        f"Repair strategy: {strategy['next_step']}"
    )


def _strategy(category: str, next_step: str) -> dict[str, Any]:
    return {
        "category": category,
        "next_step": next_step,
    }


def _failure_text(result_or_text: dict[str, Any] | str) -> str:
    if isinstance(result_or_text, str):
        return result_or_text
    return "\n".join(
        str(result_or_text.get(key) or "")
        for key in ("error", "summary", "stderr", "stdout")
    )


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)
