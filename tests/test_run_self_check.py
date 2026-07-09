from kagent.agent.run_log import RunLogger
from kagent.agent.run_self_check import (
    analyze_latest_run_health,
    analyze_run_health,
    analyze_run_health_by_id,
    format_run_health_report,
)


def test_analyze_run_health_passes_clean_completed_run(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.finish("completed", {"validated": False, "changed_paths": []})

    health = analyze_run_health(logger.path)

    assert health["health"] == "pass"
    assert health["trustworthy"] is True
    assert health["issues"] == []


def test_analyze_run_health_fails_unverified_code_changes(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.finish(
        "completed",
        {
            "validated": False,
            "changed_paths": ["kagent/agent/run_self_check.py"],
        },
    )

    health = analyze_run_health(logger.path)

    assert health["health"] == "fail"
    assert health["trustworthy"] is False
    assert health["changed_paths"] == ["kagent/agent/run_self_check.py"]
    assert _issue_codes(health) == ["unverified_changes"]


def test_analyze_run_health_reports_validation_and_runtime_risks(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.write("agent_status", {"phase": "validating"})
    logger.write("tool_result", {"name": "run_command", "result": {"ok": False, "summary": "pytest failed"}})
    logger.write("tool_loop_warning", {"message": "Repeated command"})
    logger.write("patch_recovery", {"summary": "Recovered patch context"})
    logger.write("failure_focus", {"targets": [{"path": "tests/test_app.py", "line": 3}]})
    logger.finish(
        "completed",
        {
            "validated": True,
            "validation_failed": True,
            "changed_paths": ["kagent/app.py"],
            "last_validation_summary": "1 failed",
        },
    )

    health = analyze_run_health(logger.path)
    report = format_run_health_report(logger.path)

    assert health["health"] == "fail"
    assert health["validated"] is True
    assert health["validation_failed"] is True
    assert health["failed_tools"] == [
        {"name": "run_command", "count": "1", "detail": "pytest failed"}
    ]
    assert health["loop_warning_count"] == 1
    assert health["patch_recovery_count"] == 1
    assert health["failure_focus_count"] == 1
    assert _issue_codes(health) == ["validation_failed", "failed_tools", "loop_warning"]
    assert "health: fail" in report
    assert "trustworthy: no" in report
    assert "run_command x1: pytest failed" in report


def test_analyze_run_health_warns_for_recovered_tool_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.write("tool_result", {"name": "read_file", "ok": False, "error": "missing file"})
    logger.finish(
        "completed",
        {
            "validated": True,
            "validation_failed": False,
            "changed_paths": ["README.md"],
        },
    )

    health = analyze_run_health(logger.path)

    assert health["health"] == "warn"
    assert health["trustworthy"] is False
    assert _issue_codes(health) == ["failed_tools"]


def test_analyze_run_health_fails_incomplete_or_stopped_run(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))

    unfinished = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    stopped = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    stopped.finish("stopped")

    unfinished_health = analyze_run_health(unfinished.path)
    stopped_health = analyze_run_health(stopped.path)

    assert _issue_codes(unfinished_health) == ["run_not_finished"]
    assert _issue_codes(stopped_health) == ["run_not_completed"]
    assert unfinished_health["health"] == "fail"
    assert stopped_health["health"] == "fail"


def test_analyze_latest_and_by_id(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))
    monkeypatch.setattr("kagent.agent.run_log_viewer.STATE_DIR", str(tmp_path))
    monkeypatch.setattr("kagent.agent.run_self_check.STATE_DIR", str(tmp_path))

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.finish("completed")

    assert analyze_latest_run_health()["run_id"] == logger.run_id
    assert analyze_run_health_by_id(logger.run_id)["run_id"] == logger.run_id
    assert analyze_run_health_by_id("missing") is None


def _issue_codes(health):
    return [issue["code"] for issue in health["issues"]]
