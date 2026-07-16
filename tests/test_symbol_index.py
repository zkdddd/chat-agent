from kagent.agent.symbol_index import (
    build_symbol_index,
    find_symbol_contexts,
    find_symbol_references,
    find_symbols,
)


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


def test_find_symbol_context_returns_focused_excerpt(tmp_path):
    package = tmp_path / "kagent"
    package.mkdir()
    (package / "module.py").write_text(
        "\n".join(
            [
                "def before():",
                "    pass",
                "",
                "def manage_context(value):",
                "    total = value + 1",
                "    return total",
                "",
                "def after():",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )

    contexts = find_symbol_contexts(
        tmp_path,
        "manage_context",
        kind="function",
        context_lines=1,
    )

    assert len(contexts) == 1
    context = contexts[0]
    assert context["path"] == "kagent/module.py"
    assert context["symbol_start_line"] == 4
    assert context["symbol_end_line"] == 6
    assert context["start_line"] == 3
    assert context["end_line"] == 7
    assert "def manage_context(value):" in context["content"]
    assert "return total" in context["content"]


def test_find_symbol_references_marks_imports_calls_and_tests(tmp_path):
    package = tmp_path / "kagent"
    package.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    (package / "validation.py").write_text(
        "def build_validation_plan():\n    return []\n",
        encoding="utf-8",
    )
    (package / "code_agent.py").write_text(
        "\n".join(
            [
                "from kagent.validation import build_validation_plan",
                "",
                "def run():",
                "    return build_validation_plan()",
            ]
        ),
        encoding="utf-8",
    )
    (tests / "test_validation.py").write_text(
        "\n".join(
            [
                "from kagent.validation import build_validation_plan",
                "",
                "def test_plan():",
                "    assert build_validation_plan() == []",
            ]
        ),
        encoding="utf-8",
    )

    references = find_symbol_references(tmp_path, "build_validation_plan")
    by_path_type = {(item["path"], item["reference_type"]) for item in references}

    assert ("kagent/code_agent.py", "import") in by_path_type
    assert ("kagent/code_agent.py", "call") in by_path_type
    assert ("tests/test_validation.py", "import") in by_path_type
    assert ("tests/test_validation.py", "call") in by_path_type
    assert any(item["is_test"] for item in references if item["path"] == "tests/test_validation.py")


def test_find_symbol_references_can_exclude_tests(tmp_path):
    package = tmp_path / "kagent"
    package.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    (package / "module.py").write_text("def build_plan():\n    return build_plan\n", encoding="utf-8")
    (tests / "test_module.py").write_text("def test_build_plan():\n    build_plan()\n", encoding="utf-8")

    references = find_symbol_references(tmp_path, "build_plan", include_tests=False)

    assert references
    assert all(not item["is_test"] for item in references)
    assert all(not str(item["path"]).startswith("tests/") for item in references)


def test_build_symbol_index_extracts_javascript_and_typescript_symbols(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.ts").write_text(
        "\n".join(
            [
                "import { createRoot } from 'react-dom/client';",
                "export interface AppProps { title: string }",
                "export type Route = string;",
                "export class AppShell {}",
                "export function renderApp() {}",
                "export const loadData = async () => true;",
            ]
        ),
        encoding="utf-8",
    )

    symbols = build_symbol_index(tmp_path)
    by_name = {(symbol.name, symbol.kind): symbol for symbol in symbols}

    assert by_name[("client", "import")].module == "react-dom/client"
    assert by_name[("AppProps", "interface")].line == 2
    assert by_name[("Route", "type")].line == 3
    assert by_name[("AppShell", "class")].line == 4
    assert by_name[("renderApp", "function")].line == 5
    assert by_name[("loadData", "function")].line == 6


def test_build_symbol_index_extracts_go_rust_and_java_symbols(tmp_path):
    go_dir = tmp_path / "goapp"
    rust_dir = tmp_path / "rustapp" / "src"
    java_dir = tmp_path / "javaapp"
    go_dir.mkdir()
    rust_dir.mkdir(parents=True)
    java_dir.mkdir()
    (go_dir / "service.go").write_text(
        "\n".join(
            [
                'import "fmt"',
                "type Server struct {}",
                "func NewServer() *Server { return nil }",
                "func (s *Server) Start() {}",
            ]
        ),
        encoding="utf-8",
    )
    (rust_dir / "lib.rs").write_text(
        "\n".join(
            [
                "use crate::config::Config;",
                "pub struct Runner;",
                "pub enum Mode { Fast }",
                "pub fn run() {}",
            ]
        ),
        encoding="utf-8",
    )
    (java_dir / "Service.java").write_text(
        "\n".join(
            [
                "import java.util.List;",
                "public class Service {",
                "  public void start() {}",
                "}",
            ]
        ),
        encoding="utf-8",
    )

    symbols = build_symbol_index(tmp_path)
    by_name = {(symbol.name, symbol.kind): symbol for symbol in symbols}

    assert by_name[("fmt", "import")].module == "fmt"
    assert by_name[("Server", "struct")].line == 2
    assert by_name[("NewServer", "function")].line == 3
    assert by_name[("Start", "method")].line == 4
    assert by_name[("Config", "import")].module == "crate::config::Config"
    assert by_name[("Runner", "struct")].line == 2
    assert by_name[("Mode", "enum")].line == 3
    assert by_name[("run", "function")].line == 4
    assert by_name[("List", "import")].module == "java.util.List"
    assert by_name[("Service", "class")].line == 2
    assert by_name[("start", "method")].line == 3
