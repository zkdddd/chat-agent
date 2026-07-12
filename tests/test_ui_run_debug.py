from kagent.agent.run_log import RunLogger
from kagent.ui.main_window import (
    _diff_review_markdown,
    _resume_task_prompt,
    _run_debug_markdown,
    _session_workspace_summary,
    _session_title_for_workspace,
    _tool_entry_actions,
    _tool_event_markdown,
    _t,
    _workspace_button_label,
)


def test_run_debug_markdown_includes_summary_and_self_check(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))
    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "zh")

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.write("tool_call", {"name": "read_file"})
    logger.finish("completed", {"validated": True, "changed_paths": []})

    markdown = _run_debug_markdown(str(logger.path), "summary")

    assert "运行摘要" in markdown
    assert "自检结果" in markdown
    assert "health: pass" in markdown
    assert "tools: read_file x1" in markdown


def test_run_debug_markdown_includes_timeline(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))
    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "zh")

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.write("agent_status", {"phase": "planning", "detail": "Planning"})
    logger.finish("completed")

    markdown = _run_debug_markdown(str(logger.path), "timeline")

    assert "运行时间线" in markdown
    assert "Run started" in markdown
    assert "Phase: planning" in markdown
    assert "Planning" in markdown


def test_diff_review_markdown_includes_active_paths_and_preview(monkeypatch):
    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "zh")
    markdown = _diff_review_markdown(
        {
            "available": True,
            "summary": "2 active rollbackable paths",
            "paths": ["kagent/a.py", "tests/test_a.py"],
            "preview": "diff --git a/kagent/a.py b/kagent/a.py\n@@ -1 +1 @@\n-old\n+new\n",
        }
    )

    assert "当前差异审查" in markdown
    assert "**状态**: 可用" in markdown
    assert "`kagent/a.py`" in markdown
    assert "```diff" in markdown
    assert "+new" in markdown


def test_diff_review_markdown_handles_empty_preview(monkeypatch):
    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "zh")
    markdown = _diff_review_markdown({"available": False, "paths": []})

    assert "**状态**: 空" in markdown
    assert "当前会话没有可回滚的活跃变更" in markdown


def test_resume_task_prompt_wraps_context_for_agent(monkeypatch):
    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "zh")
    prompt = _resume_task_prompt(
        {
            "run_id": "run-1",
            "status": "stopped",
            "health": "warn",
            "priority": "continue_incomplete_plan",
            "resume_prompt": "Continue from the next unfinished plan step.",
        }
    )

    assert "继续上一次 Agent 任务" in prompt
    assert "run_id: run-1" in prompt
    assert "priority: continue_incomplete_plan" in prompt
    assert "Continue from the next unfinished plan step." in prompt


def test_ui_markdown_uses_english_language(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "en")
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(tmp_path))

    logger = RunLogger(session_id="session-1", workspace_root=str(tmp_path))
    logger.finish("completed", {"validated": True})

    debug = _run_debug_markdown(str(logger.path), "summary")
    diff = _diff_review_markdown({"available": False, "paths": []})
    prompt = _resume_task_prompt({"run_id": "run-1", "priority": "continue_next_plan_step"})

    assert "Run Summary" in debug
    assert "Self Check" in debug
    assert "**Status**: empty" in diff
    assert "No active rollbackable changes" in diff
    assert "Continue the previous Agent task" in prompt


def test_tool_options_use_selected_language(monkeypatch):
    result = {"entries": [{"rollback_id": 7, "available": True}]}

    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "zh")
    zh_actions = _tool_entry_actions("list_rollback_history", result=result)
    zh_markdown = _tool_event_markdown("read_file", status="执行中", args={"path": "README.md"})

    assert zh_actions[0]["label"] == "差异 #7"
    assert "只展示差异预览" in zh_actions[0]["prompt"]
    assert "**状态** 执行中" in zh_markdown
    assert "**输入**" in zh_markdown

    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "en")
    en_actions = _tool_entry_actions("list_rollback_history", result=result)
    en_markdown = _tool_event_markdown("read_file", status="Running", args={"path": "README.md"})

    assert en_actions[0]["label"] == "Diff #7"
    assert "Show the diff preview only" in en_actions[0]["prompt"]
    assert "**Status** Running" in en_markdown
    assert "**Input**" in en_markdown


def test_session_title_for_workspace_uses_folder_name(tmp_path):
    project = tmp_path / "target-project"
    project.mkdir()

    assert _session_title_for_workspace(project) == "target-project"


def test_session_workspace_summary_distinguishes_project_and_no_folder(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "en")
    project = tmp_path / "target-project"
    project.mkdir()

    project_summary = _session_workspace_summary(
        {
            "workspace_root": str(project),
            "created_at": "2026-07-13 09:30:00",
        },
        current=True,
    )
    no_folder_summary = _session_workspace_summary({"workspace_root": "", "created_at": ""})

    assert "target-project" in project_summary
    assert "Created 07-13 09:30" in project_summary
    assert "Current" in project_summary
    assert no_folder_summary == "Normal chat · No file access"


def test_workspace_button_label_shows_current_project_folder(tmp_path, monkeypatch):
    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "zh")
    project = tmp_path / "target-project"
    project.mkdir()

    assert _workspace_button_label(project) == "当前项目：target-project"


def test_new_chat_label_distinguishes_normal_chat_from_folder_picker(monkeypatch):
    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "zh")
    assert _t("new_chat") == "+  新增会话"
    assert _t("new_chat_for_folder") == "+  选择文件夹新建会话"
    assert _t("clear_workspace") == "不选择文件夹"

    monkeypatch.setattr("kagent.config.APP_LANGUAGE", "en")
    assert _t("new_chat") == "+  New chat"
    assert _t("new_chat_for_folder") == "+  New chat from folder"
    assert _t("clear_workspace") == "No folder"
