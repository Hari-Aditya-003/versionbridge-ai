"""Reserve a conservative inference allowance before sending a paid request."""
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import os

import history


class BudgetExceeded(RuntimeError):
    pass


def configuration():
    try:
        dollars = Decimal(os.getenv("INFERENCE_BUDGET_USD", "5"))
        input_rate = Decimal(os.getenv("INFERENCE_INPUT_USD_PER_MILLION", "3"))
        output_rate = Decimal(os.getenv("INFERENCE_OUTPUT_USD_PER_MILLION", "3"))
        daily_requests = int(os.getenv("INFERENCE_DAILY_REQUESTS", "30"))
        if not all(value.is_finite() and value >= 0 for value in (dollars, input_rate, output_rate)):
            raise ValueError
        if input_rate == 0 or output_rate == 0 or not 0 <= daily_requests <= 1000 or dollars > 200:
            raise ValueError
        return int(dollars * 1_000_000), input_rate, output_rate, daily_requests
    except (ValueError, ArithmeticError) as exc:
        raise RuntimeError("Invalid inference budget configuration.") from exc


def connect():
    db = history.connect()
    db.execute("""CREATE TABLE IF NOT EXISTS inference_allowances (
        id INTEGER PRIMARY KEY, day TEXT, reserved_microdollars INTEGER
    )""")
    return db


def reserve(request_bytes, max_output_tokens):
    limit, input_rate, output_rate, daily_limit = configuration()
    # Tokenization cannot produce more ordinary tokens than UTF-8 bytes.
    # Reserve additional framing tokens and never refund failed requests.
    estimate = (Decimal(request_bytes + 4096) * input_rate
                + Decimal(max_output_tokens) * output_rate)
    reserved = int(estimate.to_integral_value(rounding=ROUND_CEILING))
    day = datetime.now(timezone.utc).date().isoformat()
    with closing(connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        total = db.execute("SELECT COALESCE(SUM(reserved_microdollars), 0) FROM inference_allowances").fetchone()[0]
        count = db.execute("SELECT COUNT(*) FROM inference_allowances WHERE day = ?", (day,)).fetchone()[0]
        if total + reserved > limit or count >= daily_limit:
            raise BudgetExceeded("Inference allowance exhausted. Review the configured budget before continuing.")
        cursor = db.execute("INSERT INTO inference_allowances (day, reserved_microdollars) VALUES (?, ?)",
                            (day, reserved))
        return {"reservation_id": cursor.lastrowid, "reserved_usd": reserved / 1_000_000}


def status():
    limit, _, _, daily_limit = configuration()
    day = datetime.now(timezone.utc).date().isoformat()
    with closing(connect()) as db:
        total, count = db.execute("""SELECT COALESCE(SUM(reserved_microdollars), 0),
            COUNT(CASE WHEN day = ? THEN 1 END) FROM inference_allowances""", (day,)).fetchone()
    return {"limit_usd": limit / 1_000_000, "reserved_usd": total / 1_000_000,
            "remaining_usd": max(0, limit - total) / 1_000_000,
            "requests_today": count, "daily_request_limit": daily_limit,
            "scope": "Application inference reservations. VM, bandwidth, and other account charges are separate."}
