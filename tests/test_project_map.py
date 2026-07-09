from kagent.agent.project_map import build_project_map, related_tests_for_source, summarize_project_map


def test_build_project_map_classifies_files_and_maps_tests(tmp_path):
    package = tmp_path / "kagent" / "agent"
    package.mkdir(parents=True)
    (tmp_path / "kagent" / "context.py").write_text("def manage(): pass\n", encoding="utf-8")
    (package / "validation.py").write_text("def validate(): pass\n", encoding="utf-8")
    tests = tmp_path / "tests" / "agent"
    tests.mkdir(parents=True)
    (tmp_path / "tests" / "test_context.py").write_text("def test_context(): pass\n", encoding="utf-8")
    (tests / "test_validation.py").write_text("def test_validation(): pass\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")

    project_map = build_project_map(tmp_path)

    assert "kagent/context.py" in project_map.source_files
    assert "kagent/agent/validation.py" in project_map.source_files
    assert "tests/test_context.py" in project_map.test_files
    assert "tests/agent/test_validation.py" in project_map.test_files
    assert "requirements.txt" in project_map.config_files
    assert "main.py" in project_map.entry_files
    assert project_map.source_to_tests["kagent/context.py"] == ["tests/test_context.py"]
    assert project_map.source_to_tests["kagent/agent/validation.py"] == [
        "tests/agent/test_validation.py"
    ]


def test_related_tests_for_source_uses_common_python_conventions():
    tests = ["tests/test_context.py", "tests/agent/test_validation.py"]

    assert related_tests_for_source("kagent/context.py", tests) == ["tests/test_context.py"]
    assert related_tests_for_source("kagent/agent/validation.py", tests) == [
        "tests/agent/test_validation.py"
    ]


def test_summarize_project_map_counts_files(tmp_path):
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text("def test_main(): pass\n", encoding="utf-8")

    summary = summarize_project_map(build_project_map(tmp_path))

    assert summary["source_count"] == 1
    assert summary["test_count"] == 1
    assert summary["mapped_source_count"] == 1
