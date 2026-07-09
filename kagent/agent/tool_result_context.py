from __future__ import annotations

import json
import re
from typing import Any

from .failure_diagnostics import extract_failure_diagnostics
from .tool_recovery import recovery_hint_for_tool


DEFAULT_TEXT_LIMIT = 8000
READ_FILE_CONTENT_LIMIT = 12000
COMMAND_STREAM_LIMIT = 6000
SEARCH_MATCH_LIMIT = 20
LIST_ITEMS_LIMIT = 120
SYMBOL_MATCH_LIMIT = 50


def tool_result_for_model(name: str, result: dict[str, Any]) -> dict[str, Any]:
    if name == "read_file":
        compacted = _compact_read_file(result)
    elif name == "search_file":
        compacted = _compact_search_file(result)
    elif name == "list_files":
        compacted = _compact_list_files(result)
    elif name == "find_symbol":
        compacted = _compact_find_symbol(result)
    elif name == "run_command":
        compacted = _compact_run_command(result)
    else:
        compacted = _compact_value(result, text_limit=DEFAULT_TEXT_LIMIT)
    if isinstance(compacted, dict):
        if isinstance(result.get("change_plan"), dict):
            compacted["change_plan"] = result["change_plan"]
        recovery = recovery_hint_for_tool(name, result)
        if recovery:
            compacted["recovery"] = recovery
    return compacted


def tool_result_json_for_model(name: str, result: dict[str, Any]) -> str:
    compacted = tool_result_for_model(name, result)
    return json.dumps(compacted, ensure_ascii=False)


def _compact_read_file(result: dict[str, Any]) -> dict[str, Any]:
    compacted = _copy_keys(
        result,
        [
            "path",
            "abs_path",
            "start_line",
            "end_line",
            "line_count",
            "truncated",
            "ok",
            "error",
        ],
    )
    content = str(result.get("content") or "")
    compacted["content"] = _clip_middle(content, READ_FILE_CONTENT_LIMIT)
    compacted["content_chars"] = len(content)
    compacted["context_compacted"] = len(compacted["content"]) < len(content)
    return compacted


def _compact_search_file(result: dict[str, Any]) -> dict[str, Any]:
    compacted = _copy_keys(
        result,
        [
            "query",
            "path",
            "file_glob",
            "count",
            "scanned_files",
            "skipped_binary",
            "truncated",
            "case_sensitive",
            "context_lines",
            "ok",
            "error",
        ],
    )
    matches = result.get("matches") if isinstance(result.get("matches"), list) else []
    compacted["matches"] = [
        _compact_value(match, text_limit=1200)
        for match in matches[:SEARCH_MATCH_LIMIT]
        if isinstance(match, dict)
    ]
    compacted["matches_omitted"] = max(0, len(matches) - SEARCH_MATCH_LIMIT)
    compacted["context_compacted"] = len(matches) > SEARCH_MATCH_LIMIT
    return compacted


def _compact_list_files(result: dict[str, Any]) -> dict[str, Any]:
    compacted = _copy_keys(
        result,
        ["root", "path", "count", "truncated", "ignored_count", "max_depth", "ok", "error"],
    )
    items = result.get("items") if isinstance(result.get("items"), list) else []
    compacted["items"] = [
        _compact_value(item, text_limit=800)
        for item in items[:LIST_ITEMS_LIMIT]
        if isinstance(item, dict)
    ]
    compacted["items_omitted"] = max(0, len(items) - LIST_ITEMS_LIMIT)
    compacted["context_compacted"] = len(items) > LIST_ITEMS_LIMIT
    return compacted


def _compact_find_symbol(result: dict[str, Any]) -> dict[str, Any]:
    compacted = _copy_keys(result, ["query", "kind", "exact", "ok", "error"])
    matches = result.get("matches") if isinstance(result.get("matches"), list) else []
    compacted["matches"] = [
        _compact_value(match, text_limit=800)
        for match in matches[:SYMBOL_MATCH_LIMIT]
        if isinstance(match, dict)
    ]
    compacted["count"] = len(matches)
    compacted["matches_omitted"] = max(0, len(matches) - SYMBOL_MATCH_LIMIT)
    compacted["context_compacted"] = len(matches) > SYMBOL_MATCH_LIMIT
    return compacted


def _compact_run_command(result: dict[str, Any]) -> dict[str, Any]:
    compacted = _copy_keys(
        result,
        [
            "command",
            "cwd",
            "returncode",
            "timed_out",
            "duration_ms",
            "summary",
            "stdout_truncated",
            "stderr_truncated",
            "ok",
            "error",
        ],
    )
    stdout = str(result.get("stdout") or "")
    stderr = str(result.get("stderr") or "")
    compacted["stdout"] = _compact_command_stream(stdout)
    compacted["stderr"] = _compact_command_stream(stderr)
    compacted["stdout_chars"] = len(stdout)
    compacted["stderr_chars"] = len(stderr)
    compacted["important_lines"] = _important_command_lines(stdout, stderr)
    compacted["diagnostics"] = extract_failure_diagnostics(result)
    compacted["context_compacted"] = (
        len(compacted["stdout"]) < len(stdout)
        or len(compacted["stderr"]) < len(stderr)
        or bool(compacted["important_lines"])
        or bool(compacted["diagnostics"])
    )
    return compacted


def _compact_command_stream(text: str) -> str:
    if len(text) <= COMMAND_STREAM_LIMIT:
        return text
    return _clip_head_tail(text, COMMAND_STREAM_LIMIT)


def _important_command_lines(stdout: str, stderr: str, limit: int = 40) -> list[str]:
    pattern = re.compile(
        r"(error|failed|failure|exception|traceback|assert|warning|no module named|syntaxerror|pytest|exit \d+)",
        re.IGNORECASE,
    )
    lines: list[str] = []
    for source_name, text in (("stdout", stdout), ("stderr", stderr)):
        for line in text.splitlines():
            if pattern.search(line):
                lines.append(f"{source_name}: {_clip_middle(line.strip(), 500)}")
                if len(lines) >= limit:
                    return lines
    return lines


def _compact_value(value: Any, *, text_limit: int) -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clip_middle(value, text_limit)
    if isinstance(value, dict):
        return {str(key): _compact_value(item, text_limit=text_limit) for key, item in value.items()}
    if isinstance(value, list):
        return [_compact_value(item, text_limit=text_limit) for item in value[:100]]
    return str(value)


def _copy_keys(source: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: source[key] for key in keys if key in source}


def _clip_middle(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 40:
        return text[:limit]
    head = max(1, int(limit * 0.65))
    tail = max(1, limit - head - 40)
    return text[:head].rstrip() + "\n... (tool output clipped) ...\n" + text[-tail:].lstrip()


def _clip_head_tail(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = max(1, limit // 2)
    tail = max(1, limit - head - 44)
    return text[:head].rstrip() + "\n... (middle of command output clipped) ...\n" + text[-tail:].lstrip()
