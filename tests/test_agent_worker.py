from kagent.ui.agent_worker import AgentWorker


def test_final_answer_from_streamed_agent_report_uses_result_marker():
    report = "### 模型输出\n\n正在分析...\n\n### 结果\n\n最终答案"

    assert AgentWorker._final_answer_from_report(report) == "最终答案"


def test_final_answer_from_report_falls_back_to_report_without_marker():
    report = "plain final answer"

    assert AgentWorker._final_answer_from_report(report) == "plain final answer"


def test_agent_worker_passes_workspace_root_to_code_agent(tmp_path, monkeypatch):
    captured = {}

    class FakeCodeAgent:
        def __init__(self, *, confirm_tool, workspace_root=None, session_id=None, model=None):
            captured["workspace_root"] = workspace_root
            captured["session_id"] = session_id
            captured["model"] = model

        def run(self, history, emit, on_event, should_stop):
            return "### 结果\n\nok"

    monkeypatch.setattr("kagent.ui.agent_worker.CodeAgent", FakeCodeAgent)
    monkeypatch.setattr("kagent.ui.agent_worker.prepare_session_history", lambda history, **kwargs: (history, None))
    monkeypatch.setattr("kagent.ui.agent_worker.db.get_context_summary", lambda session_id: None)
    monkeypatch.setattr("kagent.ui.agent_worker.db.save_message", lambda *args, **kwargs: None)
    monkeypatch.setattr("kagent.ui.agent_worker.AgentWorker._schedule_title_generation", lambda self: None)

    worker = AgentWorker(
        "session-1",
        "continue",
        [{"role": "user", "content": "continue"}],
        workspace_root=str(tmp_path),
        model="gpt-5.5",
    )
    worker.done.connect(lambda answer: captured.setdefault("answer", answer))

    worker.run()

    assert captured["workspace_root"] == str(tmp_path)
    assert captured["session_id"] == "session-1"
    assert captured["model"] == "gpt-5.5"
    assert captured["answer"] == "ok"
