from kagent.agent.change_plan import build_change_plan


def test_build_change_plan_for_patch_uses_files_touched():
    plan = build_change_plan(
        "apply_patch",
        {"files_touched": ["kagent/context.py"], "file_count": 1},
        preview="diff --git a/kagent/context.py b/kagent/context.py",
        policy={"risk_level": "low", "approval_required": False, "destructive": False},
    )

    assert plan is not None
    assert plan["operation"] == "patch"
    assert plan["paths"] == ["kagent/context.py"]
    assert plan["target_summary"] == "kagent/context.py"
    assert plan["intent"] == "Apply a targeted patch to kagent/context.py."
    assert plan["risk_level"] == "low"
    assert "can change source content" in plan["risk_summary"]
    assert "related tests" in plan["validation_hint"]
    assert plan["preview_available"] is True


def test_build_change_plan_for_delete_marks_destructive():
    plan = build_change_plan(
        "delete_path",
        {"path": "old.py"},
        preview="delete file: old.py",
        policy={"risk_level": "high", "approval_required": True, "destructive": True},
    )

    assert plan is not None
    assert plan["operation"] == "delete"
    assert plan["destructive"] is True
    assert plan["approval_required"] is True
    assert "can remove or replace current workspace state" in plan["risk_summary"]
    assert "destructive" in plan["summary"]


def test_build_change_plan_attaches_matching_symbol_impact():
    plan = build_change_plan(
        "apply_patch",
        {"files_touched": ["kagent/agent/validation.py"], "file_count": 1},
        policy={"risk_level": "low", "approval_required": False, "destructive": False},
        symbol_plans=[
            {
                "ok": True,
                "symbol": "build_validation_plan",
                "kind": "function",
                "primary_definition": {"path": "kagent/agent/validation.py", "line": 18},
                "definitions": [{"path": "kagent/agent/validation.py", "line": 18}],
                "reference_count": 12,
                "related_tests": [{"path": "tests/test_validation.py"}],
                "validation_commands": [
                    {"command": "python -m pytest -q tests/test_validation.py"}
                ],
                "risk_summary": "Changing `build_validation_plan` may affect 12 references",
            }
        ],
    )

    assert plan is not None
    assert plan["symbol_impacts"][0]["symbol"] == "build_validation_plan"
    assert plan["symbol_impacts"][0]["definition_path"] == "kagent/agent/validation.py"
    assert plan["symbol_impacts"][0]["related_tests"] == ["tests/test_validation.py"]
    assert "Symbol impact: build_validation_plan" in plan["summary"]


def test_build_change_plan_ignores_read_only_tools():
    assert build_change_plan("read_file", {"path": "kagent/context.py"}) is None
