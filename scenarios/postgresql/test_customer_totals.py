import csv
from io import StringIO
from pathlib import Path
import subprocess

import pytest


@pytest.fixture(scope="session")
def postgres():
    binaries = sorted(Path("/usr/lib/postgresql").glob("*/bin"))
    assert binaries, "PostgreSQL toolchain is missing"
    binary = binaries[-1]
    data = Path("/tmp/versionbridge-postgres")
    result = subprocess.run(
        [str(binary / "initdb"), "-D", str(data), "--auth=trust", "--no-locale", "--encoding=UTF8"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    command = [str(binary / "pg_ctl"), "-D", str(data)]
    result = subprocess.run(
        command + ["-l", "/tmp/postgres.log", "-o",
                   "-k /tmp -h '' -c shared_buffers=16MB -c max_connections=5", "-w", "start"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    try:
        yield [str(binary / "psql"), "-h", "/tmp", "-d", "postgres", "-X", "-A", "-t",
               "-v", "ON_ERROR_STOP=1"]
    finally:
        subprocess.run(command + ["-m", "immediate", "-w", "stop"], capture_output=True, timeout=10)


@pytest.mark.parametrize(("customers", "orders", "expected"), [
    ("", "", []),
    ("INSERT INTO customers VALUES (1);", "", [(1, 0, 0)]),
    ("INSERT INTO customers VALUES (2), (1);",
     "INSERT INTO orders(customer_id, cents, status) VALUES (1,300,'paid'),(1,300,'paid'),(2,400,'void');",
     [(1, 2, 600), (2, 0, 0)]),
    ("INSERT INTO customers VALUES (1);",
     "INSERT INTO orders(customer_id, cents, status) VALUES (1,NULL,'paid');", [(1, 1, 0)]),
], ids=["empty", "no-orders", "duplicates-and-void", "null-amount"])
def test_customer_totals(postgres, customers, orders, expected):
    setup = """
        DROP TABLE IF EXISTS orders, customers;
        CREATE TABLE customers (id INTEGER PRIMARY KEY);
        CREATE TABLE orders (id SERIAL PRIMARY KEY, customer_id INTEGER, cents INTEGER, status TEXT);
    """ + customers + orders
    result = subprocess.run(postgres + ["-c", setup], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    query = Path(__file__).with_name("customer_totals.sql").read_text().strip().removesuffix(";")
    result = subprocess.run(
        postgres + ["-c", "BEGIN READ ONLY; COPY (" + query + ") TO STDOUT WITH CSV; ROLLBACK;"],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr
    rows = [row for row in csv.reader(StringIO(result.stdout)) if len(row) == 3]
    assert [tuple(map(int, row)) for row in rows] == expected
