from pathlib import Path

from kagent import db


def test_session_workspace_root_defaults_and_updates(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.db.DB_PATH", str(tmp_path / "kagent.db"))
    monkeypatch.setattr("kagent.db.WORKSPACE_ROOT", str(tmp_path / "default"))
    (tmp_path / "default").mkdir()
    (tmp_path / "project").mkdir()

    db.init_db()
    db.create_session("session-1", "Session 1")
    db.create_session("session-2", "Session 2", workspace_root=str(tmp_path / "project"))

    first = db.get_session("session-1")
    second = db.get_session("session-2")

    assert first["workspace_root"] == str((tmp_path / "default").resolve())
    assert second["workspace_root"] == str((tmp_path / "project").resolve())

    db.set_session_workspace_root("session-1", str(tmp_path / "project"))

    updated = db.get_session("session-1")
    sessions = db.list_sessions()

    assert updated["workspace_root"] == str((tmp_path / "project").resolve())
    assert all("workspace_root" in session for session in sessions)


def test_session_workspace_root_can_be_empty_for_chat_only_session(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.db.DB_PATH", str(tmp_path / "kagent.db"))
    monkeypatch.setattr("kagent.db.WORKSPACE_ROOT", str(tmp_path / "default"))
    (tmp_path / "default").mkdir()

    db.init_db()
    db.create_session("chat-only", "Chat Only", workspace_root="")

    session = db.get_session("chat-only")

    assert session["workspace_root"] == ""


def test_init_db_migrates_existing_sessions_without_workspace_root(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.db.DB_PATH", str(tmp_path / "kagent.db"))
    monkeypatch.setattr("kagent.db.WORKSPACE_ROOT", str(tmp_path / "default"))
    (tmp_path / "default").mkdir()

    import sqlite3

    with sqlite3.connect(tmp_path / "kagent.db") as conn:
        conn.execute(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, title TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.execute("INSERT INTO sessions (id, title) VALUES (?, ?)", ("old", "Old"))
        conn.commit()

    db.init_db()

    session = db.get_session("old")

    assert session["workspace_root"] == str(Path(tmp_path / "default").resolve())
