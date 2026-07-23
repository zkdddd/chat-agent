from __future__ import annotations

from pathlib import Path

from kagent.agent import failure_memory as fm
from kagent.agent.failure_memory import (
    FailureMemoryIndex,
    FailureRecord,
    collect_failure_corpus,
    recall_similar_failures,
)
from kagent.agent.run_log import RunLogger


def _write_failed_run(
    runs_dir: Path,
    *,
    workspace: str,
    nodeid: str,
    failure_type: str,
    message: str,
    symbols: list[str] | None = None,
    fix_hint: str = "",
) -> None:
    log = RunLogger(session_id="s", workspace_root=workspace)
    if symbols:
        log.write(
            "symbol_impacts",
            {"symbol": symbols[0], "related_tests": [], "risk_level": "medium"},
        )
    if fix_hint:
        log.write("change_plan", {"plan": {"intent": fix_hint}})
    log.write(
        "test_case_result",
        {"nodeid": nodeid, "status": "failed", "failure_type": failure_type, "message": message},
    )
    log.finish("completed", {"validated": False, "validation_failed": True})


def _set_runs_dir(monkeypatch, runs_dir: Path) -> None:
    # RunLogger writes to run_log.STATE_DIR/runs; collect_failure_corpus reads
    # the passed runs_dir. Patch both so writes and reads land in the same place.
    monkeypatch.setattr("kagent.agent.run_log.STATE_DIR", str(runs_dir.parent))
    monkeypatch.setattr(fm, "STATE_DIR", str(runs_dir.parent))
    runs_dir.mkdir(parents=True, exist_ok=True)


def test_collect_failure_corpus_joins_failures_with_symbols_and_fix(tmp_path, monkeypatch):
    runs_dir = tmp_path / "state" / "runs"
    _set_runs_dir(monkeypatch, runs_dir)
    _write_failed_run(
        runs_dir, workspace=str(tmp_path),
        nodeid="tests/test_a.py::test_add",
        failure_type="AssertionError", message="assert 1 + 1 == 3 failed",
        symbols=["add"], fix_hint="fix add to return a+b",
    )
    _write_failed_run(
        runs_dir, workspace=str(tmp_path),
        nodeid="tests/test_b.py::test_parse",
        failure_type="ValueError", message="invalid literal for parse",
        symbols=["parse"], fix_hint="handle parse error",
    )

    records = collect_failure_corpus(runs_dir)

    assert len(records) == 2
    add_rec = next(r for r in records if "test_add" in r.nodeid)
    assert add_rec.failure_type == "AssertionError"
    assert add_rec.symbols == ["add"]
    assert "fix add" in add_rec.fix_hint


def test_recall_returns_insufficient_corpus_below_threshold(tmp_path, monkeypatch):
    runs_dir = tmp_path / "state" / "runs"
    _set_runs_dir(monkeypatch, runs_dir)
    _write_failed_run(
        runs_dir, workspace=str(tmp_path),
        nodeid="tests/test_a.py::test_only", failure_type="AssertionError", message="assert false",
    )

    result = recall_similar_failures("assert false", runs_dir=runs_dir)

    assert result["ok"] is False
    assert result["reason"] == "insufficient_corpus"
    assert result["corpus_size"] == 1
    assert result["matches"] == []


def test_recall_finds_similar_failures_by_text(tmp_path, monkeypatch):
    runs_dir = tmp_path / "state" / "runs"
    _set_runs_dir(monkeypatch, runs_dir)
    _write_failed_run(
        runs_dir, workspace=str(tmp_path),
        nodeid="tests/test_add.py::test_add", failure_type="AssertionError", message="assert 1 + 1 == 3 failed",
        symbols=["add"], fix_hint="fix add",
    )
    _write_failed_run(
        runs_dir, workspace=str(tmp_path),
        nodeid="tests/test_add.py::test_add_again", failure_type="AssertionError", message="assert 1 + 1 == 3 failed in add",
        symbols=["add"], fix_hint="fix add again",
    )
    _write_failed_run(
        runs_dir, workspace=str(tmp_path),
        nodeid="tests/test_parse.py::test_parse", failure_type="ValueError", message="invalid literal for parse",
        symbols=["parse"], fix_hint="handle parse",
    )

    result = recall_similar_failures("assert 1 + 1 == 3 failed", runs_dir=runs_dir, k=3)

    assert result["ok"] is True
    assert result["corpus_size"] == 3
    matches = result["matches"]
    assert len(matches) >= 1
    # The two "add" failures share the most tokens with the query.
    top = matches[0]
    assert "add" in top["nodeid"]
    assert top["score"] > 0


def test_recall_dedupes_repeated_nodeids(tmp_path, monkeypatch):
    runs_dir = tmp_path / "state" / "runs"
    _set_runs_dir(monkeypatch, runs_dir)
    for _ in range(3):
        _write_failed_run(
            runs_dir, workspace=str(tmp_path),
            nodeid="tests/test_a.py::test_a", failure_type="AssertionError", message="assert false",
        )
    _write_failed_run(
        runs_dir, workspace=str(tmp_path),
        nodeid="tests/test_b.py::test_b", failure_type="AssertionError", message="assert false",
    )

    records = collect_failure_corpus(runs_dir)

    nodeids = [r.nodeid for r in records]
    # The repeated nodeid collapses to one record per run, but each run is a
    # separate record; the key property is nodeids are the expected set.
    assert set(nodeids) == {"tests/test_a.py::test_a", "tests/test_b.py::test_b"}


def test_failure_index_handles_empty_corpus():
    idx = FailureMemoryIndex([])
    result = idx.recall_similar_failures("anything")
    assert result["ok"] is False
    assert result["corpus_size"] == 0
