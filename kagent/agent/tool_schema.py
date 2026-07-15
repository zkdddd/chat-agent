from __future__ import annotations

from typing import Any


def tool_schema() -> list[dict[str, Any]]:
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
                "name": "find_symbol",
                "description": "Find Python class, function, method, or import definitions by symbol name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Symbol name to find."},
                        "kind": {"type": "string", "enum": ["class", "function", "method", "import"], "description": "Optional symbol kind filter."},
                        "exact": {"type": "boolean", "description": "Whether to require an exact symbol name match. Defaults to true."},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 200, "description": "Maximum number of matches."},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "suggest_self_improvements",
                "description": (
                    "Analyze this workspace and suggest small, low-risk coding-agent improvements. "
                    "This is read-only: it does not edit files or run commands."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Maximum number of suggestions to return.",
                        },
                    },
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
                "name": "rename_path",
                "description": "Rename or move a file or directory inside the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_path": {"type": "string", "description": "Existing file or directory path inside the workspace."},
                        "target_path": {"type": "string", "description": "New file or directory path inside the workspace."},
                    },
                    "required": ["source_path", "target_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "copy_path",
                "description": "Copy a file or directory inside the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_path": {"type": "string", "description": "Existing file or directory path inside the workspace."},
                        "target_path": {"type": "string", "description": "Destination path inside the workspace."},
                    },
                    "required": ["source_path", "target_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_path",
                "description": "Delete a file or directory inside the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Existing file or directory path inside the workspace."},
                        "recursive": {"type": "boolean", "description": "Whether to delete directories recursively. Defaults to true."},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "make_directory",
                "description": "Create a directory inside the workspace when its parent already exists.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path to create inside the workspace."},
                    },
                    "required": ["path"],
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
        {
            "type": "function",
            "function": {
                "name": "list_rollback_history",
                "description": "List recent rollback records for this chat session.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Maximum number of rollback entries to return."},
                        "include_inactive": {"type": "boolean", "description": "Whether to include already applied or superseded rollback entries."},
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "preview_rollback_change",
                "description": "Preview the exact file diff for a specific rollback history id without applying it.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rollback_id": {"type": "integer", "minimum": 1, "description": "The rollback history id to inspect."},
                    },
                    "required": ["rollback_id"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "preview_rollback_session",
                "description": "Preview the current session's active rollbackable paths without applying changes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "minimum": 1, "maximum": 200, "description": "Maximum number of active rollback records to scan."},
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "preview_rollback_paths",
                "description": "Preview rollback diffs for selected paths, optionally constrained to a rollback_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "description": "Workspace-relative paths to preview.",
                        },
                        "rollback_id": {"type": "integer", "minimum": 1, "description": "Optional rollback history id to inspect."},
                    },
                    "required": ["paths"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "rollback_last_change",
                "description": "Undo the most recent workspace mutation recorded for this chat session.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "rollback_change",
                "description": "Undo a specific rollback record by its rollback_id in this chat session.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rollback_id": {"type": "integer", "minimum": 1, "description": "The rollback history id to restore."},
                    },
                    "required": ["rollback_id"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "rollback_paths",
                "description": "Rollback selected workspace paths, optionally constrained to a rollback_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "description": "Workspace-relative paths to rollback.",
                        },
                        "rollback_id": {"type": "integer", "minimum": 1, "description": "Optional rollback history id to restore from."},
                    },
                    "required": ["paths"],
                    "additionalProperties": False,
                },
            },
        },
    ]

