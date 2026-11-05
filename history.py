"""Persist bounded run summaries for the workspace."""
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3

DB = Path(os.environ.get("VERSIONBRIDGE_DB", Path(__file__).resolve().parent / "data/runs.sqlite3"))


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    if DB.stat().st_uid == os.geteuid():
        DB.chmod(0o660)
    db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created TEXT, project TEXT, status TEXT, evidence TEXT)")
    return db


def store(db, run_id, project, status, evidence):
    db.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?)", (
        run_id, datetime.now(timezone.utc).isoformat(), project, status, evidence,
    ))
    db.execute("DELETE FROM runs WHERE id IN (SELECT id FROM runs ORDER BY created DESC LIMIT -1 OFFSET 100)")


def save(run_id, project, status, evidence):
    with closing(connect()) as db, db:
        store(db, run_id, project, status, json.dumps(evidence))


def recent():
    with closing(connect()) as db, db:
        return [{"id": row[0], "created": row[1], "project": row[2], "status": row[3],
                 "evidence": json.loads(row[4])}
                for row in db.execute("SELECT * FROM runs ORDER BY created DESC LIMIT 25")]


def find(run_id):
    with closing(connect()) as db:
        row = db.execute("SELECT evidence FROM runs WHERE id = ?", (run_id,)).fetchone()
    return json.loads(row[0]) if row else None


def stats():
    with closing(connect()) as db:
        counts = dict(db.execute("SELECT status, COUNT(*) FROM runs GROUP BY status"))
    return {"retained_runs": sum(counts.values()), "verified": counts.get("Verified", 0),
            "unverified": counts.get("Unverified", 0), "retention_limit": 100}
