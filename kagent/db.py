import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import DB_PATH, WORKSPACE_ROOT

_lock = threading.Lock()


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _lock, _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                workspace_root TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        columns = {
            str(row["name"])
            for row in c.execute("PRAGMA table_info(sessions)").fetchall()
        }
        if "workspace_root" not in columns:
            c.execute("ALTER TABLE sessions ADD COLUMN workspace_root TEXT")
        c.execute(
            "UPDATE sessions SET workspace_root = ? WHERE workspace_root IS NULL OR workspace_root = ''",
            (_normalize_workspace_root(WORKSPACE_ROOT),),
        )
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)"
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS context_summaries (
                session_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                through_message_id INTEGER NOT NULL DEFAULT 0,
                source_message_count INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS rollback_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                summary TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_rollbacks_session_status ON rollback_entries(session_id, status, id DESC)"
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS project_memories (
                workspace_root TEXT PRIMARY KEY,
                memory TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'auto',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def create_session(
    session_id: str,
    title: str = "新对话",
    workspace_root: str | None = None,
) -> None:
    stored_workspace = (
        _normalize_workspace_root(WORKSPACE_ROOT)
        if workspace_root is None
        else _normalize_workspace_root(workspace_root)
    )
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO sessions (id, title, workspace_root) VALUES (?, ?, ?)",
            (session_id, title, stored_workspace),
        )


def rename_session(session_id: str, title: str) -> None:
    with _lock, _conn() as c:
        c.execute(
            "UPDATE sessions SET title = ? WHERE id = ?",
            (title, session_id),
        )


def list_sessions() -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT id, title, workspace_root, created_at FROM sessions ORDER BY created_at DESC"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "workspace_root": r["workspace_root"] if r["workspace_root"] is not None else "",
                "created_at": r["created_at"],
            }
            for r in rows
        ]


def get_session(session_id: str) -> dict | None:
    with _lock, _conn() as c:
        row = c.execute(
            "SELECT id, title, workspace_root, created_at FROM sessions WHERE id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "workspace_root": row["workspace_root"] if row["workspace_root"] is not None else "",
            "created_at": row["created_at"],
        }


def set_session_workspace_root(session_id: str, workspace_root: str) -> None:
    with _lock, _conn() as c:
        c.execute(
            "UPDATE sessions SET workspace_root = ? WHERE id = ?",
            (_normalize_workspace_root(workspace_root), session_id),
        )


def delete_session(session_id: str) -> None:
    with _lock, _conn() as c:
        c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        c.execute("DELETE FROM context_summaries WHERE session_id = ?", (session_id,))
        c.execute("DELETE FROM rollback_entries WHERE session_id = ?", (session_id,))
        c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def save_message(session_id: str, role: str, content: str) -> None:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )


def get_messages(session_id: str) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]


def get_context_summary(session_id: str) -> dict | None:
    with _lock, _conn() as c:
        row = c.execute(
            """
            SELECT session_id, summary, through_message_id, source_message_count, updated_at
            FROM context_summaries
            WHERE session_id = ?
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "session_id": row["session_id"],
            "summary": row["summary"],
            "through_message_id": row["through_message_id"],
            "source_message_count": row["source_message_count"],
            "updated_at": row["updated_at"],
        }


def save_context_summary(
    session_id: str,
    summary: str,
    through_message_id: int,
    source_message_count: int,
) -> None:
    with _lock, _conn() as c:
        c.execute(
            """
            INSERT INTO context_summaries (
                session_id, summary, through_message_id, source_message_count, updated_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                summary = excluded.summary,
                through_message_id = excluded.through_message_id,
                source_message_count = excluded.source_message_count,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                session_id,
                summary,
                int(through_message_id),
                int(source_message_count),
            ),
        )


