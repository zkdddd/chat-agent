from kagent.agent.failure_diagnostics import diagnostics_summary, extract_failure_diagnostics


def test_extracts_python_traceback_locations():
    result = {
        "stderr": (
            'Traceback (most recent call last):\n'
            '  File "kagent/agent/code_agent.py", line 42, in run\n'
            "    broken()\n"
            "RuntimeError: boom\n"
        )
    }

    diagnostics = extract_failure_diagnostics(result)

    assert diagnostics[0]["kind"] == "python_traceback"
    assert diagnostics[0]["path"] == "kagent/agent/code_agent.py"
    assert diagnostics[0]["line"] == 42


def test_extracts_pytest_failed_nodes():
    result = {
        "stdout": (
            "FAILED tests/test_context.py::test_manage_context_compacts_old_messages_and_keeps_recent_turns\n"
            "FAILED tests/test_validation.py::test_validation_result_summary_explains_missing_pytest\n"
        )
    }

    diagnostics = extract_failure_diagnostics(result)

    assert diagnostics[0]["kind"] == "pytest_failed_node"
    assert diagnostics[0]["nodeid"] == (
        "tests/test_context.py::test_manage_context_compacts_old_messages_and_keeps_recent_turns"
    )
    assert diagnostics[1]["nodeid"] == (
        "tests/test_validation.py::test_validation_result_summary_explains_missing_pytest"
    )


def test_extracts_syntax_error_with_nearest_file_line():
    result = {
        "stderr": (
            '  File "kagent/context.py", line 12\n'
            "    def bad(:\n"
            "SyntaxError: invalid syntax\n"
        )
    }

    diagnostics = extract_failure_diagnostics(result)

    assert any(item["kind"] == "syntax_error" for item in diagnostics)
    syntax = next(item for item in diagnostics if item["kind"] == "syntax_error")
    assert syntax["path"] == "kagent/context.py"
    assert syntax["line"] == 12


def test_diagnostics_summary_mentions_locations():
    summary = diagnostics_summary(
        [
            {
                "kind": "python_traceback",
                "path": "kagent/context.py",
                "line": 10,
                "message": "manage_context",
            }
        ]
    )

    assert summary is not None
    assert "kagent/context.py:10" in summary
    assert "manage_context" in summary
