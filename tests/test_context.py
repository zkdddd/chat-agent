from kagent.context import (
    PERSISTED_SUMMARY_PREFIX,
    estimate_messages_tokens,
    manage_context,
    prepare_session_history,
)


def test_manage_context_compacts_old_messages_and_keeps_recent_turns():
    messages = [{"role": "system", "content": "system prompt"}]
    messages.extend(
        {
            "role": "user" if idx % 2 == 0 else "assistant",
            "content": f"message-{idx} " + ("x" * 1600),
        }
        for idx in range(20)
    )

    managed, stats = manage_context(
        messages,
        max_tokens=900,
        keep_recent_messages=4,
        summary_max_chars=500,
        per_message_max_chars=700,
    )

    assert stats.compacted is True
    assert stats.compacted_messages > 0
    assert managed[0]["role"] == "system"
    assert managed[-1]["content"].startswith("message-19")
    assert estimate_messages_tokens(managed) <= 900


def test_prepare_session_history_reuses_persisted_summary_and_updates_boundary():
    history = [
        {
            "id": idx + 1,
            "role": "user" if idx % 2 == 0 else "assistant",
            "content": f"turn-{idx} " + ("y" * 1400),
        }
        for idx in range(18)
    ]

    managed, update = prepare_session_history(
        history,
        persisted_summary={
            "summary": "existing summary",
            "through_message_id": 5,
            "source_message_count": 5,
        },
        max_tokens=900,
        keep_recent_messages=4,
        summary_max_chars=600,
        per_message_max_chars=700,
    )

    assert managed[0]["role"] == "system"
    assert managed[0]["content"].startswith(PERSISTED_SUMMARY_PREFIX)
    assert update is not None
    assert update.through_message_id > 5
    assert update.source_message_count > 5
    assert "existing summary" in update.summary
