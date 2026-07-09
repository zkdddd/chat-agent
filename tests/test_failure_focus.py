from kagent.agent.failure_focus import focus_prompt, focus_targets_from_diagnostics


def test_focus_target_from_traceback_line_reads_context_window():
    targets = focus_targets_from_diagnostics(
        [
            {
                "kind": "python_traceback",
                "path": "kagent/context.py",
                "line": 100,
            }
        ],
        context_lines=20,
    )

    assert targets[0]["path"] == "kagent/context.py"
    assert targets[0]["start_line"] == 80
    assert targets[0]["end_line"] == 120


def test_focus_target_from_pytest_nodeid_reads_test_file():
    targets = focus_targets_from_diagnostics(
        [
            {
                "kind": "pytest_failed_node",
                "nodeid": "tests/test_context.py::test_context_failure",
            }
        ]
    )

    assert targets[0]["path"] == "tests/test_context.py"
    assert targets[0]["start_line"] == 1
    assert targets[0]["end_line"] == 160


def test_focus_targets_are_deduplicated_and_limited():
    diagnostics = [
        {"kind": "file_line", "path": "a.py", "line": 10},
        {"kind": "file_line", "path": "a.py", "line": 10},
        {"kind": "file_line", "path": "b.py", "line": 20},
        {"kind": "file_line", "path": "c.py", "line": 30},
    ]

    targets = focus_targets_from_diagnostics(diagnostics, max_targets=2)

    assert [target["path"] for target in targets] == ["a.py", "b.py"]


def test_focus_prompt_lists_targets():
    prompt = focus_prompt(
        [
            {
                "path": "tests/test_context.py",
                "start_line": 1,
                "end_line": 160,
                "reason": "Focus on the failing test file or diagnostic file",
            }
        ]
    )

    assert "automatically read" in prompt
    assert "tests/test_context.py:1-160" in prompt
