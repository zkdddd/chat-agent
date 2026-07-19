from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .run_log import read_run_events, summarize_run_log
from .run_self_check import analyze_run_health


def build_run_review(run_log_path: str | Path) -> dict[str, Any]:
    events = read_run_events(run_log_path)
    summary = summarize_run_log(run_log_path)
    health = analyze_run_health(run_log_path)
    finish_data = _event_data(_last_event(events, "run_finish"))
    model_requests = _model_requests(events)
    model_errors = _model_errors(events)
    project_rules = _latest_project_rules(events)
    symbol_impacts = _symbol_impacts(summary, events)
    risk_flags = _risk_flags(
        summary=summary,
        health=health,
        model_errors=model_errors,
        project_rules=project_rules,
        finish_data=finish_data,
    )

    return {
        "path": str(Path(run_log_path)),
        "run_id": summary.get("run_id"),
        "status": summary.get("status") or "running/unknown",
        "workspace": summary.get("workspace_root"),
        "task": _task(events),
        "started_at": summary.get("started_at"),
        "finished_at": summary.get("finished_at"),
        "changed_paths": summary.get("changed_paths") or [],
        "validation": {
            "validated": bool(finish_data.get("validated")),
            "failed": bool(summary.get("validation_failed")),
            "last_summary": summary.get("last_validation_summary"),
        },
        "failed_tools": health.get("failed_tools") or [],
        "model_requests": model_requests,
        "model_errors": model_errors,
        "symbol_impacts": symbol_impacts,
        "project_rules": project_rules,
        "health": {
            "status": health.get("health"),
            "trustworthy": bool(health.get("trustworthy")),
            "issues": health.get("issues") or [],
        },
        "risk_flags": risk_flags,
        "recommended_next_steps": _recommended_next_steps(
            risk_flags=risk_flags,
            symbol_impacts=symbol_impacts,
            changed_paths=summary.get("changed_paths") or [],
        ),
    }


def format_run_review_markdown(review: dict[str, Any]) -> str:
    lines = [
        "# Run Review",
        "",
        f"- run_id: `{review.get('run_id') or 'unknown'}`",
        f"- status: `{review.get('status') or 'unknown'}`",
        f"- workspace: `{review.get('workspace') or 'unknown'}`",
        f"- task: {_inline(review.get('task') or 'unknown')}",
    ]

    changed_paths = _list(review.get("changed_paths"))
    lines.extend(["", "## Changed Paths"])
    lines.extend(_bullet_lines(changed_paths, empty="none", code=True))

    validation = review.get("validation") if isinstance(review.get("validation"), dict) else {}
    validation_status = "failed" if validation.get("failed") else "passed/recorded"
    if not validation.get("validated") and changed_paths:
        validation_status = "not validated"
    lines.extend(
        [
            "",
            "## Validation",
            f"- status: `{validation_status}`",
            f"- last_summary: {_inline(validation.get('last_summary') or 'none')}",
        ]
    )

    lines.extend(["", "## Runtime Signals"])
    lines.extend(_bullet_lines(_failed_tool_lines(review.get("failed_tools")), empty="failed_tools: none"))
    lines.extend(_bullet_lines(_model_request_lines(review.get("model_requests")), empty="model_requests: none"))
    lines.extend(_bullet_lines(_model_error_lines(review.get("model_errors")), empty="model_errors: none"))

    project_rules = review.get("project_rules") if isinstance(review.get("project_rules"), dict) else None
    lines.extend(["", "## Project Rules"])
    lines.append(f"- {_project_rules_line(project_rules)}")

    lines.extend(["", "## Symbol Impacts"])
    lines.extend(_bullet_lines(_symbol_impact_lines(review.get("symbol_impacts")), empty="none"))

    lines.extend(["", "## Risks"])
    lines.extend(_bullet_lines(_list(review.get("risk_flags")), empty="none", code=True))

    lines.extend(["", "## Recommended Next Steps"])
    lines.extend(_bullet_lines(_list(review.get("recommended_next_steps")), empty="none"))
    return "\n".join(lines)


def _event_data(event: dict[str, Any] | None) -> dict[str, Any]:
    if not event:
        return {}
    data = event.get("data")
    return data if isinstance(data, dict) else {}


def _last_event(events: list[dict[str, Any]], event_type: str) -> dict[str, Any] | None:
    return next((event for event in reversed(events) if event.get("event") == event_type), None)


