"""Synthetic-only Forge staging reference. No network, ERP, payment or settlement writes.

IMPORTANT: This is a proposed V2 handshake, NOT confirmation of Oscar's active
Node contract. Callers must separately agree on schema, app id, and receipt API.
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
from urllib.parse import urlparse

from .adapter import ContractError, canonical, verify_receipts, sha256

CONTRACT = "SC-FORGE-STAGING-SYNTHETIC-V2"
ORIGIN = "https://staging-api.theforge.io/v1/evidence/ingest"
MAX_BODY = 65536
WINDOW_SECONDS = 300


def require_verified_https(url: str) -> None:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != "staging-api.theforge.io" or p.port not in (None, 443) or p.username or p.password or p.query or p.fragment or p.path != "/v1/evidence/ingest":
        raise ContractError("UNTRUSTED_ENDPOINT")
    # A network client MUST also enforce normal CA/hostname validation.
    # Self-signed certificates require an explicitly trusted CA, never -k.


def _uuid(text: str) -> str:
    try:
        parsed = uuid.UUID(text)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ContractError("INVALID_NONCE") from exc
    if str(parsed) != text:
        raise ContractError("NONCANONICAL_NONCE")
    return text


def _parse_pairs(pairs):
    record = {}
    for key, value in pairs:
        if key in record:
            raise ContractError("DUPLICATE_JSON_KEY")
        record[key] = value
    return record


def _parse_raw(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BODY:
        raise ContractError("INVALID_BODY_SIZE")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_parse_pairs,
                             parse_constant=lambda val: (_ for _ in ()).throw(ValueError(val)))
    except ContractError:
        raise
    except (ValueError, UnicodeError) as exc:
        raise ContractError("MALFORMED_JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "contract", "mode", "nonce", "transaction_id", "timestamp",
        "source_payload_sha256", "execution", "verified_receipt_set_sha256"
    }:
        raise ContractError("SCHEMA_MISMATCH")
    if canonical(payload) != raw:
        raise ContractError("NONCANONICAL_BYTES")
    if payload["contract"] != CONTRACT or payload["mode"] != "SYNTHETIC_ONLY" or payload["execution"] != "SIMULATED_NO_EXTERNAL_WRITES":
        raise ContractError("WRONG_EXECUTION_BOUNDARY")
    _uuid(payload["nonce"])
    if payload["transaction_id"] != payload["nonce"]:
        raise ContractError("NONCE_TRANSACTION_MISMATCH")
    for field in ("source_payload_sha256", "verified_receipt_set_sha256"):
        if not isinstance(payload[field], str) or not re.fullmatch(r"[0-9a-f]{64}", payload[field]):
            raise ContractError("INVALID_DIGEST")
    return payload


def _fresh(timestamp: str, now: dt.datetime | None = None) -> None:
    try:
        t = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if t.tzinfo is None:
            raise ValueError("tz")
    except (ValueError, AttributeError, TypeError) as exc:
        raise ContractError("INVALID_TIMESTAMP") from exc
    current = now or dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None or abs((current-t).total_seconds()) > WINDOW_SECONDS:
        raise ContractError("STALE_OR_FUTURE_EVENT")


def build_request(payload: dict, receipts: dict, proof_keys: dict,
                  forge_key: bytes, app_id: str, nonce: str,
                  *, now: dt.datetime | None = None) -> tuple[bytes, dict]:
    """Use trusted receipt verification, then create signed synthetic-only bytes."""
    verify_receipts(payload, receipts, proof_keys, now=now)
    _uuid(nonce)
    if not isinstance(app_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", app_id):
        raise ContractError("INVALID_APP_ID")
    if not isinstance(forge_key, bytes) or len(forge_key) < 32:
        raise ContractError("KEY_NOT_APPROVED")
    envelope = {
        "contract": CONTRACT, "mode": "SYNTHETIC_ONLY",
        "nonce": nonce, "transaction_id": nonce,
        "timestamp": payload["timestamp"],
        "source_payload_sha256": sha256(canonical(payload)),
        "verified_receipt_set_sha256": sha256(canonical(receipts)),
        "execution": "SIMULATED_NO_EXTERNAL_WRITES",
    }
    raw = canonical(envelope)
    signature = hmac.new(forge_key, raw, hashlib.sha256).hexdigest()
    return raw, {"Content-Type":"application/json",
                 "X-Forge-App-ID":app_id,
                 "X-Forge-Signature":"hmac-sha256="+signature,
                 "X-Forge-Nonce":nonce}


def verify_request(raw: bytes, headers: dict, forge_key: bytes,
                   app_id: str, *, now: dt.datetime | None = None) -> dict:
    if not isinstance(headers, dict) or headers.get("Content-Type") != "application/json":
        raise ContractError("CONTENT_TYPE_MISMATCH")
    if headers.get("X-Forge-App-ID") != app_id:
        raise ContractError("APP_ID_MISMATCH")
    supplied = headers.get("X-Forge-Signature")
    if not isinstance(supplied, str) or not re.fullmatch(r"hmac-sha256=[0-9a-f]{64}", supplied):
        raise ContractError("SIGNATURE_FORMAT")
    if not isinstance(forge_key, bytes) or len(forge_key) < 32:
        raise ContractError("KEY_NOT_APPROVED")
    if not isinstance(raw, bytes) or len(raw) > MAX_BODY:
        raise ContractError("INVALID_BODY_SIZE")
    expected = "hmac-sha256="+hmac.new(forge_key, raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied):
        raise ContractError("INVALID_SIGNATURE")
    parsed = _parse_raw(raw)
    if headers.get("X-Forge-Nonce") != parsed["nonce"]:
        raise ContractError("NONCE_HEADER_BODY_MISMATCH")
    _fresh(parsed["timestamp"], now=now)
    return parsed


class SyntheticReceiptStore:
    """SQLite O(1) indexed durable readback; NOT an independent witness/ledger."""
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.execute("PRAGMA busy_timeout=3000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS synthetic_ingress (
            nonce TEXT PRIMARY KEY, transaction_id TEXT NOT NULL UNIQUE,
            body_sha256 TEXT NOT NULL, state TEXT NOT NULL,
            received_at TEXT NOT NULL)""")

    def accept(self, raw: bytes, headers: dict, forge_key: bytes, app_id: str,
               *, now: dt.datetime | None = None) -> dict:
        parsed = verify_request(raw, headers, forge_key, app_id, now=now)
        current = now or dt.datetime.now(dt.timezone.utc)
        stamp = current.astimezone(dt.timezone.utc).isoformat()
        receipt = {"status":"VALIDATED_ONLY","transaction_id":parsed["transaction_id"],
                   "nonce":parsed["nonce"], "canonical_digest":"sha256:"+sha256(raw),
                   "timestamp":stamp, "settlement":False}
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("INSERT INTO synthetic_ingress VALUES (?,?,?,?,?)",
                (parsed["nonce"], parsed["transaction_id"], sha256(raw), "VALIDATED_ONLY", stamp))
            self.db.execute("COMMIT")
        except sqlite3.IntegrityError as exc:
            self.db.execute("ROLLBACK")
            raise ContractError("DUPLICATE_REQUEST_409") from exc
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return receipt

    def readback(self, transaction_id: str) -> dict | None:
        row = self.db.execute("SELECT nonce,body_sha256,state,received_at FROM synthetic_ingress WHERE transaction_id=?",(transaction_id,)).fetchone()
        if not row:
            return None
        return {"nonce":row[0], "transaction_id":transaction_id,
                "canonical_digest":"sha256:"+row[1], "status":row[2],
                "timestamp":row[3], "settlement":False}

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM synthetic_ingress").fetchone()[0]

    def close(self):
        self.db.close()
