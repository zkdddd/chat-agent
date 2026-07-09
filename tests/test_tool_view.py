from kagent.agent.tool_view import tool_report_section


def test_tool_report_section_uses_readable_chinese_labels():
    report = tool_report_section(
        "read_file",
        {"path": "kagent/context.py"},
        {"ok": True},
        preview="--- before\n+++ after",
    )

    assert "**输入**" in report
    assert "**预览**" in report
    assert "**结果**" in report


def test_tool_report_section_includes_change_plan():
    report = tool_report_section(
        "apply_patch",
        {"files_touched": ["kagent/context.py"]},
        {"ok": True},
        change_plan={
            "operation": "patch",
            "paths": ["kagent/context.py"],
            "summary": "Plan to patch",
        },
    )

    assert "**变更计划**" in report
    assert "Plan to patch" in report
