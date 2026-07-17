# KAGENT.md

Project-level rules for KAgent. Keep this file short, concrete, and updated when the Agent workflow changes.

## Project Overview

- KAgent is a local desktop coding Agent built with Python and PyQt.
- Current priority: improve coding-agent capability before broad product expansion.
- Main source directory: `kagent/`.
- Test directory: `tests/`.
- Development log: `docs/agent-development.md`.
- Resume showcase: `docs/resume-project.md`.

## Coding Rules

- Prefer small, reviewable edits over broad rewrites.
- Inspect related files, symbols, and tests before changing behavior.
- Preserve unrelated user changes in the working tree.
- Use `apply_patch` for manual code edits.
- Add or update tests for Agent behavior changes when practical.
- Document every feature or optimization in `README.md` and `docs/agent-development.md`.

## Validation

- Run targeted tests first when the changed area is clear.
- Run full validation before finishing larger coding-agent changes:

```powershell
.\run-tests.bat
```

- Treat validation output as part of the final handoff: mention what passed or what could not be run.

## Safety

- Do not run destructive git or filesystem commands unless the user explicitly asks.
- Do not install dependencies or use network commands unless needed for the task.
- Before risky edits, identify target files, reason, and validation plan.

## Agent Workflow Preferences

- For code tasks, keep moving end-to-end: inspect, edit, test, document, then summarize.
- For each completed step, tell the user what changed, what was verified, and the next recommended step.
- Prefer Simplified Chinese for user-facing progress and final responses.
