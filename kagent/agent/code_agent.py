from __future__ import annotations

import json
from typing import Any, Callable

from ..config import AGENT_SYSTEM_PROMPT, MODEL
from ..llm import client
from .workspace import WorkspaceError, WorkspaceTools

EmitFn = Callable[[str], None]
EventFn = Callable[[dict[str, Any]], None]
StopFn = Callable[[], bool]

AGENT_WORKFLOW_HINT = """
Use the workspace tools in this order when it helps:
1. list_files to inspect the project tree.
2. search_file to locate symbols, files, or text.
3. read_file for focused excerpts.
4. apply_patch for targeted edits when possible.
5. write_file only when a full replacement is simpler.
6. run_command to validate after edits.

Prefer small, reviewable changes. If a command fails, inspect the output and fix the real cause before continuing.
"""


def _tool_schema() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories in the workspace. Use this to inspect project structure before reading files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path relative to the workspace root or an absolute path inside the workspace."},
                        "max_depth": {"type": "integer", "minimum": 0, "description": "Maximum depth below the start path."},
                        "include_dirs": {"type": "boolean", "description": "Whether to include directories in the listing."},
                        "include_hidden": {"type": "boolean", "description": "Whether to include hidden files and directories."},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 2000, "description": "Maximum number of entries to return."},
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_file",
                "description": "Search text inside workspace files and return matching lines with context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Text to search for."},
                        "path": {"type": "string", "description": "Directory or file path relative to the workspace root or an absolute path inside the workspace."},
                        "file_glob": {"type": "string", "description": "Optional filename glob such as *.py or *.md."},
                        "case_sensitive": {"type": "boolean", "description": "Whether the search should be case sensitive."},
                        "include_hidden": {"type": "boolean", "description": "Whether to include hidden files and directories."},
                        "context_lines": {"type": "integer", "minimum": 0, "description": "Number of surrounding lines to include."},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 1000, "description": "Maximum number of matches to return."},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a UTF-8 text file from the workspace. Paths should be relative to the workspace root when possible.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path relative to the workspace root or an absolute path inside the workspace."},
                        "start_line": {"type": "integer", "minimum": 1, "description": "Optional 1-based starting line."},
                        "end_line": {"type": "integer", "minimum": 1, "description": "Optional 1-based ending line."},
                        "max_chars": {"type": "integer", "minimum": 1, "description": "Maximum characters to return from the selected range."},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Overwrite a UTF-8 text file inside the workspace with the provided full content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path relative to the workspace root or an absolute path inside the workspace."},
                        "content": {"type": "string", "description": "Full file content to write."},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "apply_patch",
                "description": "Apply a unified diff patch to files inside the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patch": {"type": "string", "description": "A unified diff patch beginning with diff --git lines."},
                    },
                    "required": ["patch"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Run a shell command inside the workspace root or an allowed workspace subdirectory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The shell command to run."},
                        "cwd": {"type": "string", "description": "Optional working directory relative to the workspace root or an absolute path inside the workspace."},
                        "timeout_ms": {"type": "integer", "minimum": 1, "description": "Command timeout in milliseconds."},
                    },
                    "required": ["command"],
                    "additionalProperties": False,
                },
            },
        },
    ]


