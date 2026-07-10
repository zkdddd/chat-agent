from kagent.agent.risk_policy import tool_policy


def test_read_tools_do_not_require_approval():
    policy = tool_policy("read_file", {"path": "kagent/config.py"}, {}, None)

    assert policy["risk_level"] == "safe"
    assert policy["approval_required"] is False
    assert policy["destructive"] is False


def test_safe_validation_command_is_low_risk_without_approval():
    policy = tool_policy(
        "run_command",
        {"command": "python -m py_compile kagent/agent/code_agent.py", "cwd": "."},
        {},
        None,
    )

    assert policy["risk_level"] == "low"
    assert policy["approval_required"] is False
    assert policy["risk_categories"] == ["validation"]


def test_destructive_command_is_critical_and_requires_approval():
    policy = tool_policy(
        "run_command",
        {"command": "rm -rf build", "cwd": "."},
        {},
        None,
    )

    assert policy["risk_level"] == "critical"
    assert policy["approval_required"] is True
    assert policy["destructive"] is True
    assert policy["risk_categories"] == ["destructive_delete"]


def test_sensitive_file_write_is_high_risk():
    policy = tool_policy(
        "write_file",
        {"path": ".env", "content": "SECRET=1"},
        {"path": ".env", "exists": True, "line_count": 1},
        None,
    )

    assert policy["risk_level"] == "high"
    assert policy["approval_required"] is True


def test_large_directory_delete_is_critical():
    policy = tool_policy(
        "delete_path",
        {"path": "src"},
        {"path": "src", "item_type": "directory", "item_count": 25},
        None,
    )

    assert policy["risk_level"] == "critical"
    assert policy["destructive"] is True


def test_dependency_install_command_is_high_risk_with_category():
    policy = tool_policy(
        "run_command",
        {"command": "python -m pip install requests", "cwd": "."},
        {},
        None,
    )

    assert policy["risk_level"] == "high"
    assert policy["approval_required"] is True
    assert policy["risk_categories"] == ["dependency_change"]
    assert policy["risk_factors"][0]["kind"] == "dependency_command"


def test_git_write_command_is_high_risk_with_category():
    policy = tool_policy(
        "run_command",
        {"command": "git commit -m test", "cwd": "."},
        {},
        None,
    )

    assert policy["risk_level"] == "high"
    assert policy["risk_categories"] == ["git_write"]


def test_network_command_is_high_risk_with_category():
    policy = tool_policy(
        "run_command",
        {"command": "curl https://example.com", "cwd": "."},
        {},
        None,
    )

    assert policy["risk_level"] == "high"
    assert policy["risk_categories"] == ["network"]


def test_chained_command_is_high_risk_with_category():
    policy = tool_policy(
        "run_command",
        {"command": "python -m pytest -q && git status", "cwd": "."},
        {},
        None,
    )

    assert policy["risk_level"] == "high"
    assert policy["risk_categories"] == ["chained_shell"]
