from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import (
    MODEL,
    REASONING_EFFORT,
    STATE_DIR,
    available_models,
    normalize_reasoning_effort,
)

PREFERENCES_PATH = Path(STATE_DIR) / "ui_preferences.json"


def load_ui_preferences(path: Path | None = None) -> dict[str, str]:
    target = path or PREFERENCES_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}

    model = str(raw.get("model") or MODEL).strip() or MODEL
    if model not in available_models():
        model = MODEL

    return {
        "model": model,
        "reasoning_effort": normalize_reasoning_effort(raw.get("reasoning_effort") or REASONING_EFFORT),
    }


def save_ui_preferences(preferences: dict[str, Any], path: Path | None = None) -> dict[str, str]:
    current = load_ui_preferences(path)
    current.update(
        {
            key: str(value).strip()
            for key, value in preferences.items()
            if key in {"model", "reasoning_effort"} and value is not None
        }
    )

    model = current.get("model") or MODEL
    if model not in available_models():
        model = MODEL
    current["model"] = model
    current["reasoning_effort"] = normalize_reasoning_effort(current.get("reasoning_effort"))

    target = path or PREFERENCES_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)
    return current
