from __future__ import annotations

import json
from pathlib import Path

from kagent.agent import coverage as cov_module
from kagent.agent.coverage import (
    coverage_regression_gate,
    coverage_trend,
    save_coverage_snapshot,
)


def _set_history(monkeypatch, root, snapshots):
    monkeypatch.setattr(cov_module, "STATE_DIR", str(Path(root) / "state"))
    path = Path(root) / "state" / "coverage_history.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshots), encoding="utf-8")


def test_save_and_trend_track_coverage_over_time(tmp_path, monkeypatch):
    monkeypatch.setattr(cov_module, "STATE_DIR", str(tmp_path / "state"))

    save_coverage_snapshot(tmp_path, {"line_rate": 0.50})
    save_coverage_snapshot(tmp_path, {"line_rate": 0.60})
    save_coverage_snapshot(tmp_path, {"line_rate": 0.70})

    trend = coverage_trend(tmp_path)
    assert trend["samples"] == 3
    assert trend["recent_line_rate"] == 0.70
    # baseline is the mean of [0.5, 0.6, 0.7] = 0.6; recent above baseline.
    assert trend["delta"] > 0


def test_regression_gate_warns_on_coverage_drop(tmp_path, monkeypatch):
    _set_history(monkeypatch, tmp_path, [
        {"line_rate": 0.80},
        {"line_rate": 0.80},
        {"line_rate": 0.80},
        {"line_rate": 0.70},  # recent dropped 10% from 0.8 baseline
    ])

    trend = coverage_trend(tmp_path)
    gate = coverage_regression_gate(trend)

    assert gate["status"] == "warn"
    assert "dropped" in gate["message"]
    assert gate["delta"] < 0


def test_regression_gate_passes_when_stable_or_improving(tmp_path, monkeypatch):
    _set_history(monkeypatch, tmp_path, [
        {"line_rate": 0.60},
        {"line_rate": 0.65},
        {"line_rate": 0.70},
    ])

    gate = coverage_regression_gate(coverage_trend(tmp_path))
    assert gate["status"] == "pass"


def test_regression_gate_handles_insufficient_history(tmp_path, monkeypatch):
    monkeypatch.setattr(cov_module, "STATE_DIR", str(tmp_path / "state"))

    gate = coverage_regression_gate(coverage_trend(tmp_path))
    assert gate["status"] == "pass"
    assert "insufficient" in gate["message"]


def test_measure_coverage_parses_real_coverage_json(tmp_path, monkeypatch):
    # Build a fake project with one source + one test so coverage has something to measure.
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pkg" / "mod.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "test_mod.py").write_text(
        "from pkg.mod import add\n\ndef test_add():\n    assert add(1, 2) == 3\n", encoding="utf-8"
    )

    # Run the real coverage measurement on this tiny project.
    result = cov_module.measure_coverage(tmp_path, timeout=120)

    assert result is not None
    assert 0.0 <= result["line_rate"] <= 1.0
    assert result["covered_lines"] >= 1
    assert result["num_statements"] >= 1
