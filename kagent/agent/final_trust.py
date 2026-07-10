from __future__ import annotations

from typing import Any


def build_final_trust_summary(
    *,
    status: str,
    content_changed: bool,
    changed_paths: list[str],
    validated: bool,
    validation_failed: bool,
    last_validation_summary: str | None = None,
    failed_tool_count: int = 0,
    loop_warning_count: int = 0,
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if status != "completed":
        issues.append(
            {
                "severity": "fail",
                "code": "run_not_completed",
                "message": f"Run finished with status `{status}`.",
            }
        )
    if content_changed and changed_paths and not validated:
        issues.append(
            {
                "severity": "fail",
                "code": "unverified_changes",
                "message": "Workspace files changed, but validation did not run or did not complete.",
            }
        )
    if validation_failed:
        issues.append(
            {
                "severity": "fail",
                "code": "validation_failed",
                "message": last_validation_summary or "Validation failed.",
            }
        )
    if failed_tool_count > 0:
        issues.append(
            {
                "severity": "warn",
                "code": "failed_tools",
                "message": f"{failed_tool_count} tool call(s) failed during the run.",
            }
        )
    if loop_warning_count > 0:
        issues.append(
            {
                "severity": "warn",
                "code": "loop_warning",
                "message": f"{loop_warning_count} loop warning(s) were emitted.",
            }
        )

    severities = {issue["severity"] for issue in issues}
    health = "fail" if "fail" in severities else "warn" if "warn" in severities else "pass"
    return {
        "health": health,
        "trustworthy": health == "pass",
        "status": status,
        "changed_paths": changed_paths,
        "validated": validated,
        "validation_failed": validation_failed,
        "failed_tool_count": failed_tool_count,
        "loop_warning_count": loop_warning_count,
        "issues": issues,
    }


def final_trust_prompt(summary: dict[str, Any]) -> str:
    issues = summary.get("issues") if isinstance(summary.get("issues"), list) else []
    lines = [
        "Final response trust check.",
        f"- health: {summary.get('health')}",
        f"- trustworthy: {'yes' if summary.get('trustworthy') else 'no'}",
        f"- validated: {'yes' if summary.get('validated') else 'no'}",
        f"- validation_failed: {'yes' if summary.get('validation_failed') else 'no'}",
    ]
    changed_paths = summary.get("changed_paths") if isinstance(summary.get("changed_paths"), list) else []
    if changed_paths:
        lines.append("- changed_paths: " + ", ".join(str(path) for path in changed_paths[:12]))
    if issues:
        lines.append("- required_disclosures:")
        for issue in issues:
            lines.append(f"  - [{issue['severity']}] {issue['code']}: {issue['message']}")
    else:
        lines.append("- required_disclosures: none")
    lines.append(
        "In the final answer, explicitly mention any fail issue. Mention warn issues briefly as residual risk. "
        "Do not claim validation passed unless validated=yes and validation_failed=no."
    )
    return "\n".join(lines)
