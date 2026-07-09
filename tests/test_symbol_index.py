from kagent.agent.symbol_index import build_symbol_index, find_symbols


def test_build_symbol_index_extracts_python_symbols(tmp_path):
    package = tmp_path / "kagent"
    package.mkdir()
    (package / "module.py").write_text(
        "\n".join(
            [
                "import os",
                "from pathlib import Path",
                "",
                "class Runner:",
                "    def run(self):",
                "        pass",
                "",
                "async def load():",
                "    return Path('.')",
            ]
        ),
        encoding="utf-8",
    )

    symbols = build_symbol_index(tmp_path)
    by_name = {(symbol.name, symbol.kind): symbol for symbol in symbols}

    assert by_name[("Runner", "class")].line == 4
    assert by_name[("run", "method")].container == "Runner"
    assert by_name[("load", "function")].line == 8
    assert by_name[("os", "import")].module == "os"
    assert by_name[("Path", "import")].module == "pathlib"


def test_find_symbols_exact_and_fuzzy(tmp_path):
    package = tmp_path / "kagent"
    package.mkdir()
    (package / "module.py").write_text(
        "def manage_context(): pass\nclass ContextManager: pass\n",
        encoding="utf-8",
    )

    exact = find_symbols(tmp_path, "manage_context")
    fuzzy = find_symbols(tmp_path, "Context", exact=False)

    assert exact[0]["name"] == "manage_context"
    assert {item["name"] for item in fuzzy} == {"manage_context", "ContextManager"}


def test_find_symbols_filters_kind(tmp_path):
    package = tmp_path / "kagent"
    package.mkdir()
    (package / "module.py").write_text(
        "class Service: pass\ndef Service(): pass\n",
        encoding="utf-8",
    )

    matches = find_symbols(tmp_path, "Service", kind="class")

    assert len(matches) == 1
    assert matches[0]["kind"] == "class"
