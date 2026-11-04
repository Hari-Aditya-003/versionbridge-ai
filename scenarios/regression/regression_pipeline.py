import pandas as pd


def append_event(events, event):
    return events.append(event, ignore_index=True)
