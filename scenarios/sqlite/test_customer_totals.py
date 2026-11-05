from pathlib import Path
import sqlite3

import pytest

QUERY = Path(__file__).with_name("customer_totals.sql").read_text()


@pytest.mark.parametrize(("customers", "orders", "expected"), [
    ([], [], []),
    ([(1,)], [], [(1, 0, 0)]),
    ([(2,), (1,)], [(1, 300, "paid"), (1, 300, "paid"), (2, 400, "void")],
     [(1, 2, 600), (2, 0, 0)]),
    ([(1,)], [(1, None, "paid"), (1, 100, None)], [(1, 1, 0)]),
])
def test_customer_totals(customers, orders, expected):
    with sqlite3.connect(":memory:") as db:
        db.executescript("""
            CREATE TABLE customers (id INTEGER PRIMARY KEY);
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY, customer_id INTEGER, cents INTEGER, status TEXT
            );
        """)
        db.executemany("INSERT INTO customers VALUES (?)", customers)
        db.executemany("INSERT INTO orders (customer_id, cents, status) VALUES (?, ?, ?)", orders)
        db.execute("PRAGMA query_only = ON")
        assert db.execute(QUERY).fetchall() == expected
