from kagent.agent.tool_loop_guard import (
    loop_warning_prompt,
    record_tool_call,
    tool_call_signature,
)


def test_tool_call_signature_ignores_unimportant_read_args():
    first = tool_call_signature("read_file", {"path": "a.py", "max_chars": 1000})
    second = tool_call_signature("read_file", {"path": "a.py", "max_chars": 2000})

    assert first == second


def test_record_tool_call_warns_on_repeated_failed_command():
    history = []

    assert record_tool_call(
        history,
        name="run_command",
        args={"command": "python -m pytest -q", "cwd": "."},
        ok=False,
        summary="failed",
    ) is None
    warning = record_tool_call(
        history,
        name="run_command",
        args={"command": "python -m pytest -q", "cwd": "."},
        ok=False,
        summary="failed again",
    )

    assert warning is not None
    assert warning["category"] == "repeated_failed_tool"
    assert warning["failed_count"] == 2


def test_record_tool_call_warns_on_repeated_inspection():
    history = []
    for _ in range(2):
        assert record_tool_call(
            history,
            name="read_file",
            args={"path": "kagent/context.py"},
            ok=True,
        ) is None

    warning = record_tool_call(
        history,
        name="read_file",
        args={"path": "kagent/context.py"},
        ok=True,
    )

    assert warning is not None
    assert warning["category"] == "repeated_inspection"


def test_loop_warning_prompt_is_actionable():
    prompt = loop_warning_prompt(
        {
            "category": "repeated_failed_tool",
            "tool": "apply_patch",
            "repeat_count": 2,
            "failed_count": 2,
            "guidance": "Change strategy.",
        }
    )

    assert "Potential tool loop detected" in prompt
    assert "Change strategy" in prompt
