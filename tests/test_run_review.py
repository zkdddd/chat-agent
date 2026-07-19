from kagent.agent.run_log import RunLogger
from kagent.agent.run_review import build_run_review, format_run_review_markdown


def test_build_run_review_summarizes_clean_run(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.write("run_context", {"task": "Add run review core"})
    logger.write("model_request", {"model": "gpt-5.5", "reasoning_effort": "high"})
    logger.write(
        "project_rules_check",
        {
            "path": "KAGENT.md",
            "health": "good",
            "score": 100,
            "issue_count": 0,
            "issues": [],
        },
    )
    logger.finish(
        "completed",
        {
            "validated": True,
            "validation_failed": False,
            "changed_paths": ["kagent/agent/run_review.py"],
            "last_validation_summary": "199 passed",
        },
    )

    review = build_run_review(logger.path)
    markdown = format_run_review_markdown(review)

    assert review["run_id"] == logger.run_id
    assert review["status"] == "completed"
    assert review["workspace"] == str(tmp_path)
    assert review["task"] == "Add run review core"
    assert review["validation"]["validated"] is True
    assert review["validation"]["failed"] is False
    assert review["validation"]["last_summary"] == "199 passed"
    assert review["changed_paths"] == ["kagent/agent/run_review.py"]
    assert review["model_requests"] == [
        {
            "model": "gpt-5.5",
            "reasoning_effort": "high",
            "fallback_without_reasoning": False,
            "count": 1,
        }
    ]
    assert review["project_rules"]["health"] == "good"
    assert review["risk_flags"] == []
    assert review["recommended_next_steps"] == [
        "Review the changed files and keep the recorded validation summary with the final answer."
    ]
    assert "# Run Review" in markdown
    assert "status: `passed/recorded`" in markdown
    assert "`kagent/agent/run_review.py`" in markdown


def test_build_run_review_reports_risks_and_symbol_impacts(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.write("run_context", {"user_task": "Fix validation failure"})
    logger.write(
        "change_plan",
        {
            "plan": {
                "operation": "patch",
                "symbol_impacts": [
                    {
                        "symbol": "build_run_review",
                        "definition_path": "kagent/agent/run_review.py",
                        "reference_count": 2,
                        "related_tests": ["tests/test_run_review.py"],
                        "validation_commands": [
                            {"command": "python -m pytest -q tests/test_run_review.py"}
                        ],
                    }
                ],
            }
        },
    )
    logger.write("model_request", {"model": "gpt-5.5", "reasoning_effort": "high"})
    logger.write(
        "model_error",
        {
            "model": "gpt-5.5",
            "error_type": "ValueError",
            "error": "unsupported parameter: reasoning_effort",
        },
    )
    logger.write(
        "model_request",
        {
            "model": "gpt-5.5",
            "reasoning_effort": None,
            "fallback_without_reasoning": True,
        },
    )
    logger.write("tool_result", {"name": "run_command", "ok": False, "error": "pytest failed"})
    logger.write(
        "project_rules_check",
        {
            "path": "KAGENT.md",
            "health": "weak",
            "score": 40,
            "issue_count": 2,
            "issues": [{"kind": "missing_validation_command", "severity": "high"}],
        },
    )
    logger.finish(
        "completed",
        {
            "validated": True,
            "validation_failed": True,
            "changed_paths": ["kagent/agent/run_review.py"],
            "last_validation_summary": "1 failed",
            "symbol_impacts": [
                {
                    "symbol": "build_run_review",
                    "definition_path": "kagent/agent/run_review.py",
                    "reference_count": 2,
                    "related_tests": ["tests/test_run_review.py"],
                }
            ],
        },
    )

    review = build_run_review(logger.path)
    markdown = format_run_review_markdown(review)

    assert review["task"] == "Fix validation failure"
    assert review["failed_tools"] == [{"name": "run_command", "count": "1", "detail": "pytest failed"}]
    assert review["model_errors"] == [
        {
            "model": "gpt-5.5",
            "error_type": "ValueError",
            "detail": "unsupported parameter: reasoning_effort",
        }
    ]
    assert review["model_requests"][0]["count"] == 1
    assert review["symbol_impacts"] == [
        {
            "symbol": "build_run_review",
            "definition_path": "kagent/agent/run_review.py",
            "reference_count": 2,
            "related_tests": ["tests/test_run_review.py"],
            "validation_commands": ["python -m pytest -q tests/test_run_review.py"],
        }
    ]
    assert review["project_rules"]["health"] == "weak"
    assert review["risk_flags"] == [
        "validation_failed",
        "failed_tools",
        "model_errors",
        "project_rules_need_attention",
    ]
    assert review["recommended_next_steps"][0].startswith("Inspect the last validation failure")
    assert any(
        "Prioritize review and tests around impacted symbols" in step
        for step in review["recommended_next_steps"]
    )
    assert "model_error: `gpt-5.5` ValueError" in markdown
    assert "`build_run_review` at `kagent/agent/run_review.py`" in markdown
    assert "`validation_failed`" in markdown


def test_build_run_review_flags_unfinished_run_without_rules_check(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))

    review = build_run_review(logger.path)

    assert review["status"] == "running/unknown"
    assert review["risk_flags"] == ["run_not_finished", "project_rules_not_checked"]
    assert review["recommended_next_steps"] == [
        "Run a project rules check so local validation, safety, and workflow rules are visible."
    ]
