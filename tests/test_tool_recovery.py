from kagent.agent.tool_recovery import recovery_hint_for_tool


def test_recovery_hint_for_missing_path():
    hint = recovery_hint_for_tool("read_file", {"error": "File not found: missing.py"})

    assert hint is not None
    assert hint["category"] == "path_not_found"
    assert "List or search" in hint["next_step"]


def test_recovery_hint_for_invalid_json_arguments():
    hint = recovery_hint_for_tool(
        "read_file",
        {"error": "Invalid JSON arguments: Expecting property name"},
    )

    assert hint is not None
    assert hint["category"] == "invalid_arguments"
    assert hint["retryable"] is True


def test_recovery_hint_for_user_rejected_action_is_not_retryable():
    hint = recovery_hint_for_tool("delete_path", {"rejected": True, "error": "Action rejected"})

    assert hint is not None
    assert hint["category"] == "user_rejected"
    assert hint["retryable"] is False


def test_recovery_hint_for_missing_dependency():
    hint = recovery_hint_for_tool(
        "run_command",
        {
            "returncode": 1,
            "stderr": "D:\\python\\python.exe: No module named pytest",
        },
    )

    assert hint is not None
    assert hint["category"] == "missing_dependency"


def test_recovery_hint_for_code_error():
    hint = recovery_hint_for_tool(
        "run_command",
        {
            "returncode": 1,
            "stderr": "Traceback (most recent call last):\nSyntaxError: invalid syntax",
        },
    )

    assert hint is not None
    assert hint["category"] == "syntax_error"


def test_recovery_hint_for_patch_failure_includes_read_targets():
    hint = recovery_hint_for_tool(
        "apply_patch",
        {
            "error": "Failed to apply patch",
            "change_plan": {"paths": ["kagent/context.py"]},
        },
    )

    assert hint is not None
    assert hint["category"] == "patch_failed"
    assert hint["read_targets"][0]["path"] == "kagent/context.py"


def test_recovery_hint_for_assertion_failure():
    hint = recovery_hint_for_tool(
        "run_command",
        {
            "returncode": 1,
            "stdout": "E       AssertionError: assert 1 == 2",
        },
    )

    assert hint is not None
    assert hint["category"] == "assertion_failure"
