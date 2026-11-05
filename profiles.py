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
    language: str = "Python"
    suffix: str = ".py"
    bundled_only: bool = False
    native: bool = False
    timeout: int = 35


PROFILES = {
    "go": Profile("Go · pagination boundary", "scenarios/go",
                  "    return items / size", ("    return (items + size - 1) / size",),
                  "test_compiled_contract", language="Go", suffix=".go", bundled_only=True, native=True, timeout=75),
    "rust": Profile("Rust · inclusive limit", "scenarios/rust",
                    "    value < limit", ("    value <= limit",),
                    "test_compiled_contract", language="Rust", suffix=".rs", bundled_only=True, native=True),
    "java": Profile("Java · role string comparison", "scenarios/java",
                    '        return role == "admin";', ('        return "admin".equals(role);',),
                    "test_compiled_contract", language="Java", suffix=".java", bundled_only=True, native=True),
    "cpp": Profile("C++ · integer overflow", "scenarios/cpp",
                   "    return a * b;", ("    return static_cast<long long>(a) * b;",),
                   "test_compiled_contract", language="C++", suffix=".cpp", bundled_only=True, native=True),
    "typescript": Profile("TypeScript · inventory field mismatch", "scenarios/typescript",
                          "  return item?.quantity ?? 0;",
                          ("  return item?.available ?? 0;",),
                          "TS2339", language="TypeScript", suffix=".ts", bundled_only=True),
    "javascript": Profile("JavaScript · enforce discount cap", "scenarios/javascript",
                          "  const deduction = Math.min(subtotal, discount);",
                          ("  const deduction = Math.min(subtotal, discount, cap);",),
                          "test_discount_total", language="JavaScript", suffix=".mjs", bundled_only=True),
    "postgresql": Profile("PostgreSQL · count paid orders", "scenarios/postgresql",
                      "SELECT c.id, COUNT(*) AS paid_orders, COALESCE(SUM(o.cents), 0) AS total_cents",
                      ("SELECT c.id, COUNT(o.id) AS paid_orders, COALESCE(SUM(o.cents), 0) AS total_cents",),
                      "test_customer_totals", language="PostgreSQL SQL", suffix=".sql", bundled_only=True),
    "sqlite": Profile("SQLite · count paid orders", "scenarios/sqlite",
                      "SELECT c.id, COUNT(*) AS paid_orders, COALESCE(SUM(o.cents), 0) AS total_cents",
                      ("SELECT c.id, COUNT(o.id) AS paid_orders, COALESCE(SUM(o.cents), 0) AS total_cents",),
                      "test_customer_totals", language="SQLite SQL", suffix=".sql", bundled_only=True),
    "algorithm": Profile("Algorithm · count values at or below a threshold", "scenarios/algorithm",
                         "    return bisect_left(ordered, threshold)",
                         ("    return bisect_right(ordered, threshold)",),
                         "test_rank", bundled_only=True),
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
