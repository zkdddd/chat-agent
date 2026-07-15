from kagent.agent.code_agent import CodeAgent
from kagent.agent.run_log import RunLogger
from kagent.agent.self_improve import suggest_self_improvements
from kagent.agent.tool_schema import tool_schema


def test_suggest_self_improvements_returns_ranked_candidates(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr("kagent.agent.run_history.STATE_DIR", str(tmp_path / "runs"))

    package = tmp_path / "kagent" / "agent"
    package.mkdir(parents=True)
    (package / "feature.py").write_text("def run():\n    pass\n", encoding="utf-8")
    (package / "todo.py").write_text("# TODO: improve this\n", encoding="utf-8")
    long_file = package / "large.py"
    long_file.write_text("\n".join("x = 1" for _ in range(520)), encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_existing.py").write_text("def test_existing(): pass\n", encoding="utf-8")

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.finish(
        "completed",
        {
            "validated": True,
            "validation_failed": True,
            "changed_paths": ["kagent/agent/feature.py"],
        },
    )

    result = suggest_self_improvements(tmp_path, limit=5)

    assert result["ok"] is True
    assert result["suggestions"]
    kinds = [item["kind"] for item in result["suggestions"]]
    assert "failed_runs" in kinds
    assert "missing_tests" in kinds
    assert "long_files" in kinds
    assert all(item["action"] for item in result["suggestions"])
    assert all(item["validation"] for item in result["suggestions"])


def test_suggest_self_improvements_is_available_as_agent_tool(tmp_path):
    tool_names = {item["function"]["name"] for item in tool_schema()}
    assert "suggest_self_improvements" in tool_names

    agent = CodeAgent(workspace_root=str(tmp_path), session_id="session-1")
    result = agent._dispatch_tool("suggest_self_improvements", {"limit": 2})

    assert result["ok"] is True
    assert len(result["suggestions"]) <= 2
