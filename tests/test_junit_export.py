import xml.etree.ElementTree as ET

from kagent.agent.junit_export import build_junit_xml
from kagent.agent.run_log import RunLogger


def _parse(xml_text: str) -> ET.Element:
    return ET.fromstring(xml_text)


def test_build_junit_xml_emits_one_testcase_per_recorded_test(tmp_path):
    log = RunLogger(session_id="s", workspace_root=str(tmp_path))
    log.write(
        "test_case_result",
        {
            "nodeid": "tests/test_x.py::test_a",
            "status": "passed",
            "duration_ms": 120,
            "classname": "tests.test_x",
            "name": "test_a",
        },
    )
    log.write(
        "test_case_result",
        {
            "nodeid": "tests/test_x.py::test_b",
            "status": "failed",
            "duration_ms": 80,
            "message": "assert False",
            "failure_type": "AssertionError",
            "classname": "tests.test_x",
            "name": "test_b",
        },
    )
    log.write(
        "test_case_result",
        {
            "nodeid": "tests/test_x.py::test_c",
            "status": "skipped",
            "duration_ms": 0,
            "classname": "tests.test_x",
            "name": "test_c",
        },
    )
    log.finish("completed", {"validated": False, "validation_failed": True})

    root = _parse(build_junit_xml(log.path))

    assert root.tag == "testsuite"
    assert root.get("tests") == "3"
    assert root.get("failures") == "1"
    assert root.get("skipped") == "1"
    assert root.get("errors") == "0"
    cases = root.findall("testcase")
    assert [c.get("name") for c in cases] == ["test_a", "test_b", "test_c"]
    assert cases[0].find("failure") is None
    assert cases[1].find("failure") is not None
    assert cases[1].find("failure").get("type") == "AssertionError"
    assert cases[2].find("skipped") is not None
    # Duration is rendered in seconds (3 decimal places).
    assert cases[0].get("time") == "0.120"


def test_build_junit_xml_dedupes_repeated_nodeids(tmp_path):
    log = RunLogger(session_id="s", workspace_root=str(tmp_path))
    for _ in range(2):
        log.write(
            "test_case_result",
            {"nodeid": "tests/test_x.py::test_a", "status": "passed", "duration_ms": 10},
        )
    log.finish("completed", {"validated": True})

    root = _parse(build_junit_xml(log.path))

    assert root.get("tests") == "1"
    assert len(root.findall("testcase")) == 1


def test_build_junit_xml_falls_back_to_run_summary_without_per_test(tmp_path):
    log = RunLogger(session_id="s", workspace_root=str(tmp_path))
    log.finish("completed", {"validated": False, "validation_failed": True, "last_validation_summary": "1 failed"})

    root = _parse(build_junit_xml(log.path))

    assert root.tag == "testsuite"
    assert root.get("tests") == "1"
    assert root.get("failures") == "1"
    case = root.find("testcase")
    assert case is not None
    assert case.find("failure") is not None


def test_build_junit_xml_run_summary_passes_for_clean_run(tmp_path):
    log = RunLogger(session_id="s", workspace_root=str(tmp_path))
    log.finish("completed", {"validated": True})

    root = _parse(build_junit_xml(log.path))

    assert root.get("failures") == "0"
    assert root.find("testcase").find("failure") is None


def test_build_junit_xml_is_valid_xml(tmp_path):
    log = RunLogger(session_id="s", workspace_root=str(tmp_path))
    log.write("test_case_result", {"nodeid": "tests/x::t", "status": "passed", "duration_ms": 5})
    log.finish("completed", {"validated": True})

    # Must parse without error and be serializable.
    xml_text = build_junit_xml(log.path)
    ET.fromstring(xml_text)
    assert "<?xml" not in xml_text  # toString without declaration is fine for CI ingestion
