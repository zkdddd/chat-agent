from kagent.ui.agent_worker import AgentWorker


def test_final_answer_from_streamed_agent_report_uses_result_marker():
    report = "### 模型输出\n\n正在分析...\n\n### 结果\n\n最终答案"

    assert AgentWorker._final_answer_from_report(report) == "最终答案"


def test_final_answer_from_report_falls_back_to_report_without_marker():
    report = "plain final answer"

    assert AgentWorker._final_answer_from_report(report) == "plain final answer"
