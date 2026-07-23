from __future__ import annotations

from pathlib import Path

from kagent.agent.test_gen import find_untested_symbols, generate_test_scaffold


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_project(tmp_path: Path) -> Path:
    # Untested source file: a module with a function and a class, no test file.
    _write(
        tmp_path / "pkg" / "untested.py",
        "def add(a, b):\n    return a + b\n\n\nclass Calculator:\n    def mul(self, a, b):\n        return a * b\n",
    )
    # Tested source file: has a matching tests/test_untested2.py.
    _write(
        tmp_path / "pkg" / "tested.py",
        "def sub(a, b):\n    return a - b\n",
    )
    _write(
        tmp_path / "tests" / "test_tested.py",
        "from pkg.tested import sub\n\ndef test_sub():\n    assert sub(2, 1) == 1\n",
    )
    _write(
        (tmp_path / "pkg" / "__init__.py"),
        "",
    )
    _write(
        (tmp_path / "tests" / "__init__.py"),
        "",
    )
    return tmp_path


def test_find_untested_symbols_returns_only_untested(tmp_path):
    root = _make_project(tmp_path)

    untested = find_untested_symbols(root, limit=50)

    names = {item["symbol"] for item in untested}
    # untested.py symbols have no mapped test file -> included.
    assert "add" in names
    assert "Calculator" in names
    # tested.py has tests/test_tested.py -> its symbol is NOT untested.
    assert "sub" not in names
    # Each untested symbol points at the same suggested test path.
    paths = {item["path"] for item in untested}
    assert paths == {"pkg/untested.py"}
    for item in untested:
        assert item["suggested_test_path"].startswith("tests/")


def test_generate_test_scaffold_produces_import_and_placeholder_tests(tmp_path):
    root = _make_project(tmp_path)
    untested = find_untested_symbols(root, limit=50)
    target = next(item for item in untested if item["symbol"] == "add")

    result = generate_test_scaffold(root, target)

    assert result["ok"] is True
    assert result["test_path"].startswith("tests/")
    assert "add" in result["targets"]
    content = result["content"]
    # Imports the module under test.
    assert "from pkg.untested import" in content
    # Has a placeholder test function and a TODO assertion marker.
    assert "def test_add" in content
    assert "TODO" in content
    assert "assert" in content


def test_generated_scaffold_is_collectable_by_pytest(tmp_path, monkeypatch):
    root = _make_project(tmp_path)
    untested = find_untested_symbols(root, limit=50)
    target = next(item for item in untested if item["symbol"] == "add")
    result = generate_test_scaffold(root, target)

    # Write the scaffold to its suggested path and confirm pytest can collect it.
    test_file = root / result["test_path"]
    _write(test_file, result["content"])

    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", str(test_file)],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    # Collection should succeed and find the generated test.
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "test_add" in proc.stdout


def test_find_untested_symbols_skips_dunder_and_private(tmp_path):
    _write(
        tmp_path / "pkg2" / "internal.py",
        "def _private():\n    pass\n\n\ndef __dunder__():\n    pass\n\n\ndef public():\n    pass\n",
    )
    _write((tmp_path / "pkg2" / "__init__.py"), "")

    untested = find_untested_symbols(tmp_path, limit=50)
    names = {item["symbol"] for item in untested if item["path"] == "pkg2/internal.py"}
    assert "public" in names
    assert "_private" not in names
    assert "__dunder__" not in names


def test_generate_test_scaffold_handles_missing_source(tmp_path):
    result = generate_test_scaffold(tmp_path, {"path": "nope/missing.py", "symbol": "x"})
    assert result["ok"] is False
    assert "not found" in result["error"]
