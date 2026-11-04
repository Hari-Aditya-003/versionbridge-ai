import pandas as pd
from pipeline import append_event


def test_append_event():
    events = pd.DataFrame({"event": ["opened"]}, index=[42])
    result = append_event(events, {"event": "closed"})
    assert result.to_dict("records") == [{"event": "opened"}, {"event": "closed"}]
    assert result.index.tolist() == [0, 1]
    assert events.index.tolist() == [42]


def test_append_event_to_empty_frame():
    result = append_event(pd.DataFrame(columns=["event"]), {"event": "created"})
    assert result.to_dict("records") == [{"event": "created"}]
