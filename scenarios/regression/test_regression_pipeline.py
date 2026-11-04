import pandas as pd
from regression_pipeline import append_event


class TrackedEvents(pd.DataFrame):
    """Legacy application adapter that preserves audit metadata on append."""

    def append(self, event, ignore_index=False):
        result = pd.concat([self, pd.DataFrame([event])], ignore_index=ignore_index)
        result.attrs = self.attrs.copy()
        return result


def test_standard_frame_migration():
    events = pd.DataFrame({"event": ["opened"]})
    assert append_event(events, {"event": "closed"})["event"].tolist() == ["opened", "closed"]


def test_preserve_adapter_audit_metadata():
    events = TrackedEvents({"event": ["opened"]})
    events.attrs["audit_stream"] = "billing"
    result = append_event(events, {"event": "closed"})
    assert result.attrs.get("audit_stream") == "billing"
