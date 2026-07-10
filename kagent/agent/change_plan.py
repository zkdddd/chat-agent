from __future__ import annotations

from typing import Any


CHANGE_TOOLS = {
    "write_file",
    "apply_patch",
    "rename_path",
    "copy_path",
    "delete_path",
    "make_directory",
    "rollback_last_change",
    "rollback_change",
    "rollback_paths",
}


def build_change_plan(
    name: str,
    args: dict[str, Any],
    *,
    preview: str | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if name not in CHANGE_TOOLS:
        return None

    files = _planned_paths(name, args)
    operation = _operation_for_tool(name)
    risk_level = str((policy or {}).get("risk_level") or "unknown")
    destructive = bool((policy or {}).get("destructive", False))
    approval_required = bool((policy or {}).get("approval_required", False))
    preview_text = preview or ""
    plan = {
        "tool": name,
        "operation": operation,
        "paths": files,
        "path_count": len(files),
        "risk_level": risk_level,
        "destructive": destructive,
        "approval_required": approval_required,
        "summary": _summary(name, operation, files, destructive, approval_required),
        "preview_available": bool(preview_text.strip()),
        "preview_lines": len(preview_text.splitlines()) if preview_text else 0,
        "preview_truncated_for_plan": len(preview_text) > 2000,
    }
    if preview_text:
        plan["preview_excerpt"] = _clip(preview_text, 2000)
    return plan


def _planned_paths(name: str, args: dict[str, Any]) -> list[str]:
    if name == "apply_patch":
        paths = args.get("files_touched") or []
        return [str(path) for path in paths if path]
    if name in {"write_file", "delete_path", "make_directory"}:
        return [str(args["path"])] if args.get("path") else []
    if name in {"rename_path", "copy_path"}:
        return [
            str(path)
            for path in (args.get("source_path"), args.get("target_path"))
            if path
        ]
    if name in {"rollback_last_change", "rollback_change", "rollback_paths"}:
        paths = args.get("paths") or []
        return [str(path) for path in paths if path]
    return []


def _operation_for_tool(name: str) -> str:
    return {
        "write_file": "write",
        "apply_patch": "patch",
        "rename_path": "rename",
        "copy_path": "copy",
        "delete_path": "delete",
        "make_directory": "mkdir",
        "rollback_last_change": "rollback",
        "rollback_change": "rollback",
        "rollback_paths": "rollback",
    }.get(name, name)


def _summary(
    name: str,
    operation: str,
    paths: list[str],
    destructive: bool,
    approval_required: bool,
) -> str:
    target = ", ".join(paths[:4]) if paths else "workspace"
    if len(paths) > 4:
        target += f", ... ({len(paths)} paths)"
    flags = []
    if destructive:
        flags.append("destructive")
    if approval_required:
        flags.append("requires approval")
    suffix = f" [{' / '.join(flags)}]" if flags else ""
    return f"Plan to {operation} via `{name}` on {target}.{suffix}"


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 28)].rstrip() + "\n... (plan preview clipped)"
