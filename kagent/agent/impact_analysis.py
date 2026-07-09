from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from .project_map import build_project_map, related_tests_for_source

MAX_RELATED_TEST_COMMANDS = 3


def related_test_commands_for_changes(
    changed_paths: set[str],
    *,
    workspace_root: Path,
    cwd: str = ".",
    max_commands: int = MAX_RELATED_TEST_COMMANDS,
) -> list[dict[str, Any]]:
    tests = related_tests_for_changes(changed_paths, workspace_root=workspace_root)
    commands: list[dict[str, Any]] = []
    for test_path in tests[:max_commands]:
        commands.append(
            {
                "label": "Related tests",
                "reason": "Run tests inferred from the changed file path before the full suite.",
                "command": subprocess.list2cmdline([sys.executable, "-m", "pytest", "-q", test_path]),
                "cwd": cwd,
                "timeout_ms": 180000,
                "related_test": test_path,
            }
        )
    return commands


def related_tests_for_changes(changed_paths: set[str], *, workspace_root: Path) -> list[str]:
    project_map = build_project_map(workspace_root)
    test_set = set(project_map.test_files)
    related_by_source = project_map.source_to_tests
    candidates: list[str] = []
    seen: set[str] = set()
    for raw_path in sorted(path for path in changed_paths if path):
        normalized = Path(str(raw_path).replace("\\", "/")).as_posix()
        direct_tests = [normalized] if normalized in test_set else []
        mapped_tests = related_by_source.get(normalized)
        if mapped_tests is None:
            mapped_tests = related_tests_for_source(normalized, list(test_set))
        for candidate in [*direct_tests, *mapped_tests]:
            if candidate not in test_set:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)
    return candidates
