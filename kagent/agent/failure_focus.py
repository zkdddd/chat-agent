from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_CONTEXT_LINES = 40
MAX_FOCUS_TARGETS = 3


def focus_targets_from_diagnostics(
    diagnostics: list[dict[str, Any]],
    *,
    context_lines: int = DEFAULT_CONTEXT_LINES,
    max_targets: int = MAX_FOCUS_TARGETS,
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    seen: set[tuple[str, int | None, int | None]] = set()
    for item in diagnostics:
        path = _diagnostic_path(item)
        if not path:
            continue
        line = _diagnostic_line(item)
        if line is not None:
            start_line = max(1, line - context_lines)
            end_line = line + context_lines
            reason = f"Focus around diagnostic line {line}"
        else:
            start_line = 1
            end_line = 160
            reason = "Focus on the failing test file or diagnostic file"

        key = (path, start_line, end_line)
        if key in seen:
            continue
        seen.add(key)
        targets.append(
            {
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
                "max_chars": 16000,
                "reason": reason,
                "diagnostic": item,
            }
        )
        if len(targets) >= max_targets:
            break
    return targets


def focus_prompt(targets: list[dict[str, Any]]) -> str:
    if not targets:
        return ""
    lines = [
        "Validation failed. I automatically read the most relevant failure locations.",
        "Use these focused excerpts first before searching broadly:",
    ]
    for idx, target in enumerate(targets, start=1):
        lines.append(
            f"{idx}. {target['path']}:{target['start_line']}-{target['end_line']} - {target['reason']}"
        )
    return "\n".join(lines)


def _diagnostic_path(item: dict[str, Any]) -> str | None:
    path = item.get("path")
    if path:
        return str(path)
    nodeid = item.get("nodeid")
    if not nodeid:
        return None
    raw_path = str(nodeid).split("::", 1)[0]
    if Path(raw_path).suffix:
        return raw_path
    return None


def _diagnostic_line(item: dict[str, Any]) -> int | None:
    try:
        line = item.get("line")
        return int(line) if line else None
    except (TypeError, ValueError):
        return None