class CodeAgent:
    def __init__(self, workspace_root: str | None = None, model: str = MODEL):
        self.workspace = WorkspaceTools(workspace_root) if workspace_root else WorkspaceTools()
        self.model = model

    @staticmethod
    def _json_block(data: Any, limit: int = 3500) -> str:
        text = json.dumps(data, ensure_ascii=False, indent=2)
        truncated = False
        if len(text) > limit:
            text = text[:limit] + "\n... (truncated)"
            truncated = True
        return f"```json\n{text}\n```" + ("\n" if truncated else "")

    @staticmethod
    def _text_block(text: str, limit: int = 4500) -> str:
        truncated = False
        if len(text) > limit:
            text = text[:limit] + "\n... (truncated)"
            truncated = True
        return f"```text\n{text}\n```" + ("\n" if truncated else "")

    def _tool_display_args(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
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
        return self.workspace.preview_patch(patch)

    @staticmethod
    def _tool_preview_text(name: str, args: dict[str, Any]) -> str | None:
        if name != "apply_patch":
            return None
        patch = str(args.get("patch") or "")
        return patch or None

    def _tool_report_section(
        self,
        name: str,
        args: dict[str, Any],
        result: dict[str, Any],
        preview: str | None = None,
    ) -> str:
        parts = [
            f"#### `{name}`",
            "",
            "**输入**",
            "",
            self._json_block(args),
        ]
        if preview:
            parts.extend(["**预览**", "", f"```diff\n{preview}\n```", ""])
        parts.extend(
            [
                "**结果**",
                "",
                self._json_block(result),
            ]
        )
        return "\n".join(parts)

    def _emit(self, emit: EmitFn | None, parts: list[str], text: str) -> None:
        parts.append(text)
        if emit:
            emit(text)

    def _emit_event(self, on_event: EventFn | None, event: dict[str, Any]) -> None:
        if on_event:
            on_event(event)

    def _dispatch_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "list_files":
            return self.workspace.list_files(
                path=str(args.get("path", ".")),
                max_depth=args.get("max_depth", 3),
                include_dirs=bool(args.get("include_dirs", True)),
                include_hidden=bool(args.get("include_hidden", False)),
                max_results=int(args.get("max_results", 500)),
            )
        if name == "search_file":
            return self.workspace.search_file(
                query=str(args["query"]),
                path=str(args.get("path", ".")),
                file_glob=str(args.get("file_glob", "*")),
                case_sensitive=bool(args.get("case_sensitive", False)),
                include_hidden=bool(args.get("include_hidden", False)),
                context_lines=int(args.get("context_lines", 1)),
                max_results=int(args.get("max_results", 50)),
            )
        if name == "read_file":
            return self.workspace.read_file(
                path=str(args["path"]),
                start_line=args.get("start_line"),
                end_line=args.get("end_line"),
                max_chars=int(args.get("max_chars", 20000)),
            )
        if name == "write_file":
            return self.workspace.write_file(
                path=str(args["path"]),
                content=str(args["content"]),
            )
        if name == "apply_patch":
            return self.workspace.apply_patch(
                patch=str(args["patch"]),
            )
        if name == "run_command":
            return self.workspace.run_command(
                command=str(args["command"]),
                cwd=args.get("cwd"),
                timeout_ms=int(args.get("timeout_ms", 120000)),
            )
        raise WorkspaceError(f"Unknown tool: {name}")

    def run(
        self,
        history: list[dict[str, Any]],
        emit: EmitFn | None = None,
        on_event: EventFn | None = None,
        should_stop: StopFn | None = None,
        max_rounds: int = 12,
    ) -> str:
        if not history:
            raise WorkspaceError("history is required")

        user_task = ""
        for item in reversed(history):
            if item.get("role") == "user":
                user_task = str(item.get("content", ""))
                break

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    AGENT_SYSTEM_PROMPT.format(workspace_root=str(self.workspace.root))
                    + "\n\n"
                    + AGENT_WORKFLOW_HINT
                ),
            }
        ]
        for item in history:
            if item.get("role") in ("user", "assistant"):
                messages.append(
                    {
                        "role": item["role"],
                        "content": str(item.get("content", "")),
                    }
                )

        report_parts: list[str] = []
        self._emit_event(
            on_event,
            {
                "type": "agent_start",
                "task": user_task,
                "workspace_root": str(self.workspace.root),
            },
        )
        self._emit(
            emit,
            report_parts,
            "### 任务\n\n"
            f"{user_task}\n\n"
            f"### 工作区\n\n`{self.workspace.root}`\n",
        )

        for round_idx in range(max_rounds):
            if should_stop and should_stop():
                self._emit(emit, report_parts, "\n> 已中止\n")
                return "".join(report_parts)

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=_tool_schema(),
                tool_choice="auto",
                temperature=0.2,
            )

            assistant = response.choices[0].message
            assistant_dump = assistant.model_dump(exclude_none=True)
            messages.append(assistant_dump)

            tool_calls = assistant.tool_calls or []
            assistant_text = (assistant.content or "").strip()
            if not tool_calls:
                final_text = assistant_text
                if not final_text:
                    final_text = "已完成。"
                self._emit(emit, report_parts, f"### 结果\n\n{final_text}\n")
                return "".join(report_parts)

            if assistant_text:
                self._emit(emit, report_parts, f"{assistant_text}\n\n")

            self._emit(emit, report_parts, f"### 工具调用 {round_idx + 1}\n")
            for tool_call in tool_calls:
                if should_stop and should_stop():
                    self._emit(emit, report_parts, "\n> 已中止\n")
                    return "".join(report_parts)

                name = tool_call.function.name
                raw_args = tool_call.function.arguments or "{}"
                args: dict[str, Any] = {}
                display_args: dict[str, Any]
                preview_text: str | None = None
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError as exc:
                    display_args = {"raw_arguments": raw_args}
                    self._emit_event(
                        on_event,
                        {
                            "type": "tool_start",
                            "call_id": tool_call.id,
                            "name": name,
                            "args": display_args,
                            "round": round_idx + 1,
                        },
                    )
                    result = {"ok": False, "error": f"Invalid JSON arguments: {exc}", "raw_arguments": raw_args}
                else:
                    display_args = self._tool_display_args(name, args)
                    preview_text = self._tool_preview_text(name, args)
                    self._emit_event(
                        on_event,
                        {
                            "type": "tool_start",
                            "call_id": tool_call.id,
                            "name": name,
                            "args": display_args,
                            "round": round_idx + 1,
                        },
                    )
                    if preview_text:
                        self._emit_event(
                            on_event,
                            {
                                "type": "tool_preview",
                                "call_id": tool_call.id,
                                "name": name,
                                "args": display_args,
                                "preview": preview_text,
                                "round": round_idx + 1,
                            },
                        )
                    try:
                        result = self._dispatch_tool(name, args)
                    except Exception as exc:
                        result = {"ok": False, "error": str(exc)}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

                self._emit_event(
                    on_event,
                    {
                        "type": "tool_result",
                        "call_id": tool_call.id,
                        "name": name,
                        "args": display_args,
                        "result": result,
                        "round": round_idx + 1,
                        "ok": bool(result.get("ok", True)),
                    },
                )

                self._emit(
                    emit,
                    report_parts,
                    self._tool_report_section(name, display_args, result, preview=preview_text),
                )

        self._emit(
            emit,
            report_parts,
            "### 结果\n\n"
            "已达到最大轮次限制，未能自动收敛到最终答案。"
            " 请查看工具输出，或者再发一条更明确的指令继续。",
        )
        return "".join(report_parts)
