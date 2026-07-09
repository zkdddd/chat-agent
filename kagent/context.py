from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ContextStats:
    original_messages: int
    final_messages: int
    original_tokens: int
    final_tokens: int
    compacted_messages: int
    compacted: bool


@dataclass(frozen=True)
class PersistedContextUpdate:
    summary: str
    through_message_id: int
    source_message_count: int


PERSISTED_SUMMARY_PREFIX = (
    "Persisted conversation summary from earlier messages.\n"
    "Use this as background context, but prefer the latest user request.\n\n"
)


def estimate_text_tokens(text: str) -> int:
    """Small dependency-free token estimate used for preflight budgeting."""
    if not text:
        return 0
    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    non_ascii_chars = len(text) - ascii_chars
    return max(1, (ascii_chars + non_ascii_chars * 2) // 4)


def estimate_message_tokens(message: dict[str, Any]) -> int:
    total = 6 + estimate_text_tokens(str(message.get("role") or ""))
    content = message.get("content")
    if content is not None:
        total += estimate_text_tokens(str(content))
    tool_calls = message.get("tool_calls")
    if tool_calls:
        total += estimate_text_tokens(json.dumps(tool_calls, ensure_ascii=False))
    tool_call_id = message.get("tool_call_id")
    if tool_call_id:
        total += estimate_text_tokens(str(tool_call_id))
    return total


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    return sum(estimate_message_tokens(message) for message in messages)


def manage_context(
    messages: list[dict[str, Any]],
    *,
    max_tokens: int,
    keep_recent_messages: int,
    summary_max_chars: int,
    per_message_max_chars: int,
) -> tuple[list[dict[str, Any]], ContextStats]:
    original_tokens = estimate_messages_tokens(messages)
    if original_tokens <= max_tokens:
        copied = [_copy_message(message, per_message_max_chars) for message in messages]
        return copied, ContextStats(
            original_messages=len(messages),
            final_messages=len(copied),
            original_tokens=original_tokens,
            final_tokens=estimate_messages_tokens(copied),
            compacted_messages=0,
            compacted=False,
        )

    system_prefix, body = _split_system_prefix(messages)
    system_tokens = estimate_messages_tokens(system_prefix)
    recent_budget = max(1, max_tokens - system_tokens - estimate_text_tokens("Earlier context compacted.") - 64)
    recent_messages, compacted_messages = _select_recent_body(
        body,
        recent_budget=recent_budget,
        keep_recent_messages=max(1, keep_recent_messages),
        per_message_max_chars=per_message_max_chars,
    )
    compacted_messages = _normalize_compacted_prefix(compacted_messages, recent_messages)

    summary = _summarize_messages(compacted_messages, max_chars=max(256, summary_max_chars))
    final_messages = list(system_prefix)
    if summary:
        final_messages.append(
            {
                "role": "system",
                "content": (
                    "Earlier conversation context was compacted to stay within the model context budget.\n"
                    "Use this summary as background, but prefer the latest user request and recent tool results.\n\n"
                    f"{summary}"
                ),
            }
        )
    final_messages.extend(recent_messages)
    final_messages = _trim_until_within_budget(final_messages, max_tokens, per_message_max_chars)

    return final_messages, ContextStats(
        original_messages=len(messages),
        final_messages=len(final_messages),
        original_tokens=original_tokens,
        final_tokens=estimate_messages_tokens(final_messages),
        compacted_messages=len(compacted_messages),
        compacted=True,
    )


def prepare_session_history(
    history: list[dict[str, Any]],
    *,
    persisted_summary: dict[str, Any] | None,
    max_tokens: int,
    keep_recent_messages: int,
    summary_max_chars: int,
    per_message_max_chars: int,
) -> tuple[list[dict[str, Any]], PersistedContextUpdate | None]:
    through_message_id = _safe_int(
        (persisted_summary or {}).get("through_message_id"),
        default=0,
    )
    existing_summary = str((persisted_summary or {}).get("summary") or "").strip()
    remaining_history = [
        dict(message)
        for message in history
        if _safe_int(message.get("id"), default=0) > through_message_id
    ]

    prefix = []
    if existing_summary:
        prefix.append(
            {
                "role": "system",
                "content": PERSISTED_SUMMARY_PREFIX + existing_summary,
            }
        )

    candidate = prefix + remaining_history
    managed, stats = manage_context(
        candidate,
        max_tokens=max_tokens,
        keep_recent_messages=keep_recent_messages,
        summary_max_chars=summary_max_chars,
        per_message_max_chars=per_message_max_chars,
    )
    if not stats.compacted or stats.compacted_messages <= 0:
        return managed, None

    compacted_messages = remaining_history[: stats.compacted_messages]
    if not compacted_messages:
        return managed, None

    new_through_id = max(_safe_int(message.get("id"), default=0) for message in compacted_messages)
    if new_through_id <= through_message_id:
        return managed, None

    summary_parts = []
    if existing_summary:
        summary_parts.append(existing_summary)
    summary_parts.append(_summarize_messages(compacted_messages, max_chars=max(256, summary_max_chars)))
    combined_summary = "\n".join(part.strip() for part in summary_parts if part.strip())
    if len(combined_summary) > summary_max_chars:
        combined_summary = _clip(combined_summary, summary_max_chars)

    return managed, PersistedContextUpdate(
        summary=combined_summary,
        through_message_id=new_through_id,
        source_message_count=_safe_int(
            (persisted_summary or {}).get("source_message_count"),
            default=0,
        )
        + len(compacted_messages),
    )


def _copy_message(message: dict[str, Any], per_message_max_chars: int) -> dict[str, Any]:
    copied = dict(message)
    content = copied.get("content")
    if isinstance(content, str) and len(content) > per_message_max_chars:
        copied["content"] = _clip(content, per_message_max_chars)
    return copied


def _split_system_prefix(messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    system_prefix: list[dict[str, Any]] = []
    idx = 0
    for idx, message in enumerate(messages):
        if message.get("role") != "system":
            break
        system_prefix.append(dict(message))
    else:
        return system_prefix, []
    return system_prefix, [dict(message) for message in messages[idx:]]


def _select_recent_body(
    body: list[dict[str, Any]],
    *,
    recent_budget: int,
    keep_recent_messages: int,
    per_message_max_chars: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected_reversed: list[dict[str, Any]] = []
    selected_tokens = 0
    split_at = len(body)

    for idx in range(len(body) - 1, -1, -1):
        copied = _copy_message(body[idx], per_message_max_chars)
        token_count = estimate_message_tokens(copied)
        must_keep = len(selected_reversed) < keep_recent_messages
        if selected_reversed and not must_keep and selected_tokens + token_count > recent_budget:
            break
        selected_reversed.append(copied)
        selected_tokens += token_count
        split_at = idx

    recent = list(reversed(selected_reversed))
    compacted = [dict(message) for message in body[:split_at]]
    return recent, compacted


def _normalize_compacted_prefix(
    compacted: list[dict[str, Any]],
    recent: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    while recent and recent[0].get("role") == "tool":
        compacted.append(recent.pop(0))
    return compacted


def _summarize_messages(messages: list[dict[str, Any]], *, max_chars: int) -> str:
    if not messages:
        return ""

    lines: list[str] = []
    for message in messages:
        role = str(message.get("role") or "unknown")
        content = str(message.get("content") or "").strip()
        if role == "assistant" and message.get("tool_calls"):
            tool_names = []
            for call in message.get("tool_calls") or []:
                if isinstance(call, dict):
                    function = call.get("function") or {}
                    if isinstance(function, dict) and function.get("name"):
                        tool_names.append(str(function["name"]))
            if tool_names:
                content = f"Requested tool calls: {', '.join(tool_names)}. {content}".strip()
        if role == "tool":
            content = _tool_result_summary(content)
        if not content:
            continue
        lines.append(f"- {role}: {_single_line(content, 240)}")
        if sum(len(line) + 1 for line in lines) >= max_chars:
            break

    summary = "\n".join(lines)
    if len(summary) > max_chars:
        return _clip(summary, max_chars)
    return summary


def _tool_result_summary(raw: str) -> str:
    try:
        parsed = json.loads(raw)
    except Exception:
        return raw
    if not isinstance(parsed, dict):
        return raw
    parts = []
    for key in ("summary", "error", "path", "command"):
        value = parsed.get(key)
        if value:
            parts.append(f"{key}={_single_line(str(value), 160)}")
    ok = parsed.get("ok")
    if ok is not None:
        parts.insert(0, f"ok={bool(ok)}")
    return "; ".join(parts) or raw


def _trim_until_within_budget(
    messages: list[dict[str, Any]],
    max_tokens: int,
    per_message_max_chars: int,
) -> list[dict[str, Any]]:
    trimmed = [_copy_message(message, per_message_max_chars) for message in messages]
    while len(trimmed) > 1 and estimate_messages_tokens(trimmed) > max_tokens:
        remove_idx = 1 if trimmed[0].get("role") == "system" else 0
        trimmed.pop(remove_idx)
        while len(trimmed) > remove_idx and trimmed[remove_idx].get("role") == "tool":
            trimmed.pop(remove_idx)
    return trimmed


def _single_line(text: str, limit: int) -> str:
    return _clip(" ".join(text.split()), limit)


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 24)].rstrip() + "\n... (context clipped)"


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
