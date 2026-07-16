from kagent.ui_preferences import load_ui_preferences, save_ui_preferences


def test_ui_preferences_round_trip(tmp_path):
    path = tmp_path / "ui_preferences.json"

    saved = save_ui_preferences(
        {"model": "gpt-5.5", "reasoning_effort": "high"},
        path=path,
    )
    loaded = load_ui_preferences(path)

    assert saved == {"model": "gpt-5.5", "reasoning_effort": "high"}
    assert loaded == saved


def test_ui_preferences_fallback_for_invalid_file(tmp_path):
    path = tmp_path / "ui_preferences.json"
    path.write_text("not-json", encoding="utf-8")

    loaded = load_ui_preferences(path)

    assert loaded["model"]
    assert loaded["reasoning_effort"] == "medium"


def test_ui_preferences_reject_unknown_model_and_reasoning(tmp_path):
    path = tmp_path / "ui_preferences.json"

    saved = save_ui_preferences(
        {"model": "unknown-model", "reasoning_effort": "turbo"},
        path=path,
    )

    assert saved["model"] != "unknown-model"
    assert saved["reasoning_effort"] == "medium"
