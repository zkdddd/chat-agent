from kagent import db
from kagent.agent.workspace import WorkspaceTools


def test_preview_rollback_session_lists_active_paths(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    workspace = WorkspaceTools(root=tmp_path, session_id="session-1")
    (tmp_path / "a.txt").write_text("before\n", encoding="utf-8")

    workspace.write_file("a.txt", "after\n")

    preview = workspace.preview_rollback_session()

    assert preview["available"] is True
    assert preview["paths"] == ["a.txt"]
    assert preview["path_count"] == 1
    assert "a.txt" in preview["preview"]


def test_rollback_previews_include_symbol_impacts(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    workspace = WorkspaceTools(root=tmp_path, session_id="session-1")
    package = tmp_path / "kagent" / "agent"
    package.mkdir(parents=True)
    target = package / "validation.py"
    target.write_text("def build_validation_plan():\n    return []\n", encoding="utf-8")

    result = workspace.write_file(
        "kagent/agent/validation.py",
        "def build_validation_plan():\n    return ['ok']\n",
    )
    workspace.annotate_rollback_symbol_impacts(
        result["rollback_id"],
        [
            {
                "symbol": "build_validation_plan",
                "definition_path": "kagent/agent/validation.py",
                "reference_count": 12,
                "related_tests": ["tests/test_validation.py"],
            }
        ],
    )

    history = workspace.list_rollback_history()
    session_preview = workspace.preview_rollback_session()
    change_preview = workspace.preview_rollback_change(result["rollback_id"])

    assert history["entries"][0]["symbol_impacts"][0]["symbol"] == "build_validation_plan"
    assert session_preview["symbol_impacts"][0]["definition_path"] == "kagent/agent/validation.py"
    assert change_preview["symbol_impacts"][0]["related_tests"] == ["tests/test_validation.py"]
    assert change_preview["diff_entries"][0]["symbol_impacts"][0]["symbol"] == "build_validation_plan"


def test_rollback_paths_restores_only_selected_file(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    workspace = WorkspaceTools(root=tmp_path, session_id="session-1")
    (tmp_path / "a.txt").write_text("a-before\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b-before\n", encoding="utf-8")

    workspace.write_file("a.txt", "a-after\n")
    workspace.write_file("b.txt", "b-after\n")

    preview = workspace.preview_rollback_paths(["a.txt"])
    result = workspace.rollback_paths(["a.txt"])

    assert preview["available"] is True
    assert preview["paths"] == ["a.txt"]
    assert result["ok"] is True
    assert result["paths"] == ["a.txt"]
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "a-before\n"
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "b-after\n"


def test_rollback_paths_can_restore_selected_path_from_multi_file_entry(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    workspace = WorkspaceTools(root=tmp_path, session_id="session-1")
    (tmp_path / "a.txt").write_text("a-before\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b-before\n", encoding="utf-8")
    patch = """diff --git a/a.txt b/a.txt
--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-a-before
+a-after
diff --git a/b.txt b/b.txt
--- a/b.txt
+++ b/b.txt
@@ -1 +1 @@
-b-before
+b-after
"""

    applied = workspace.apply_patch(patch)
    preview = workspace.preview_rollback_paths(["a.txt"], rollback_id=applied["rollback_id"])
    result = workspace.rollback_paths(["a.txt"], rollback_id=applied["rollback_id"])
    history = workspace.list_rollback_history(include_inactive=False)

    assert preview["paths"] == ["a.txt"]
    assert result["paths"] == ["a.txt"]
    assert result["results"][0]["remaining_rollback_id"] is not None
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "a-before\n"
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "b-after\n"
    assert any(item["paths"] == ["b.txt"] for item in history["entries"])


def test_preview_rollback_paths_reports_missing_path(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    workspace = WorkspaceTools(root=tmp_path, session_id="session-1")
    (tmp_path / "a.txt").write_text("before\n", encoding="utf-8")

    workspace.write_file("a.txt", "after\n")
    preview = workspace.preview_rollback_paths(["missing.txt"])

    assert preview["available"] is False
    assert preview["missing_paths"] == ["missing.txt"]


def _setup_db(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.db.DB_PATH", str(tmp_path / "kagent.db"))
    monkeypatch.setattr("kagent.agent.workspace.ROLLBACK_ROOT", str(tmp_path / "rollback"))
    db.init_db()
    db.create_session("session-1", "Session 1")
