"""Exercise the controlled repair and the actual Docker containment probes."""
from server import containment, repair


def capture(action, *args):
    events = []
    action(lambda name, data: events.append({"event": name, **data}), *args)
    return events


if __name__ == "__main__":
    repair_events = capture(repair, "smoke-test")
    report = repair_events[-1]
    assert report["event"] == "result"
    assert "2 failed" in report["before"] and "2 passed" in report["after"]
    assert report["baseline_exit_code"] == 1 and report["verification_exit_code"] == 0
    repair_sandboxes = [event for event in repair_events if event["event"] == "sandbox"]
    assert [event["status"] for event in repair_sandboxes] == ["Dispatching", "Removed"] * 2
    assert repair_sandboxes[0]["name"] != repair_sandboxes[2]["name"]

    probe_events = capture(containment)
    assert probe_events[-1]["event"] == "contained"
    assert any(event.get("timed_out") and event["status"] == "Removed" for event in probe_events)
    print("Baseline failure, passing patch, unique container IDs, timeout and teardown verified.")
