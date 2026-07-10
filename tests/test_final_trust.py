from kagent.agent.final_trust import build_final_trust_summary, final_trust_prompt


def test_final_trust_fails_unverified_changes():
    summary = build_final_trust_summary(
        status="completed",
        content_changed=True,
        changed_paths=["kagent/app.py"],
        validated=False,
        validation_failed=False,
    )

    assert summary["health"] == "fail"
    assert summary["trustworthy"] is False
    assert [issue["code"] for issue in summary["issues"]] == ["unverified_changes"]
    prompt = final_trust_prompt(summary)
    assert "unverified_changes" in prompt
    assert "Do not claim validation passed" in prompt


def test_final_trust_warns_for_recovered_tool_issues():
    summary = build_final_trust_summary(
        status="completed",
        content_changed=True,
        changed_paths=["kagent/app.py"],
        validated=True,
        validation_failed=False,
        failed_tool_count=1,
        loop_warning_count=1,
    )

    assert summary["health"] == "warn"
    assert [issue["code"] for issue in summary["issues"]] == [
        "failed_tools",
        "loop_warning",
    ]


def test_final_trust_passes_clean_validated_run():
    summary = build_final_trust_summary(
        status="completed",
        content_changed=True,
        changed_paths=["kagent/app.py"],
        validated=True,
        validation_failed=False,
    )

    assert summary["health"] == "pass"
    assert summary["trustworthy"] is True
    assert summary["issues"] == []
