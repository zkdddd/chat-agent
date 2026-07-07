from __future__ import annotations

import fnmatch
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from ..config import BASE_DIR


DEFAULT_IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
}


class WorkspaceError(ValueError):
    pass


class WorkspaceTools:
    def __init__(self, root: Path | str = BASE_DIR):
        self.root = Path(root).resolve()

    def _resolve_path(self, raw_path: str) -> Path:
        if not raw_path:
            raise WorkspaceError("path is required")
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = (self.root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if candidate == self.root:
            return candidate
        if self.root not in candidate.parents:
            raise WorkspaceError(f"Path outside workspace: {raw_path}")
        return candidate

    def _rel(self, path: Path) -> str:
        try:
            rel = path.relative_to(self.root)
            return "." if not rel.parts else rel.as_posix()
        except Exception:
            return path.as_posix() if isinstance(path, Path) else str(path)

    @staticmethod
    def _clip(text: str, limit: int = 20000) -> tuple[str, bool]:
        if limit is None or limit <= 0:
            return text, False
        if len(text) <= limit:
            return text, False
        return text[:limit], True

    @staticmethod
    def _is_hidden(name: str) -> bool:
        return name.startswith(".")

    @staticmethod
    def _is_text_file(path: Path) -> bool:
        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".pdf", ".zip", ".7z", ".tar", ".gz", ".bz2", ".xz", ".pyc", ".pyd", ".dll", ".exe", ".so", ".dylib"}:
            return False
        return True

    def _iter_directory(
        self,
        root: Path,
        max_depth: int | None,
        ignore_hidden: bool,
    ):
        start_depth = len(root.parts)
        for current_root, dirs, files in os.walk(root):
            current = Path(current_root)
            depth = len(current.parts) - start_depth
            if max_depth is not None and depth > max_depth:
                dirs[:] = []
                continue

            dirs.sort()
            files.sort()

            if ignore_hidden:
                dirs[:] = [
                    d
                    for d in dirs
                    if not self._is_hidden(d) and d not in DEFAULT_IGNORED_DIRS
                ]
                files = [f for f in files if not self._is_hidden(f)]

            yield current, depth, dirs, files

    def _patch_paths(self, patch_text: str) -> list[str]:
        paths: list[str] = []
        seen: set[str] = set()
        for line in patch_text.splitlines():
            if line.startswith("diff --git "):
                parts = line.split()
                if len(parts) >= 4:
                    candidate = parts[3]
                    if candidate.startswith("b/"):
                        rel = candidate[2:]
                        if rel not in seen:
                            seen.add(rel)
                            paths.append(rel)
            elif line.startswith("+++ b/"):
                rel = line[6:].strip()
                if rel != "/dev/null" and rel not in seen:
                    seen.add(rel)
                    paths.append(rel)
        return paths

    def read_file(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        max_chars: int = 20000,
    ) -> dict[str, Any]:
        file_path = self._resolve_path(path)
        if not file_path.exists():
            raise WorkspaceError(f"File not found: {self._rel(file_path)}")
        if file_path.is_dir():
            raise WorkspaceError(f"Expected a file but found a directory: {self._rel(file_path)}")

        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError(f"File is not valid UTF-8 text: {self._rel(file_path)}") from exc

        lines = text.splitlines()
        total_lines = len(lines)

        if start_line is not None or end_line is not None:
            start = 1 if start_line is None else max(start_line, 1)
            stop = total_lines if end_line is None else max(end_line, 0)
            if stop and stop < start:
                raise WorkspaceError("end_line must be greater than or equal to start_line")
            selected = "\n".join(lines[start - 1:stop])
            excerpt_start = start
            excerpt_end = min(stop, total_lines)
        else:
            selected = text
            excerpt_start = 1
            excerpt_end = total_lines

        selected, truncated = self._clip(selected, max_chars)
        return {
            "path": self._rel(file_path),
            "abs_path": str(file_path),
            "start_line": excerpt_start,
            "end_line": excerpt_end,
            "line_count": total_lines,
            "content": selected,
            "truncated": truncated,
        }

    def list_files(
        self,
        path: str = ".",
        max_depth: int | None = 3,
        include_dirs: bool = True,
        include_hidden: bool = False,
        max_results: int = 500,
    ) -> dict[str, Any]:
        start = self._resolve_path(path)
        if not start.exists():
            raise WorkspaceError(f"Path not found: {self._rel(start)}")
        if start.is_file():
            start = start.parent
        if not start.is_dir():
            raise WorkspaceError(f"Expected a directory but found a file: {self._rel(start)}")

        if max_depth is not None:
            max_depth = max(0, int(max_depth))
        max_results = max(1, int(max_results))

        items: list[dict[str, Any]] = []
        truncated = False
        ignored_count = 0

        for current, depth, dirs, files in self._iter_directory(start, max_depth, not include_hidden):
            if include_dirs:
                for name in dirs:
                    if not include_hidden and name in DEFAULT_IGNORED_DIRS:
                        ignored_count += 1
                        continue
                    child = current / name
                    rel = self._rel(child)
                    if len(items) >= max_results:
                        truncated = True
                        break
                    items.append(
                        {
                            "type": "dir",
                            "name": name,
                            "path": rel,
                            "depth": depth + 1,
                        }
                    )
                if truncated:
                    break

            for name in files:
                child = current / name
                rel = self._rel(child)
                if len(items) >= max_results:
                    truncated = True
                    break
                stat = child.stat()
                items.append(
                    {
                        "type": "file",
                        "name": name,
                        "path": rel,
                        "depth": depth + 1,
                        "size": stat.st_size,
                    }
                )
            if truncated:
                break

        return {
            "root": str(start),
            "path": self._rel(start),
            "items": items,
            "count": len(items),
            "truncated": truncated,
            "ignored_count": ignored_count,
            "max_depth": max_depth,
        }

    def search_file(
        self,
        query: str,
        path: str = ".",
        file_glob: str = "*",
        case_sensitive: bool = False,
        include_hidden: bool = False,
        context_lines: int = 1,
        max_results: int = 50,
    ) -> dict[str, Any]:
        if not query or not query.strip():
            raise WorkspaceError("query is required")

        start = self._resolve_path(path)
        if not start.exists():
            raise WorkspaceError(f"Path not found: {self._rel(start)}")

        if start.is_file():
            candidates = [start]
            base_dir = start.parent
        else:
            base_dir = start
            candidates = []
            for current, _, dirs, files in self._iter_directory(start, None, not include_hidden):
                for name in files:
                    child = current / name
                    rel = child.relative_to(base_dir).as_posix()
                    if fnmatch.fnmatch(name, file_glob) or fnmatch.fnmatch(rel, file_glob):
                        candidates.append(child)

        max_results = max(1, int(max_results))
        context_lines = max(0, int(context_lines))
        needle = query if case_sensitive else query.lower()

        matches: list[dict[str, Any]] = []
        scanned = 0
        skipped_binary = 0
        truncated = False

        for file_path in candidates:
            if len(matches) >= max_results:
                truncated = True
                break
            if file_path.is_dir():
                continue
            scanned += 1
            if file_path.stat().st_size > 1_500_000:
                continue
            if not self._is_text_file(file_path):
                skipped_binary += 1
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                skipped_binary += 1
                continue

            lines = text.splitlines()
            for line_no, line in enumerate(lines, start=1):
                haystack = line if case_sensitive else line.lower()
                if needle not in haystack:
                    continue

                start_line = max(1, line_no - context_lines)
                end_line = min(len(lines), line_no + context_lines)
                snippet = "\n".join(lines[start_line - 1 : end_line])
                matches.append(
                    {
                        "path": self._rel(file_path),
                        "line_number": line_no,
                        "line": line,
                        "snippet": snippet,
                        "start_line": start_line,
                        "end_line": end_line,
                    }
                )
                if len(matches) >= max_results:
                    truncated = True
                    break
            if truncated:
                break

        return {
            "query": query,
            "path": self._rel(start),
            "file_glob": file_glob,
            "matches": matches,
            "count": len(matches),
            "scanned_files": scanned,
            "skipped_binary": skipped_binary,
            "truncated": truncated,
            "case_sensitive": case_sensitive,
            "context_lines": context_lines,
        }

    def apply_patch(self, patch: str) -> dict[str, Any]:
        if not patch or not patch.strip():
            raise WorkspaceError("patch is required")

        proc = subprocess.run(
            ["git", "apply", "--recount", "--whitespace=nowarn"],
            cwd=str(self.root),
            input=patch.encode("utf-8"),
            capture_output=True,
        )
        if proc.returncode != 0:
            stderr = (proc.stderr or b"").decode("utf-8", "replace").strip()
            stdout = (proc.stdout or b"").decode("utf-8", "replace").strip()
            message = stderr or stdout or "git apply failed"
            raise WorkspaceError(message)

        files_touched = self._patch_paths(patch)
        return {
            "ok": True,
            "files_touched": files_touched,
            "file_count": len(files_touched),
            "patch_bytes": len(patch.encode("utf-8")),
        }

    def preview_patch(self, patch: str) -> dict[str, Any]:
        if not patch or not patch.strip():
            raise WorkspaceError("patch is required")

        files_touched = self._patch_paths(patch)
        return {
            "files_touched": files_touched,
            "file_count": len(files_touched),
            "patch_bytes": len(patch.encode("utf-8")),
            "patch_lines": patch.count("\n") + 1,
        }

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        file_path = self._resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return {
            "path": self._rel(file_path),
            "abs_path": str(file_path),
            "bytes_written": len(content.encode("utf-8")),
            "line_count": len(content.splitlines()),
        }

    def run_command(
        self,
        command: str,
        cwd: str | None = None,
        timeout_ms: int = 120000,
    ) -> dict[str, Any]:
        if not command or not command.strip():
            raise WorkspaceError("command is required")

        workdir = self.root if not cwd else self._resolve_path(cwd)
        if not workdir.exists():
            raise WorkspaceError(f"Working directory not found: {self._rel(workdir)}")
        if not workdir.is_dir():
            raise WorkspaceError(f"Working directory must be a directory: {self._rel(workdir)}")

        started = time.monotonic()
        timeout_sec = max(timeout_ms, 1) / 1000.0
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_sec,
            )
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            stdout, stdout_truncated = self._clip(stdout)
            stderr, stderr_truncated = self._clip(stderr)
            return {
                "command": command,
                "cwd": self._rel(workdir),
                "returncode": None,
                "timed_out": True,
                "duration_ms": duration_ms,
                "stdout": stdout,
                "stdout_truncated": stdout_truncated,
                "stderr": stderr,
                "stderr_truncated": stderr_truncated,
            }

        duration_ms = int((time.monotonic() - started) * 1000)
        stdout, stdout_truncated = self._clip(proc.stdout or "")
        stderr, stderr_truncated = self._clip(proc.stderr or "")
        return {
            "command": command,
            "cwd": self._rel(workdir),
            "returncode": proc.returncode,
            "timed_out": timed_out,
            "duration_ms": duration_ms,
            "stdout": stdout,
            "stdout_truncated": stdout_truncated,
            "stderr": stderr,
            "stderr_truncated": stderr_truncated,
        }
