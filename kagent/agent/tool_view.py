from __future__ import annotations

import json
from typing import Any


def tool_display_args(workspace: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "write_file":
        preview = workspace.preview_write_file(
            path=str(args["path"]),
            content=str(args["content"]),
        )
        return {
            "path": preview["path"],
            "exists": preview["exists"],
            "bytes_written": preview["bytes_written"],
            "line_count": preview["line_count"],
            "preview_truncated": preview["preview_truncated"],
        }

    if name == "run_command":
        preview = workspace.preview_command(
            command=str(args["command"]),
            cwd=args.get("cwd"),
            timeout_ms=int(args.get("timeout_ms", 120000)),
        )
        return {
            "command": preview["command"],
            "cwd": preview["cwd"],
            "timeout_ms": preview["timeout_ms"],
        }

    if name == "rename_path":
        preview = workspace.preview_rename_path(
            source_path=str(args["source_path"]),
            target_path=str(args["target_path"]),
        )
        return {
            "source_path": preview["source_path"],
            "target_path": preview["target_path"],
            "item_type": preview["item_type"],
        }

    if name == "copy_path":
        preview = workspace.preview_copy_path(
            source_path=str(args["source_path"]),
            target_path=str(args["target_path"]),
        )
        return {
            "source_path": preview["source_path"],
            "target_path": preview["target_path"],
            "item_type": preview["item_type"],
            "item_count": preview["item_count"],
            "item_count_truncated": preview["item_count_truncated"],
        }

    if name == "delete_path":
        preview = workspace.preview_delete_path(
            path=str(args["path"]),
            recursive=bool(args.get("recursive", True)),
        )
        return {
            "path": preview["path"],
            "item_type": preview["item_type"],
            "recursive": preview["recursive"],
            "item_count": preview["item_count"],
            "item_count_truncated": preview["item_count_truncated"],
        }

    if name == "make_directory":
        preview = workspace.preview_make_directory(
            path=str(args["path"]),
        )
        return {
            "path": preview["path"],
            "exists": preview["exists"],
        }

    if name == "list_rollback_history":
        limit = int(args.get("limit", 12))
        include_inactive = bool(args.get("include_inactive", True))
        return {
            "limit": limit,
            "include_inactive": include_inactive,
        }

    if name == "preview_rollback_change":
        preview = workspace.preview_rollback_change(
            rollback_id=int(args["rollback_id"]),
        )
        return {
            "rollback_id": preview["rollback_id"],
            "source_tool": preview["source_tool"],
            "created_at": preview["created_at"],
            "status": preview["status"],
            "available": preview["available"],
            "path_count": preview["path_count"],
            "paths": preview["paths"][:12],
            "paths_truncated": len(preview["paths"]) > 12,
            "preview_truncated": preview["preview_truncated"],
            "superseded_active_count": preview["superseded_active_count"],
        }

    if name == "rollback_last_change":
        preview = workspace.preview_rollback_last_change()
        return {
            "rollback_id": preview["rollback_id"],
            "source_tool": preview["source_tool"],
            "created_at": preview["created_at"],
            "status": preview["status"],
            "available": preview["available"],
            "path_count": preview["path_count"],
            "paths": preview["paths"][:12],
            "paths_truncated": len(preview["paths"]) > 12,
        }

    if name == "rollback_change":
        preview = workspace.preview_rollback_change(
            rollback_id=int(args["rollback_id"]),
        )
        return {
            "rollback_id": preview["rollback_id"],
            "source_tool": preview["source_tool"],
            "created_at": preview["created_at"],
            "status": preview["status"],
            "available": preview["available"],
            "path_count": preview["path_count"],
            "paths": preview["paths"][:12],
            "paths_truncated": len(preview["paths"]) > 12,
            "superseded_active_count": preview["superseded_active_count"],
        }

    if name != "apply_patch":
        return args

    patch = str(args.get("patch") or "")
    if not patch.strip():
        return {
            "patch_bytes": 0,
            "patch_lines": 0,
            "file_count": 0,
            "files_touched": [],
        }
    return workspace.preview_patch(patch)


def tool_preview_text(workspace: Any, name: str, args: dict[str, Any]) -> str | None:
    if name == "apply_patch":
        patch = str(args.get("patch") or "")
        return patch or None
    if name == "write_file":
        preview = workspace.preview_write_file(
            path=str(args["path"]),
            content=str(args["content"]),
        )
        return str(preview["preview"])
    if name == "run_command":
        preview = workspace.preview_command(
            command=str(args["command"]),
            cwd=args.get("cwd"),
            timeout_ms=int(args.get("timeout_ms", 120000)),
        )
        return str(preview["preview"])
    if name == "rename_path":
        preview = workspace.preview_rename_path(
            source_path=str(args["source_path"]),
            target_path=str(args["target_path"]),
        )
        return str(preview["preview"])
    if name == "copy_path":
        preview = workspace.preview_copy_path(
            source_path=str(args["source_path"]),
            target_path=str(args["target_path"]),
        )
        return str(preview["preview"])
    if name == "delete_path":
        preview = workspace.preview_delete_path(
            path=str(args["path"]),
            recursive=bool(args.get("recursive", True)),
        )
        return str(preview["preview"])
    if name == "make_directory":
        preview = workspace.preview_make_directory(
            path=str(args["path"]),
        )
        return str(preview["preview"])
    if name == "list_rollback_history":
        history = workspace.list_rollback_history(
            limit=int(args.get("limit", 12)),
            include_inactive=bool(args.get("include_inactive", True)),
        )
        return str(history["preview"])
    if name == "preview_rollback_change":
        preview = workspace.preview_rollback_change(
            rollback_id=int(args["rollback_id"]),
        )
        return str(preview["preview"])
    if name == "rollback_last_change":
        preview = workspace.preview_rollback_last_change()
        return str(preview["preview"])
    if name == "rollback_change":
        preview = workspace.preview_rollback_change(
            rollback_id=int(args["rollback_id"]),
        )
        return str(preview["preview"])
    return None


def tool_report_section(
    name: str,
    args: dict[str, Any],
    result: dict[str, Any],
    preview: str | None = None,
    policy: dict[str, Any] | None = None,
    change_plan: dict[str, Any] | None = None,
) -> str:
    parts = [
        f"#### `{name}`",
        "",
        "**输入**",
        "",
        json_block(args),
    ]
    if policy:
        parts.extend(
            [
                "**Policy**",
                "",
                json_block(
                    {
                        "risk_level": policy.get("risk_level"),
                        "approval_required": policy.get("approval_required"),
                        "destructive": policy.get("destructive"),
                        "reason": policy.get("reason"),
                    }
                ),
            ]
        )
    if change_plan:
        parts.extend(
            [
                "**变更计划**",
                "",
                json_block(change_plan),
            ]
        )
    if preview:
        parts.extend(["**预览**", "", f"```diff\n{preview}\n```", ""])
    parts.extend(
        [
            "**结果**",
            "",
            json_block(result),
        ]
    )
    text = "\n".join(parts)
    return (
        text.replace("**\u6748\u64b3\u53c6**", "**输入**")
        .replace("**\u68f0\u52ee\ue74d**", "**预览**")
        .replace("**\u7f01\u64b4\u7049**", "**结果**")
    )


def json_block(data: Any, limit: int = 3500) -> str:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    truncated = False
    if len(text) > limit:
        text = text[:limit] + "\n... (truncated)"
        truncated = True
    return f"```json\n{text}\n```" + ("\n" if truncated else "")


def text_block(text: str, limit: int = 4500) -> str:
    truncated = False
    if len(text) > limit:
        text = text[:limit] + "\n... (truncated)"
        truncated = True
    return f"```text\n{text}\n```" + ("\n" if truncated else "")