def get_project_memory(workspace_root: str) -> dict | None:
    with _lock, _conn() as c:
        row = c.execute(
            """
            SELECT workspace_root, memory, source, updated_at
            FROM project_memories
            WHERE workspace_root = ?
            LIMIT 1
            """,
            (workspace_root,),
        ).fetchone()
        if row is None:
            return None
        return {
            "workspace_root": row["workspace_root"],
            "memory": json.loads(row["memory"]),
            "source": row["source"],
            "updated_at": row["updated_at"],
        }


def save_project_memory(workspace_root: str, memory: dict, source: str = "auto") -> None:
    with _lock, _conn() as c:
        c.execute(
            """
            INSERT INTO project_memories (workspace_root, memory, source, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(workspace_root) DO UPDATE SET
                memory = excluded.memory,
                source = excluded.source,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                workspace_root,
                json.dumps(memory, ensure_ascii=False),
                source,
            ),
        )


def save_rollback_entry(
    session_id: str,
    tool_name: str,
    summary: str,
    payload: dict,
) -> int:
    with _lock, _conn() as c:
        cur = c.execute(
            """
            INSERT INTO rollback_entries (session_id, tool_name, summary, payload)
            VALUES (?, ?, ?, ?)
            """,
            (
                session_id,
                tool_name,
                summary,
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        return int(cur.lastrowid)


def get_latest_rollback_entry(session_id: str) -> dict | None:
    with _lock, _conn() as c:
        row = c.execute(
            """
            SELECT id, session_id, tool_name, summary, payload, status, created_at
            FROM rollback_entries
            WHERE session_id = ? AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "tool_name": row["tool_name"],
            "summary": row["summary"],
            "payload": json.loads(row["payload"]),
            "status": row["status"],
            "created_at": row["created_at"],
        }


def get_rollback_entry(session_id: str, entry_id: int) -> dict | None:
    with _lock, _conn() as c:
        row = c.execute(
            """
            SELECT id, session_id, tool_name, summary, payload, status, created_at
            FROM rollback_entries
            WHERE session_id = ? AND id = ?
            LIMIT 1
            """,
            (session_id, int(entry_id)),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "tool_name": row["tool_name"],
            "summary": row["summary"],
            "payload": json.loads(row["payload"]),
            "status": row["status"],
            "created_at": row["created_at"],
        }


def update_rollback_entry_payload(entry_id: int, payload: dict) -> None:
    with _lock, _conn() as c:
        c.execute(
            "UPDATE rollback_entries SET payload = ? WHERE id = ?",
            (json.dumps(payload, ensure_ascii=False), int(entry_id)),
        )


def list_rollback_entries(
    session_id: str,
    limit: int = 20,
    include_inactive: bool = True,
) -> list[dict]:
    query = """
        SELECT id, session_id, tool_name, summary, payload, status, created_at
        FROM rollback_entries
        WHERE session_id = ?
    """
    params: list[object] = [session_id]
    if not include_inactive:
        query += " AND status = 'active'"
    query += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, int(limit)))

    with _lock, _conn() as c:
        rows = c.execute(query, tuple(params)).fetchall()
        return [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "tool_name": row["tool_name"],
                "summary": row["summary"],
                "payload": json.loads(row["payload"]),
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]


def mark_rollback_entry_applied(entry_id: int) -> None:
    with _lock, _conn() as c:
        c.execute(
            "UPDATE rollback_entries SET status = 'applied' WHERE id = ?",
            (entry_id,),
        )


def mark_rollback_entries_superseded_after(session_id: str, entry_id: int) -> int:
    with _lock, _conn() as c:
        cur = c.execute(
            """
            UPDATE rollback_entries
            SET status = 'superseded'
            WHERE session_id = ? AND status = 'active' AND id > ?
            """,
            (session_id, int(entry_id)),
        )
        return int(cur.rowcount or 0)


def _normalize_workspace_root(path: str) -> str:
    if str(path).strip() == "":
        return ""
    return str(Path(path).expanduser().resolve())
