import json

from kagent.agent.tool_result_context import tool_result_for_model, tool_result_json_for_model


def test_read_file_result_is_compacted_but_keeps_metadata():
    content = "A" * 9000 + "\nIMPORTANT_TAIL"
    result = {
        "path": "large.py",
        "abs_path": "D:/repo/large.py",
        "start_line": 1,
        "end_line": 500,
        "line_count": 500,
        "content": content,
        "truncated": False,
    }

    compacted = tool_result_for_model("read_file", result)

    assert compacted["path"] == "large.py"
    assert compacted["line_count"] == 500
    assert compacted["content"] == content
    assert compacted["context_compacted"] is False


def test_very_large_read_file_result_keeps_head_and_tail():
    content = "HEAD\n" + ("body\n" * 4000) + "TAIL"
    compacted = tool_result_for_model("read_file", {"path": "large.py", "content": content})

    assert compacted["path"] == "large.py"
    assert compacted["content"].startswith("HEAD")
    assert compacted["content"].endswith("TAIL")
    assert "tool output clipped" in compacted["content"]
    assert compacted["context_compacted"] is True


def test_run_command_result_extracts_important_lines_and_clips_streams():
    stdout = "ok\n" * 5000
    stderr = "Traceback (most recent call last):\nSyntaxError: bad syntax\n" + ("noise\n" * 5000)
    result = {
        "command": "python -m pytest -q",
        "cwd": ".",
        "returncode": 1,
        "timed_out": False,
        "duration_ms": 123,
        "summary": "Exit 1: SyntaxError",
        "stdout": stdout,
        "stderr": stderr,
    }

    compacted = tool_result_for_model("run_command", result)

    assert compacted["returncode"] == 1
    assert len(compacted["stdout"]) < len(stdout)
    assert len(compacted["stderr"]) < len(stderr)
    assert any("Traceback" in line for line in compacted["important_lines"])
    assert any("SyntaxError" in line for line in compacted["important_lines"])


def test_search_file_result_limits_matches():
    matches = [
        {"path": f"file_{idx}.py", "line_number": idx, "snippet": "x" * 2000}
        for idx in range(30)
    ]

    compacted = tool_result_for_model("search_file", {"query": "x", "matches": matches, "count": 30})

    assert len(compacted["matches"]) == 20
    assert compacted["matches_omitted"] == 10
    assert compacted["context_compacted"] is True
    assert len(compacted["matches"][0]["snippet"]) < 2000


def test_list_files_result_limits_items():
    items = [{"path": f"file_{idx}.py", "type": "file"} for idx in range(150)]

    compacted = tool_result_for_model("list_files", {"items": items, "count": 150})

    assert len(compacted["items"]) == 120
    assert compacted["items_omitted"] == 30


def test_tool_result_json_for_model_is_valid_json():
    text = tool_result_json_for_model("run_command", {"stdout": "ok", "stderr": "", "returncode": 0})

    assert json.loads(text)["returncode"] == 0


def test_failed_tool_result_includes_recovery_hint_for_model():
    text = tool_result_json_for_model("read_file", {"error": "File not found: missing.py"})
    payload = json.loads(text)

    assert payload["recovery"]["category"] == "path_not_found"
    assert payload["recovery"]["retryable"] is True


def test_failed_command_result_includes_recovery_hint_for_model():
    compacted = tool_result_for_model(
        "run_command",
        {
            "command": "python -m pytest -q",
            "returncode": 1,
            "stderr": "SyntaxError: invalid syntax",
            "stdout": "",
        },
    )

    assert compacted["recovery"]["category"] == "syntax_error"


def test_failed_command_result_includes_failure_diagnostics_for_model():
    compacted = tool_result_for_model(
        "run_command",
        {
            "command": "python -m pytest -q",
            "returncode": 1,
            "stdout": "FAILED tests/test_context.py::test_context_failure\n",
            "stderr": "",
        },
    )

    assert compacted["diagnostics"][0]["kind"] == "pytest_failed_node"
    assert compacted["diagnostics"][0]["nodeid"] == "tests/test_context.py::test_context_failure"


def test_find_symbol_result_limits_matches():
    result = {
        "query": "Service",
        "kind": None,
        "exact": False,
        "matches": [
            {"name": f"Service{idx}", "kind": "class", "path": "kagent/service.py", "line": idx}
            for idx in range(60)
        ],
    }

    compacted = tool_result_for_model("find_symbol", result)

    assert compacted["count"] == 60
    assert len(compacted["matches"]) == 50
    assert compacted["matches_omitted"] == 10


def test_find_symbol_context_result_compacts_content():
    content = "x" * 7000
    result = {
        "query": "build_plan",
        "contexts": [
            {
                "name": "build_plan",
                "kind": "function",
                "path": "kagent/module.py",
                "line": 10,
                "start_line": 8,
                "symbol_start_line": 10,
                "symbol_end_line": 12,
                "content": content,
            }
        ],
    }

    compacted = tool_result_for_model("find_symbol_context", result)

    assert compacted["count"] == 1
    assert compacted["contexts"][0]["path"] == "kagent/module.py"
    assert compacted["contexts"][0]["content_chars"] == len(content)
    assert len(compacted["contexts"][0]["content"]) < len(content)
    assert compacted["context_compacted"] is True


def test_find_symbol_references_result_limits_references_and_counts_tests():
    result = {
        "query": "build_plan",
        "include_tests": True,
        "references": [
            {
                "symbol": "build_plan",
                "path": f"tests/test_{idx}.py",
                "line": idx + 1,
                "reference_type": "call",
                "excerpt": "build_plan()",
                "is_test": True,
            }
            for idx in range(90)
        ],
    }

    compacted = tool_result_for_model("find_symbol_references", result)

    assert compacted["count"] == 90
    assert compacted["test_reference_count"] == 90
    assert len(compacted["references"]) == 80
    assert compacted["references_omitted"] == 10
    assert compacted["context_compacted"] is True


def test_tool_result_for_model_keeps_change_plan():
    compacted = tool_result_for_model(
        "write_file",
        {
            "path": "kagent/context.py",
            "summary": "Updated file",
            "change_plan": {
                "operation": "write",
                "paths": ["kagent/context.py"],
                "summary": "Plan to write",
            },
        },
    )

    assert compacted["change_plan"]["operation"] == "write"
    assert compacted["change_plan"]["paths"] == ["kagent/context.py"]
