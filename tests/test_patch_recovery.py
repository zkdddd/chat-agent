from kagent.agent.patch_recovery import patch_failure_recovery, patch_recovery_prompt


def test_patch_failure_recovery_uses_change_plan_paths():
    recovery = patch_failure_recovery(
        {"error": "patch failed"},
        change_plan={"paths": ["kagent/context.py"]},
    )

    assert recovery is not None
    assert recovery["category"] == "patch_failed"
    assert recovery["retryable"] is True
    assert recovery["read_targets"][0]["path"] == "kagent/context.py"


def test_patch_failure_recovery_extracts_paths_from_error():
    recovery = patch_failure_recovery(
        {"error": "Failed to apply patch to kagent/agent/code_agent.py"},
    )

    assert recovery is not None
    assert recovery["read_targets"][0]["path"] == "kagent/agent/code_agent.py"


def test_patch_recovery_prompt_lists_read_targets():
    prompt = patch_recovery_prompt(
        {
            "next_step": "Retry smaller.",
            "read_targets": [
                {
                    "path": "kagent/context.py",
                    "start_line": 1,
                    "end_line": 220,
                }
            ],
        }
    )

    assert "apply_patch failed" in prompt
    assert "kagent/context.py:1-220" in prompt
