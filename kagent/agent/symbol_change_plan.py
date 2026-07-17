from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from .symbol_index import find_symbol_contexts, find_symbol_references, find_symbols


def build_symbol_change_plan(
    root: Path,
    symbol_name: str,
    *,
    kind: str | None = None,
    exact: bool = True,
    context_lines: int = 4,
    max_references: int = 80,
    max_validation_commands: int = 5,
) -> dict[str, Any]:
    symbol = str(symbol_name or "").strip()
    if not symbol:
        return {"ok": False, "error": "symbol_name is required"}

    definitions = find_symbols(root, symbol, kind=kind, exact=exact, limit=10)
    contexts = find_symbol_contexts(
        root,
        symbol,
        kind=kind,
        exact=exact,
        limit=5,
        context_lines=context_lines,
        max_chars=10000,
    )
    references = find_symbol_references(root, symbol, include_tests=True, limit=max_references)
    related_tests = _related_tests_from_references(references)
    validation_commands = _validation_commands_for_tests(
        related_tests,
        max_commands=max_validation_commands,
    )

    return {
        "ok": True,
        "symbol": symbol,
        "kind": kind,
        "exact": exact,
        "definition_count": len(definitions),
        "definitions": definitions,
        "primary_definition": definitions[0] if definitions else None,
        "contexts": contexts,
        "reference_count": len(references),
        "references": references,
        "related_tests": related_tests,
        "validation_commands": validation_commands,
        "risk_summary": _risk_summary(symbol, definitions, references, related_tests),
        "summary": _summary(symbol, definitions, references, related_tests),
    }


def _related_tests_from_references(references: list[dict[str, object]]) -> list[dict[str, Any]]:
    related: list[dict[str, Any]] = []
    seen: set[str] = set()
    for reference in references:
        if not reference.get("is_test"):
            continue
        path = str(reference.get("path") or "")
        if not path or path in seen:
            continue
        seen.add(path)
        related.append(
            {
                "path": path,
                "reason": f"references symbol `{reference.get('symbol')}`",
                "first_reference_line": reference.get("line"),
                "reference_type": reference.get("reference_type"),
            }
        )
    return related


def _validation_commands_for_tests(
    related_tests: list[dict[str, Any]], *, max_commands: int
) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for item in related_tests[:max_commands]:
        path = str(item.get("path") or "")
        if not path:
            continue
        commands.append(
            {
                "label": "Related symbol test",
                "reason": item.get("reason") or "Test references the changed symbol.",
                "command": subprocess.list2cmdline([sys.executable, "-m", "pytest", "-q", path]),
                "cwd": ".",
                "timeout_ms": 180000,
                "related_test": path,
            }
        )
    return commands


def _risk_summary(
    symbol: str,
    definitions: list[dict[str, object]],
    references: list[dict[str, object]],
    related_tests: list[dict[str, Any]],
) -> str:
    parts = [
        f"Changing `{symbol}` may affect {len(references)} reference(s)",
        f"{len(related_tests)} related test file(s)",
    ]
    if not definitions:
        parts.append("definition not found")
    if any(not item.get("is_test") for item in references):
        parts.append("non-test callers present")
    return "; ".join(parts)


def _summary(
    symbol: str,
    definitions: list[dict[str, object]],
    references: list[dict[str, object]],
    related_tests: list[dict[str, Any]],
) -> str:
    if not definitions:
        return f"No definition found for `{symbol}`; inspect references before editing."
    definition = definitions[0]
    location = f"{definition.get('path')}:{definition.get('line')}"
    return (
        f"Plan symbol change for `{symbol}` at {location}: "
        f"{len(references)} reference(s), {len(related_tests)} related test file(s)."
    )
