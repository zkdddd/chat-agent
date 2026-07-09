from kagent.agent.repair_strategy import classify_failure, repair_strategy_prompt


def test_classifies_assertion_failure():
    strategy = classify_failure("E       AssertionError: assert 1 == 2")

    assert strategy["category"] == "assertion_failure"
    assert "expected vs actual" in strategy["next_step"]


def test_classifies_import_error():
    strategy = classify_failure("ImportError: cannot import name 'Config'")

    assert strategy["category"] == "import_error"
    assert "circular" in strategy["next_step"]


def test_classifies_syntax_error():
    strategy = classify_failure("SyntaxError: invalid syntax")

    assert strategy["category"] == "syntax_error"
    assert "py_compile" in strategy["next_step"]


def test_classifies_timeout():
    strategy = classify_failure({"timed_out": True, "summary": "Timed out after 120000 ms"})

    assert strategy["category"] == "timeout"


def test_repair_strategy_prompt_includes_category_and_next_step():
    prompt = repair_strategy_prompt("ModuleNotFoundError: No module named pytest")

    assert "Failure category: missing_dependency" in prompt
    assert "Repair strategy:" in prompt
