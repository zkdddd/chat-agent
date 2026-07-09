from kagent.agent.impact_analysis import (
    related_test_commands_for_changes,
    related_tests_for_changes,
)


def test_related_tests_for_top_level_module(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_context.py").write_text("def test_ok(): pass\n", encoding="utf-8")

    related = related_tests_for_changes({"kagent/context.py"}, workspace_root=tmp_path)

    assert related == ["tests/test_context.py"]


def test_related_tests_for_nested_module(tmp_path):
    target = tmp_path / "tests" / "agent"
    target.mkdir(parents=True)
    (target / "test_validation.py").write_text("def test_ok(): pass\n", encoding="utf-8")

    related = related_tests_for_changes({"kagent/agent/validation.py"}, workspace_root=tmp_path)

    assert related == ["tests/agent/test_validation.py"]


def test_related_tests_keeps_changed_test_file(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_validation.py").write_text("def test_ok(): pass\n", encoding="utf-8")

    related = related_tests_for_changes({"tests/test_validation.py"}, workspace_root=tmp_path)

    assert related == ["tests/test_validation.py"]


def test_related_test_commands_use_pytest(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_context.py").write_text("def test_ok(): pass\n", encoding="utf-8")

    commands = related_test_commands_for_changes(
        {"kagent/context.py"},
        workspace_root=tmp_path,
        cwd=".",
    )

    assert len(commands) == 1
    assert commands[0]["label"] == "Related tests"
    assert "pytest" in commands[0]["command"]
    assert "tests/test_context.py" in commands[0]["command"]
