"""Synthetic-only proposed V3 Forge evidence contract.

NOT a deployed receiver, bank event, authority grant or independent witness.
No networking. Stable transaction identity is separate from per-attempt nonce.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import re
import sqlite3
import uuid
from pathlib import Path

from .adapter import ContractError, canonical, sha256
from .staging_contract import _fresh, _parse_pairs

CONTRACT = "SC-FORGE-STAGING-SYNTHETIC-V3-PROPOSAL"
MAX_BODY = 65536
HEX = re.compile(r"^[0-9a-f]{64}$")
DECISIONS = {"PERMIT", "HOLD", "REJECT"}

def _uuid(value, name):
    try:
        if not isinstance(value, str) or str(uuid.UUID(value)) != value:
            raise ValueError("noncanonical")
    except (TypeError, AttributeError, ValueError) as e:
        raise ContractError("INVALID_" + name) from e
    return value

def _digest(value, name):
    if not isinstance(value, str) or HEX.fullmatch(value) is None:
        raise ContractError("INVALID_" + name)
    return value

def validate_envelope(obj: dict, *, now: dt.datetime | None = None) -> dict:
    fields = {
        "contract", "mode", "transaction_id", "logical_action_sha256",
        "scenario_id", "transition_id", "attempt_nonce", "timestamp",
        "decision", "gekyume_precheck_sha256", "scqos_decision_sha256",
        "observed_effect", "execution_receipt_sha256", "observer_receipt_sha256",
    }
    if not isinstance(obj, dict) or set(obj) != fields:
        raise ContractError("SCHEMA_MISMATCH")
    if obj["contract"] != CONTRACT or obj["mode"] != "SYNTHETIC_ONLY":
        raise ContractError("WRONG_EXECUTION_BOUNDARY")
    for k in ("transaction_id", "scenario_id", "transition_id", "attempt_nonce"):
        _uuid(obj[k], k.upper())
    for k in ("logical_action_sha256", "gekyume_precheck_sha256",
              "scqos_decision_sha256", "observer_receipt_sha256"):
        _digest(obj[k], k.upper())
    if obj["transaction_id"] == obj["attempt_nonce"]:
        raise ContractError("TRANSACTION_NONCE_NOT_SEPARATE")
    if not isinstance(obj["decision"], str) or obj["decision"] not in DECISIONS:
        raise ContractError("INVALID_DECISION")
    _fresh(obj["timestamp"], now=now)
    if obj["decision"] == "PERMIT":
        # This is a *claimed synthetic observation*, NOT a verified execution.
        if obj["observed_effect"] != "ISOLATED_SYNTHETIC_EFFECT":
            raise ContractError("PERMIT_EFFECT_MISMATCH")
        _digest(obj["execution_receipt_sha256"], "EXECUTION_RECEIPT_SHA256")
    else:
        if obj["observed_effect"] != "NO_PROTECTED_EFFECT":
            raise ContractError("DENIAL_EFFECT_MISMATCH")
        if obj["execution_receipt_sha256"] is not None:
            raise ContractError("FABRICATED_DENIED_EXECUTION_RECEIPT")
    return obj

def sign_envelope(obj: dict, app_id: str, key: bytes, *,
                  now: dt.datetime | None = None) -> tuple[bytes, dict]:
    validate_envelope(obj, now=now)
    if not isinstance(app_id, str) or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", app_id) is None:
        raise ContractError("INVALID_APP_ID")
    if not isinstance(key, bytes) or len(key) < 32:
        raise ContractError("KEY_NOT_APPROVED")
    raw = canonical(obj)
    return raw, {
        "Content-Type": "application/json",
        "X-Forge-App-ID": app_id,
        "X-Forge-Nonce": obj["attempt_nonce"],
        "X-Forge-Signature": "hmac-sha256=" + hmac.new(key, raw, hashlib.sha256).hexdigest(),
    }

def verify_signed_envelope(raw: bytes, headers: dict, app_id: str, key: bytes,
                           *, now: dt.datetime | None = None) -> dict:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BODY:
        raise ContractError("INVALID_BODY_SIZE")
    if not isinstance(headers, dict) or headers.get("Content-Type") != "application/json":
        raise ContractError("CONTENT_TYPE_MISMATCH")
    if headers.get("X-Forge-App-ID") != app_id:
        raise ContractError("APP_ID_MISMATCH")
    if not isinstance(key, bytes) or len(key) < 32:
        raise ContractError("KEY_NOT_APPROVED")
    signed = headers.get("X-Forge-Signature")
    if not isinstance(signed, str) or re.fullmatch(r"hmac-sha256=[a-f0-9]{64}", signed) is None:
        raise ContractError("SIGNATURE_FORMAT")
    expected = "hmac-sha256=" + hmac.new(key, raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signed, expected):
        raise ContractError("INVALID_SIGNATURE")
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_parse_pairs,
                         parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
    except ContractError:
        raise
    except (ValueError, UnicodeError) as e:
        raise ContractError("MALFORMED_JSON") from e
    if canonical(obj) != raw:
        raise ContractError("NONCANONICAL_BYTES")
    validate_envelope(obj, now=now)
    if headers.get("X-Forge-Nonce") != obj["attempt_nonce"]:
        raise ContractError("NONCE_HEADER_BODY_MISMATCH")
    return obj

class SyntheticV3Store:
    """Atomic indexed *metadata* store, not an independently witnessed ledger.

    SQLite test reference. No production or external business side effects.
    """
    def __init__(self, filename: str | Path):
        self.db = sqlite3.connect(str(filename), isolation_level=None, timeout=5)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS evidence (
            transaction_id TEXT PRIMARY KEY,
            attempt_nonce TEXT UNIQUE NOT NULL,
            logical_action_sha256 TEXT NOT NULL,
            decision TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            received_at TEXT NOT NULL
        )""")

    def accept(self, raw: bytes, headers: dict, app_id: str, key: bytes,
               *, now: dt.datetime | None = None) -> dict:
        obj = verify_signed_envelope(raw, headers, app_id, key, now=now)
        received = (now or dt.datetime.now(dt.timezone.utc)).isoformat()
        digest = sha256(raw)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            # Distinguish nonce replay from a new delivery attempt of same logical tx.
            if self.db.execute("SELECT 1 FROM evidence WHERE attempt_nonce=?",
                               (obj["attempt_nonce"],)).fetchone():
                raise ContractError("REPLAY_NONCE_401")
            if self.db.execute("SELECT 1 FROM evidence WHERE transaction_id=?",
                               (obj["transaction_id"],)).fetchone():
                raise ContractError("DUPLICATE_TRANSACTION_409")
            self.db.execute("INSERT INTO evidence VALUES (?,?,?,?,?,?)",
                (obj["transaction_id"], obj["attempt_nonce"],
                 obj["logical_action_sha256"], obj["decision"], digest, received))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return self.readback(obj["transaction_id"])

    def readback(self, txid: str) -> dict | None:
        row = self.db.execute(
            "SELECT attempt_nonce, logical_action_sha256, decision, payload_sha256, received_at "
            "FROM evidence WHERE transaction_id=?", (txid,)
        ).fetchone()
        if not row:
            return None
        return {
            "transaction_id": txid,
            "attempt_nonce": row[0],
            "logical_action_sha256": row[1],
            "decision": row[2],
            "canonical_digest": "sha256:" + row[3],
            "timestamp": row[4],
            "status": "VALIDATED_ONLY" if row[2] == "PERMIT" else "VALIDATED_DENIAL",
            "settlement": False,
            "independent_witness_verified": False,
        }

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]

    def close(self):
        self.db.close()
