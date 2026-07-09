from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .project_map import build_project_map


SymbolKind = Literal["class", "function", "method", "import"]


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: SymbolKind
    path: str
    line: int
    end_line: int | None = None
    container: str | None = None
    module: str | None = None


def build_symbol_index(root: Path) -> list[Symbol]:
    project_map = build_project_map(root)
    symbols: list[Symbol] = []
    for rel_path in project_map.source_files:
        if Path(rel_path).suffix.lower() != ".py":
            continue
        path = root / rel_path
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        symbols.extend(_symbols_from_tree(tree, rel_path))
    return sorted(symbols, key=lambda item: (item.path, item.line, item.name))


def find_symbols(
    root: Path,
    query: str,
    *,
    kind: SymbolKind | None = None,
    exact: bool = True,
    limit: int = 50,
) -> list[dict[str, object]]:
    needle = str(query or "").strip()
    if not needle:
        return []
    matches: list[Symbol] = []
    for symbol in build_symbol_index(root):
        if kind and symbol.kind != kind:
            continue
        if exact and symbol.name != needle:
            continue
        if not exact and needle.lower() not in symbol.name.lower():
            continue
        matches.append(symbol)
        if len(matches) >= limit:
            break
    return [symbol_to_dict(symbol) for symbol in matches]


def symbol_to_dict(symbol: Symbol) -> dict[str, object]:
    return {
        "name": symbol.name,
        "kind": symbol.kind,
        "path": symbol.path,
        "line": symbol.line,
        "end_line": symbol.end_line,
        "container": symbol.container,
        "module": symbol.module,
    }


def _symbols_from_tree(tree: ast.AST, rel_path: str) -> list[Symbol]:
    visitor = _SymbolVisitor(rel_path)
    visitor.visit(tree)
    return visitor.symbols


class _SymbolVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.symbols: list[Symbol] = []
        self.containers: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbols.append(
            Symbol(
                name=node.name,
                kind="class",
                path=self.rel_path,
                line=node.lineno,
                end_line=getattr(node, "end_lineno", None),
                container=self._container(),
            )
        )
        self.containers.append(node.name)
        self.generic_visit(node)
        self.containers.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.symbols.append(
                Symbol(
                    name=alias.asname or alias.name.split(".", 1)[0],
                    kind="import",
                    path=self.rel_path,
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", None),
                    module=alias.name,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = "." * int(node.level or 0) + (node.module or "")
        for alias in node.names:
            self.symbols.append(
                Symbol(
                    name=alias.asname or alias.name,
                    kind="import",
                    path=self.rel_path,
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", None),
                    module=module,
                )
            )

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        kind: SymbolKind = "method" if self.containers else "function"
        self.symbols.append(
            Symbol(
                name=node.name,
                kind=kind,
                path=self.rel_path,
                line=node.lineno,
                end_line=getattr(node, "end_lineno", None),
                container=self._container(),
            )
        )
        self.containers.append(node.name)
        self.generic_visit(node)
        self.containers.pop()

    def _container(self) -> str | None:
        return ".".join(self.containers) if self.containers else None
