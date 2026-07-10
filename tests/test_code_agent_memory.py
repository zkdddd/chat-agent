from types import SimpleNamespace

from kagent import db
from kagent.agent.code_agent import AgentRunState, CodeAgent


def test_code_agent_injects_project_memory_into_model_messages(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.db.DB_PATH", str(tmp_path / "kagent.db"))
    monkeypatch.setattr("kagent.agent.workspace.ROLLBACK_ROOT", str(tmp_path / "rollback"))
    db.init_db()

    (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "run-tests.bat").write_text("python -m pytest -q\n", encoding="utf-8")

    captured = {}

    def fake_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        return [_chunk(content="完成")]

    monkeypatch.setattr("kagent.agent.code_agent.client.chat.completions.create", fake_create)

    agent = CodeAgent(workspace_root=str(tmp_path), session_id="session-1")
    report = agent.run([{"role": "user", "content": "说明项目"}], max_rounds=1)

    system_messages = [
        message["content"]
        for message in captured["messages"]
        if message.get("role") == "system"
    ]
    assert "完成" in report
    assert any("Long-term project memory." in content for content in system_messages)
    assert any("run-tests.bat" in content for content in system_messages)


def test_code_agent_final_prompt_includes_trust_check(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.db.DB_PATH", str(tmp_path / "kagent.db"))
    monkeypatch.setattr("kagent.agent.workspace.ROLLBACK_ROOT", str(tmp_path / "rollback"))
    db.init_db()

    agent = CodeAgent(workspace_root=str(tmp_path), session_id="session-1")
    state = AgentRunState(
        content_changed=True,
        changed_paths={"a.py"},
        validated=False,
        validation_failed=False,
    )

    prompt = agent._final_response_prompt(state)

    assert "Final response trust check." in prompt
    assert "unverified_changes" in prompt


def _chunk(content=None, tool_calls=None):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(
                    content=content,
                    tool_calls=tool_calls,
                )
            )
        ],
        close=lambda: None,
    )


def _tool_delta(call_id, name, arguments):
    return SimpleNamespace(
        index=0,
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )
