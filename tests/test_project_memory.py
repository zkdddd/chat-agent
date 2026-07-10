from kagent import db
from kagent.agent.project_memory import (
    build_project_memory,
    format_project_memory_for_prompt,
    load_or_refresh_project_memory,
)


def test_project_memory_builds_stable_project_facts(tmp_path):
    _write_project(tmp_path)

    memory = build_project_memory(tmp_path)

    assert memory["project_type"] == "python"
    assert memory["project_summary"]["source_count"] == 2
    assert memory["project_summary"]["test_count"] == 1
    assert memory["entry_files"] == ["main.py"]
    assert "requirements.txt" in memory["config_files"]
    assert any(item["command"] == "run-tests.bat" for item in memory["validation_commands"])
    assert "Use run-tests.bat as the default full validation entrypoint." in memory["preferences"]


def test_project_memory_persists_by_workspace_root(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.db.DB_PATH", str(tmp_path / "kagent.db"))
    db.init_db()
    project = tmp_path / "project"
    project.mkdir()
    _write_project(project)

    first = load_or_refresh_project_memory(project)
    second = load_or_refresh_project_memory(project)
    stored = db.get_project_memory(str(project.resolve()))

    assert first == second
    assert stored is not None
    assert stored["memory"]["workspace_root"] == str(project.resolve())


def test_format_project_memory_for_prompt_is_compact_and_actionable(tmp_path):
    _write_project(tmp_path)
    memory = build_project_memory(tmp_path)

    prompt = format_project_memory_for_prompt(memory)

    assert "Long-term project memory." in prompt
    assert "project_type: python" in prompt
    assert "entry_files: main.py" in prompt
    assert "Full project validation: `run-tests.bat`" in prompt
    assert "Document every feature or optimization" in prompt


def _write_project(root):
    (root / "kagent").mkdir(exist_ok=True)
    (root / "tests").mkdir(exist_ok=True)
    (root / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "kagent" / "context.py").write_text("def manage_context(): pass\n", encoding="utf-8")
    (root / "tests" / "test_context.py").write_text("def test_context(): pass\n", encoding="utf-8")
    (root / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (root / "run-tests.bat").write_text("python -m pytest -q\n", encoding="utf-8")
