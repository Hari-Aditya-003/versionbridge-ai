"""Bounded migration policy and bundled acceptance cases."""
from dataclasses import dataclass

PANDAS_CALL = "    return events.append(event, ignore_index=True)"


@dataclass(frozen=True)
class Profile:
    title: str
    fixture: str
    original: str
    candidates: tuple[str, ...]
    failure: str
    arithmetic_names: tuple[str, ...] = ()


PROFILES = {
    "billing": Profile("Python · invoice total bug", "scenarios/billing",
                       "    return unit_cents + quantity + fee_cents",
                       ("    return unit_cents * quantity + fee_cents",),
                       "test_invoice_total", ("unit_cents", "quantity", "fee_cents")),
    "pandas": Profile("pandas 2 · removed append API", "fixture", PANDAS_CALL, (
        "    return pd.concat([events, pd.DataFrame([event])], ignore_index=True)",
        "    return pd.concat([events, pd.Series(event).to_frame().T], ignore_index=True)",
    ), "has no attribute 'append'"),
    "settings": Profile("Pydantic 2 · settings import", "scenarios/settings",
                        "from pydantic import BaseSettings",
                        ("from pydantic_settings import BaseSettings",), "PydanticImportError"),
    "regression": Profile("pandas 2 · regression guard", "scenarios/regression", PANDAS_CALL, (
        "    return pd.concat([events, pd.DataFrame([event])], ignore_index=True)",
        "    return pd.concat([events, pd.Series(event).to_frame().T], ignore_index=True)",
    ), "has no attribute 'append'"),
}
