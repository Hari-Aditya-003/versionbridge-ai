"""SQLite queue for the single local controller process."""
from contextlib import closing
import json
from uuid import uuid4
import hashlib
import os
import time
from datetime import datetime, timezone

import history

ACTIVE = ("queued", "running", "cancelling")


class Cancelled(RuntimeError):
    pass


def connect():
    db = history.connect()
    db.execute("""CREATE TABLE IF NOT EXISTS jobs (
        sequence INTEGER PRIMARY KEY, id TEXT UNIQUE, state TEXT,
        settings TEXT, events TEXT
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS submission_keys (
        key TEXT PRIMARY KEY, fingerprint TEXT, job_id TEXT
    )""")
    db.execute("CREATE TABLE IF NOT EXISTS worker_status (id INTEGER PRIMARY KEY, checked REAL, ready INTEGER)")
    db.execute("CREATE TABLE IF NOT EXISTS demo_quota (day TEXT PRIMARY KEY, count INTEGER)")
    return db


def submit(settings, idempotency_key=None):
    job_id = uuid4().hex
    with closing(connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        if idempotency_key:
            fingerprint = hashlib.sha256(json.dumps(settings).encode()).hexdigest()
            existing = db.execute("SELECT fingerprint, job_id FROM submission_keys WHERE key = ?", (idempotency_key,)).fetchone()
            if existing:
                if existing[0] != fingerprint:
                    raise ValueError("The idempotency key belongs to different repair settings.")
                return existing[1]
        count = db.execute("SELECT COUNT(*) FROM jobs WHERE state IN (?, ?, ?)", ACTIVE).fetchone()[0]
        if count >= 5:
            return None
        if os.getenv("PUBLIC_DEMO") == "1":
            day = datetime.now(timezone.utc).date().isoformat()
            row = db.execute("SELECT count FROM demo_quota WHERE day = ?", (day,)).fetchone()
            if row and row[0] >= 100:
                return None
            db.execute("""INSERT INTO demo_quota VALUES (?, 1)
                ON CONFLICT(day) DO UPDATE SET count = count + 1""", (day,))
        db.execute("INSERT INTO jobs (id, state, settings, events) VALUES (?, 'queued', ?, '[]')",
                   (job_id, json.dumps(settings)))
        if idempotency_key:
            db.execute("INSERT INTO submission_keys VALUES (?, ?, ?)", (idempotency_key, fingerprint, job_id))
        db.execute("""DELETE FROM jobs WHERE sequence IN (
            SELECT sequence FROM jobs WHERE state NOT IN (?, ?, ?)
            ORDER BY sequence DESC LIMIT -1 OFFSET 100
        )""", ACTIVE)
        db.execute("DELETE FROM submission_keys WHERE job_id NOT IN (SELECT id FROM jobs)")
    return job_id


def get(job_id, cursor):
    with closing(connect()) as db:
        row = db.execute("SELECT state, events FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    state, payload = row
    events = json.loads(payload)
    return {"id": job_id, "state": state, "cursor": len(events), "events": events[cursor:]}


def claim():
    with closing(connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT id, settings FROM jobs WHERE state = 'queued' ORDER BY sequence LIMIT 1").fetchone()
        if row:
            db.execute("UPDATE jobs SET state = 'running' WHERE id = ?", (row[0],))
            return row[0], json.loads(row[1])


def cancel(job_id):
    with closing(connect()) as db, db:
        updated = db.execute("""UPDATE jobs SET state = CASE state
            WHEN 'queued' THEN 'cancelled' ELSE 'cancelling' END
            WHERE id = ? AND state IN ('queued', 'running', 'cancelling')""", (job_id,))
        return updated.rowcount != 0


def interrupted_events():
    with closing(connect()) as db:
        rows = db.execute("SELECT events FROM jobs WHERE state IN ('running', 'cancelling')").fetchall()
    return [event for row in rows for event in json.loads(row[0])]


def interrupted():
    with closing(connect()) as db, db:
        db.execute("UPDATE jobs SET state = 'interrupted' WHERE state IN ('running', 'cancelling')")


def publish(job_id, events, *, project=None):
    final = project is not None
    with closing(connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        state = db.execute("SELECT state FROM jobs WHERE id = ?", (job_id,)).fetchone()[0]
        if state == "cancelling":
            if final:
                db.execute("UPDATE jobs SET state = 'cancelled' WHERE id = ?", (job_id,))
                return
            event = events[-1]
            if event["event"] != "sandbox" or event["status"] not in ("Removed", "Absent"):
                raise Cancelled("Cancellation requested.")
        next_state = state
        evidence = json.dumps(events)
        if final:
            next_state = {"result": "verified", "contained": "contained"}.get(events[-1]["event"], "unverified")
            history.store(db, job_id, project, next_state.capitalize(), evidence)
        db.execute("UPDATE jobs SET state = ?, events = ? WHERE id = ?",
                   (next_state, evidence, job_id))


def heartbeat(ready):
    with closing(connect()) as db, db:
        db.execute("INSERT OR REPLACE INTO worker_status VALUES (1, ?, ?)", (time.time(), int(ready)))


def worker_ready():
    with closing(connect()) as db:
        row = db.execute("SELECT checked, ready FROM worker_status WHERE id = 1").fetchone()
    return bool(row and row[1] and time.time() - row[0] < 20)
