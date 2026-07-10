from kagent.agent.run_log import RunLogger
from kagent.ui.main_window import _run_debug_markdown


def test_run_debug_markdown_includes_summary_and_self_check(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.write("tool_call", {"name": "read_file"})
    logger.finish("completed", {"validated": True, "changed_paths": []})

    markdown = _run_debug_markdown(str(logger.path), "summary")

    assert "Run Summary" in markdown
    assert "Self Check" in markdown
    assert "health: pass" in markdown
    assert "tools: read_file x1" in markdown


def test_run_debug_markdown_includes_timeline(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.write("agent_status", {"phase": "planning", "detail": "Planning"})
    logger.finish("completed")

    markdown = _run_debug_markdown(str(logger.path), "timeline")

    assert "Run Timeline" in markdown
    assert "Run started" in markdown
    assert "Phase: planning" in markdown
    assert "Planning" in markdown
