from kagent.agent.project_rules import (
    RULES_FILENAME,
    check_project_rules,
    format_project_rules_health_for_prompt,
    format_project_rules_for_prompt,
    generate_project_rules,
    load_project_rules,
)
from kagent.agent.code_agent import CodeAgent
from kagent.agent.tool_schema import tool_schema


def test_load_project_rules_tolerates_missing_file(tmp_path):
    result = load_project_rules(tmp_path)

    assert result["ok"] is True
    assert result["exists"] is False
    assert result["path"] == RULES_FILENAME
    assert format_project_rules_for_prompt(result) == ""


def test_load_project_rules_reads_and_formats_prompt(tmp_path):
    (tmp_path / RULES_FILENAME).write_text(
        "# KAGENT.md\n\n- Run `python -m pytest` before final replies.\n",
        encoding="utf-8",
    )

    result = load_project_rules(tmp_path)
    prompt = format_project_rules_for_prompt(result)

    assert result["ok"] is True
    assert result["exists"] is True
    assert "Run `python -m pytest`" in result["content"]
    assert "Project rules from KAGENT.md." in prompt
    assert "Follow these explicit project rules" in prompt


def test_load_project_rules_clips_large_content(tmp_path):
    (tmp_path / RULES_FILENAME).write_text("HEAD\n" + ("x" * 2000) + "\nTAIL", encoding="utf-8")

    result = load_project_rules(tmp_path, max_chars=200)
    prompt = format_project_rules_for_prompt(result)

    assert result["truncated"] is True
    assert "[... clipped ...]" in result["content"]
    assert "Project rules were clipped" in prompt


def test_generate_project_rules_draft_uses_project_facts(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "run-tests.bat").write_text("python -m pytest -q\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    result = generate_project_rules(tmp_path)

    assert result["ok"] is True
    assert result["path"] == RULES_FILENAME
    assert "# KAGENT.md" in result["content"]
    assert "run-tests.bat" in result["content"]
    assert "Preserve unrelated user changes" in result["content"]


def test_check_project_rules_returns_draft_when_missing(tmp_path):
    result = check_project_rules(tmp_path)
    prompt = format_project_rules_health_for_prompt(result)

    assert result["ok"] is True
    assert result["exists"] is False
    assert result["health"] == "missing"
    assert result["issues"][0]["kind"] == "missing_file"
    assert "# KAGENT.md" in result["suggested_additions"][0]
    assert "Project rules health check for KAGENT.md." in prompt
    assert "missing_file" in prompt


def test_check_project_rules_reports_missing_validation_and_safety(tmp_path):
    (tmp_path / RULES_FILENAME).write_text(
        "# KAGENT.md\n\n## Project Overview\n\n- Small project.\n\n## Coding Rules\n\n- Keep edits small.\n",
        encoding="utf-8",
    )

    result = check_project_rules(tmp_path)
    issue_kinds = {issue["kind"] for issue in result["issues"]}

    assert result["ok"] is True
    assert result["health"] in {"needs_attention", "weak"}
    assert "missing_validation" in issue_kinds
    assert "missing_safety" in issue_kinds
    assert "missing_validation_command" in issue_kinds
    assert result["suggested_additions"]


def test_check_project_rules_accepts_complete_rules(tmp_path):
    (tmp_path / RULES_FILENAME).write_text(
        "\n".join(
            [
                "# KAGENT.md",
                "## Project Overview",
                "- Project.",
                "## Coding Rules",
                "- Preserve unrelated user changes in the working tree.",
                "- Document every feature or optimization in `README.md` and `docs/agent-development.md`.",
                "## Validation",
                "- Run `python -m pytest`.",
                "## Safety",
                "- Do not run destructive git or filesystem commands unless the user explicitly asks.",
            ]
        ),
        encoding="utf-8",
    )

    result = check_project_rules(tmp_path)

    assert result["ok"] is True
    assert result["exists"] is True
    assert result["health"] == "good"
    assert result["score"] == 100
    assert result["issues"] == []
    assert format_project_rules_health_for_prompt(result) == ""


def test_project_rules_tools_are_available_and_dispatchable(tmp_path):
    tool_names = {item["function"]["name"] for item in tool_schema()}
    agent = CodeAgent(workspace_root=str(tmp_path), session_id="session-1")

    read_result = agent._dispatch_tool("read_project_rules", {})
    generate_result = agent._dispatch_tool("generate_project_rules", {})
    check_result = agent._dispatch_tool("check_project_rules", {})

    assert "read_project_rules" in tool_names
    assert "generate_project_rules" in tool_names
    assert "check_project_rules" in tool_names
    assert read_result["exists"] is False
    assert generate_result["ok"] is True
    assert check_result["ok"] is True
    assert check_result["health"] == "missing"
    assert "# KAGENT.md" in generate_result["content"]
