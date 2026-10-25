"""Offline durable outbox with fail-closed replay rejection."""
import hashlib
import sqlite3
from pathlib import Path
from .adapter import _check

class Outbox:
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.execute("PRAGMA busy_timeout = 3000")
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS deliveries (
            event_id TEXT PRIMARY KEY, body_sha256 TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('RESERVED','ACKED','UNCERTAIN')),
            acknowledgment_sha256 TEXT)""")
    def reserve(self, event_id: str, body: bytes) -> str:
        digest = hashlib.sha256(body).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            exists = self.db.execute("SELECT body_sha256,state FROM deliveries WHERE event_id=?", (event_id,)).fetchone()
            _check(exists is None, "DUPLICATE_OR_UNKNOWN_DELIVERY")
            self.db.execute("INSERT INTO deliveries VALUES (?,?,?,NULL)", (event_id, digest, "RESERVED"))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return digest
    def mark_acknowledged(self, event_id: str, digest: str, acknowledgment: bytes):
        _check(bool(acknowledgment), "EMPTY_ACKNOWLEDGMENT")
        ack_hash = hashlib.sha256(acknowledgment).hexdigest()
        changed = self.db.execute(
            "UPDATE deliveries SET state='ACKED',acknowledgment_sha256=? "
            "WHERE event_id=? AND body_sha256=? AND state='RESERVED'",
            (ack_hash,event_id,digest)).rowcount
        _check(changed == 1, "ACKNOWLEDGMENT_STATE_MISMATCH")
    def mark_uncertain(self, event_id: str, digest: str):
        changed=self.db.execute(
            "UPDATE deliveries SET state='UNCERTAIN' "
            "WHERE event_id=? AND body_sha256=? AND state='RESERVED'",
            (event_id,digest)).rowcount
        _check(changed == 1, "UNCERTAIN_STATE_MISMATCH")
    def state(self, event_id: str):
        return self.db.execute("SELECT state,body_sha256,acknowledgment_sha256 "
                               "FROM deliveries WHERE event_id=?", (event_id,)).fetchone()
    def close(self):
        self.db.close()