def _task(events: list[dict[str, Any]]) -> str | None:
    for event in events:
        data = _event_data(event)
        for key in ("task", "user_task", "prompt", "objective"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return _short_text(value, limit=240)
    return None


def _model_requests(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for event in events:
        if event.get("event") != "model_request":
            continue
        data = _event_data(event)
        model = str(data.get("model") or "unknown")
        effort = str(data.get("reasoning_effort") or "no-reasoning")
        fallback = bool(data.get("fallback_without_reasoning"))
        key = f"{model}|{effort}|{fallback}"
        counts[key] += 1

    requests: list[dict[str, Any]] = []
    for key, count in counts.most_common():
        model, effort, fallback = key.split("|", 2)
        requests.append(
            {
                "model": model,
                "reasoning_effort": effort,
                "fallback_without_reasoning": fallback == "True",
                "count": count,
            }
        )
    return requests


def _model_errors(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for event in events:
        if event.get("event") != "model_error":
            continue
        data = _event_data(event)
        errors.append(
            {
                "model": str(data.get("model") or "unknown"),
                "error_type": str(data.get("error_type") or "error"),
                "detail": _short_text(data.get("error")) or "",
            }
        )
    return errors


def _latest_project_rules(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in reversed(events):
        if event.get("event") != "project_rules_check":
            continue
        data = _event_data(event)
        return {
            "path": data.get("path"),
            "health": data.get("health"),
            "score": data.get("score"),
            "issue_count": data.get("issue_count"),
            "issues": data.get("issues") if isinstance(data.get("issues"), list) else [],
        }
    return None


def _symbol_impacts(summary: dict[str, Any], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    impacts: list[dict[str, Any]] = []
    raw_summary_impacts = summary.get("symbol_impacts")
    if isinstance(raw_summary_impacts, list):
        impacts.extend(item for item in raw_summary_impacts if isinstance(item, dict))

    for event in events:
        data = _event_data(event)
        impacts.extend(_nested_symbol_impacts(data))

    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for impact in impacts:
        symbol = str(impact.get("symbol") or "unknown")
        definition_path = str(impact.get("definition_path") or impact.get("path") or "unknown")
        key = (symbol, definition_path)
        normalized = {
            "symbol": symbol,
            "definition_path": definition_path,
            "reference_count": impact.get("reference_count"),
            "related_tests": _list(impact.get("related_tests"))[:5],
            "validation_commands": _commands(impact.get("validation_commands"))[:5],
        }
        if key not in by_key:
            by_key[key] = normalized
            continue
        existing = by_key[key]
        existing["reference_count"] = existing.get("reference_count") or normalized.get("reference_count")
        existing["related_tests"] = _merge_unique(
            _list(existing.get("related_tests")), normalized["related_tests"], limit=5
        )
        existing["validation_commands"] = _merge_unique(
            _list(existing.get("validation_commands")), normalized["validation_commands"], limit=5
        )
    return list(by_key.values())[:12]


def _nested_symbol_impacts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        raw = value.get("symbol_impacts")
        found = [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
        for child in value.values():
            if isinstance(child, dict | list):
                found.extend(_nested_symbol_impacts(child))
        return found
    if isinstance(value, list):
        found: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict | list):
                found.extend(_nested_symbol_impacts(item))
        return found
    return []


def _risk_flags(
    *,
    summary: dict[str, Any],
    health: dict[str, Any],
    model_errors: list[dict[str, str]],
    project_rules: dict[str, Any] | None,
    finish_data: dict[str, Any],
) -> list[str]:
    flags = [str(issue.get("code")) for issue in health.get("issues") or [] if issue.get("code")]
    changed_paths = summary.get("changed_paths") or []
    if changed_paths and not finish_data.get("validated") and "unverified_changes" not in flags:
        flags.append("unverified_changes")
    if model_errors:
        flags.append("model_errors")
    if project_rules is None:
        flags.append("project_rules_not_checked")
    elif str(project_rules.get("health") or "").lower() not in {"", "pass", "healthy", "ok", "good"}:
        flags.append("project_rules_need_attention")
    return list(dict.fromkeys(flags))


def _recommended_next_steps(
    *, risk_flags: list[str], symbol_impacts: list[dict[str, Any]], changed_paths: list[str]
) -> list[str]:
    steps: list[str] = []
    if "validation_failed" in risk_flags:
        steps.append("Inspect the last validation failure, fix the root cause, then rerun focused validation.")
    if "unverified_changes" in risk_flags:
        steps.append("Run the narrowest relevant validation for the changed files before finalizing.")
    if "failed_tools" in risk_flags:
        steps.append("Review failed tool results and confirm they were recovered or are no longer relevant.")
    if "model_errors" in risk_flags:
        steps.append("Check model settings or fallback behavior before relying on this run.")
    if "project_rules_not_checked" in risk_flags:
        steps.append("Run a project rules check so local validation, safety, and workflow rules are visible.")
    if "project_rules_need_attention" in risk_flags:
        steps.append("Update or follow the issues reported by KAGENT.md project rules.")
    if symbol_impacts:
        steps.append("Prioritize review and tests around impacted symbols and their related tests.")
    if changed_paths and not steps:
        steps.append("Review the changed files and keep the recorded validation summary with the final answer.")
    if not steps:
        steps.append("No immediate follow-up detected from the run log.")
    return list(dict.fromkeys(steps))


def _failed_tool_lines(value: Any) -> list[str]:
    tools = value if isinstance(value, list) else []
    lines: list[str] = []
    for item in tools:
        if not isinstance(item, dict):
            continue
        detail = f": {item.get('detail')}" if item.get("detail") else ""
        lines.append(f"failed_tool: `{item.get('name') or 'unknown'}` x{item.get('count') or 1}{detail}")
    return lines


def _model_request_lines(value: Any) -> list[str]:
    requests = value if isinstance(value, list) else []
    lines: list[str] = []
    for item in requests:
        if not isinstance(item, dict):
            continue
        fallback = " fallback" if item.get("fallback_without_reasoning") else ""
        lines.append(
            f"model_request: `{item.get('model') or 'unknown'}`/"
            f"`{item.get('reasoning_effort') or 'no-reasoning'}` x{item.get('count') or 1}{fallback}"
        )
    return lines


def _model_error_lines(value: Any) -> list[str]:
    errors = value if isinstance(value, list) else []
    lines: list[str] = []
    for item in errors:
        if not isinstance(item, dict):
            continue
        detail = f": {item.get('detail')}" if item.get("detail") else ""
        lines.append(f"model_error: `{item.get('model') or 'unknown'}` {item.get('error_type') or 'error'}{detail}")
    return lines


def _project_rules_line(project_rules: dict[str, Any] | None) -> str:
    if not project_rules:
        return "not checked"
    parts = [f"health: `{project_rules.get('health') or 'unknown'}`"]
    if project_rules.get("score") is not None:
        parts.append(f"score: `{project_rules.get('score')}`")
    if project_rules.get("issue_count") is not None:
        parts.append(f"issues: `{project_rules.get('issue_count')}`")
    return ", ".join(parts)


def _symbol_impact_lines(value: Any) -> list[str]:
    impacts = value if isinstance(value, list) else []
    lines: list[str] = []
    for impact in impacts:
        if not isinstance(impact, dict):
            continue
        refs = impact.get("reference_count")
        ref_text = f", refs: `{refs}`" if refs is not None else ""
        tests = _list(impact.get("related_tests"))
        test_text = f", tests: {', '.join(f'`{test}`' for test in tests[:3])}" if tests else ""
        lines.append(
            f"`{impact.get('symbol') or 'unknown'}` at "
            f"`{impact.get('definition_path') or 'unknown'}`{ref_text}{test_text}"
        )
    return lines


def _bullet_lines(items: list[str], *, empty: str, code: bool = False) -> list[str]:
    if not items:
        return [f"- {empty}"]
    if code:
        return [f"- `{item}`" for item in items]
    return [f"- {item}" for item in items]


def _commands(value: Any) -> list[str]:
    commands: list[str] = []
    if not isinstance(value, list):
        return commands
    for item in value:
        if isinstance(item, str):
            commands.append(item)
        elif isinstance(item, dict) and item.get("command"):
            commands.append(str(item["command"]))
    return commands


def _list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _merge_unique(first: list[str], second: list[str], *, limit: int) -> list[str]:
    return list(dict.fromkeys([*first, *second]))[:limit]


def _inline(value: Any) -> str:
    text = _short_text(value) or ""
    return f"`{text}`" if text else "`none`"


def _short_text(value: Any, limit: int = 180) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
