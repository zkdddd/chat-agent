from kagent.agent.symbol_change_plan import build_symbol_change_plan


def test_symbol_change_plan_links_definition_references_tests_and_validation(tmp_path):
    package = tmp_path / "kagent"
    package.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    (package / "validation.py").write_text(
        "def build_validation_plan():\n    return []\n",
        encoding="utf-8",
    )
    (package / "code_agent.py").write_text(
        "from kagent.validation import build_validation_plan\n\n"
        "def run():\n"
        "    return build_validation_plan()\n",
        encoding="utf-8",
    )
    (tests / "test_validation.py").write_text(
        "from kagent.validation import build_validation_plan\n\n"
        "def test_plan():\n"
        "    assert build_validation_plan() == []\n",
        encoding="utf-8",
    )

    plan = build_symbol_change_plan(
        tmp_path,
        "build_validation_plan",
        kind="function",
    )

    assert plan["ok"] is True
    assert plan["primary_definition"]["path"] == "kagent/validation.py"
    assert plan["definition_count"] == 1
    assert plan["reference_count"] >= 4
    assert plan["related_tests"][0]["path"] == "tests/test_validation.py"
    assert "tests/test_validation.py" in plan["validation_commands"][0]["command"]
    assert "related test file" in plan["risk_summary"]
    assert "Plan symbol change" in plan["summary"]


def test_symbol_change_plan_handles_missing_symbol(tmp_path):
    plan = build_symbol_change_plan(tmp_path, "missing_symbol")

    assert plan["ok"] is True
    assert plan["definition_count"] == 0
    assert plan["primary_definition"] is None
    assert "No definition found" in plan["summary"]
