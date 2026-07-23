from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .run_log import read_run_events, summarize_run_log


def build_junit_xml(run_log_path: str | Path) -> str:
    """Build a standard JUnit XML report for a run log.

    Reads `test_case_result` events from the JSONL run log and emits a
    `<testsuite>` with one `<testcase>` per recorded test (including
    `<failure>` / `<error>` / `<skipped>` children). When the run log has no
    per-test events (e.g. validation did not run or used a non-pytest command),
    it falls back to a single run-level testcase summarizing the run status, so
    the export always produces a valid, CI-consumable JUnit document.
    """
    path = Path(run_log_path)
    events = read_run_events(path)
    cases = _test_case_results(events)
    summary = summarize_run_log(path)

    run_id = str(summary.get("run_id") or path.stem)
    suite_name = f"kagent-run-{run_id[:12]}"
    timestamp = str(summary.get("started_at") or "")

    suite = ET.Element(
        "testsuite",
        {
            "name": suite_name,
            "tests": str(len(cases)) if cases else "1",
            "timestamp": timestamp,
        },
    )

    if cases:
        _populate_cases(suite, cases)
    else:
        _populate_run_level_summary(suite, summary)

    _set_suite_counts(suite)
    _indent(suite)
    return ET.tostring(suite, encoding="unicode")


def _test_case_results(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for event in events:
        if event.get("event") != "test_case_result":
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        results.append(data)
    return results


def _populate_cases(suite: ET.Element, cases: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for case in cases:
        nodeid = str(case.get("nodeid") or "")
        if not nodeid or nodeid in seen:
            continue
        seen.add(nodeid)
        classname = str(case.get("classname") or _classname_from_nodeid(nodeid))
        name = str(case.get("name") or _name_from_nodeid(nodeid))
        status = str(case.get("status") or "unknown")
        duration_ms = _int(case.get("duration_ms"))
        time_attr = f"{duration_ms / 1000:.3f}" if duration_ms else "0"

        testcase = ET.SubElement(
            suite, "testcase", {"classname": classname, "name": name, "time": time_attr}
        )
        message = str(case.get("message") or "")
        failure_type = str(case.get("failure_type") or "")
        if status in {"failed", "error"}:
            child_tag = "failure" if status == "failed" else "error"
            attrs: dict[str, str] = {}
            if failure_type:
                attrs["type"] = failure_type
            if message:
                attrs["message"] = message
            child = ET.SubElement(testcase, child_tag, attrs)
            if message:
                child.text = message
        elif status == "skipped":
            ET.SubElement(testcase, "skipped")
        elif status not in {"passed"}:
            # Unknown status: record as a skipped-ish note without dropping it.
            ET.SubElement(testcase, "skipped", {"message": f"status={status}"})


def _populate_run_level_summary(suite: ET.Element, summary: dict[str, Any]) -> None:
    status = str(summary.get("status") or "unknown")
    validation_failed = bool(summary.get("validation_failed"))
    failed = status != "completed" or validation_failed
    testcase = ET.SubElement(
        suite, "testcase", {"classname": "kagent.run", "name": "run-summary", "time": "0"}
    )
    if failed:
        message = "validation_failed" if validation_failed else f"run status: {status}"
        failure = ET.SubElement(testcase, "failure", {"message": message})
        failure.text = str(summary.get("last_validation_summary") or message)


def _set_suite_counts(suite: ET.Element) -> None:
    testcases = suite.findall("testcase")
    failures = sum(1 for tc in testcases if tc.find("failure") is not None)
    errors = sum(1 for tc in testcases if tc.find("error") is not None)
    skipped = sum(1 for tc in testcases if tc.find("skipped") is not None)
    suite.set("tests", str(len(testcases)))
    suite.set("failures", str(failures))
    suite.set("errors", str(errors))
    suite.set("skipped", str(skipped))


def _classname_from_nodeid(nodeid: str) -> str:
    head = nodeid.split("::", 1)[0]
    return head.replace("/", ".").replace("\\", ".")


def _name_from_nodeid(nodeid: str) -> str:
    parts = nodeid.split("::")
    return parts[-1] if parts else nodeid


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _indent(element: ET.Element, level: int = 0) -> None:
    indent = "\n" + "  " * level
    if len(element):
        if not element.text or not element.text.strip():
            element.text = indent + "  "
        for child in element:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    if level and (not element.tail or not element.tail.strip()):
        element.tail = indent
