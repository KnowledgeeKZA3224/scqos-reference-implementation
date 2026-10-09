"""GEKYUME x SCQOS -> The Forge telemetry contract adapter, synthetic-safe v1.
Never initiates a payment; proof keys must originate from independently verified
trust boundaries, NEVER from the user request carrying the telemetry claim.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import hmac
import ipaddress
import json
import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any

TENANT_ID = "FORGE-WA-001"
SCHEMA_ID = "SPEC-WA-TELEMETRY-V1"
ENGINES = ("GEKYUME", "SCQOS", "EXECUTION")
DECISIONS = {"GEKYUME": "PERMIT", "SCQOS": "PERMIT", "EXECUTION": "COMMITTED"}
HEX64 = re.compile(r"^[a-f0-9]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
EVENT_WINDOW_SECONDS = 300

class ContractError(ValueError):
    """Fail closed; never silently coerce authority, amounts or proofs."""

def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")

def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def mac(key: bytes, message: bytes) -> str:
    if not isinstance(key, bytes) or len(key) < 32:
        raise ContractError("KEY_NOT_APPROVED")
    return hmac.new(key, message, hashlib.sha256).hexdigest()

def _check(condition: bool, code: str) -> None:
    if not condition:
        raise ContractError(code)

def _text(value: Any, code: str, *, maxlen: int = 128) -> str:
    _check(isinstance(value, str) and 0 < len(value) <= maxlen, code)
    return value

def _datetime(value: str) -> dt.datetime:
    try:
        t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        _check(t.tzinfo is not None, "TIMEZONE_REQUIRED")
        return t.astimezone(dt.timezone.utc)
    except (ValueError, TypeError) as exc:
        raise ContractError("INVALID_TIMESTAMP") from exc

def _amount(value: Any) -> Decimal:
    _check(not isinstance(value, bool) and isinstance(value, (float, int, Decimal)), "INVALID_AMOUNT")
    try:
        v = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ContractError("INVALID_AMOUNT") from exc
    _check(v.is_finite() and v > 0 and v <= Decimal("1000000000000"), "AMOUNT_OUT_OF_BOUNDS")
    _check(v == v.quantize(Decimal("0.01")), "INVALID_CURRENCY_PRECISION")
    return v

def validate_payload(payload: dict, *, now: dt.datetime | None = None,
                     enforce_freshness: bool = True) -> str:
    _check(isinstance(payload, dict), "PAYLOAD_NOT_OBJECT")
    required = {"telemetry_id", "timestamp", "gekyume_validation", "scqos_evaluation", "transaction_data"}
    _check(set(payload) == required, "SCHEMA_TOP_LEVEL_MISMATCH")
    event_id = _text(payload["telemetry_id"], "INVALID_TELEMETRY_ID")
    _check(bool(SAFE_ID.fullmatch(event_id)), "INVALID_TELEMETRY_ID")
    timestamp = _datetime(_text(payload["timestamp"], "INVALID_TIMESTAMP"))
    if enforce_freshness:
        clock = now or dt.datetime.now(dt.timezone.utc)
        _check(clock.tzinfo is not None, "CLOCK_NOT_UTC")
        _check(abs((clock - timestamp).total_seconds()) <= EVENT_WINDOW_SECONDS, "STALE_OR_FUTURE_EVENT")
    g, s, t = payload["gekyume_validation"], payload["scqos_evaluation"], payload["transaction_data"]
    _check(isinstance(g, dict) and set(g) == {"status", "policy_check_passed", "rule_engine_id"}, "GEKYUME_SCHEMA")
    _check(g["status"] == "PASSED" and g["policy_check_passed"] is True, "GEKYUME_NOT_PERMITTED")
    _text(g["rule_engine_id"], "MISSING_RULE_ENGINE_ID")
    _check(isinstance(s, dict) and set(s) == {"authority_state", "admissibility_score", "consequence_vector"}, "SCQOS_SCHEMA")
    _check(s["authority_state"] == "AUTHORIZED", "SCQOS_NOT_AUTHORIZED")
    score = s["admissibility_score"]
    _check(not isinstance(score, bool) and type(score) in (int, float) and
           math.isfinite(score) and 0 <= score <= 1, "INVALID_SCORE")
    _text(s["consequence_vector"], "MISSING_CONSEQUENCE_VECTOR", maxlen=512)
    keys = {"arn", "amount", "currency", "device_fingerprint", "ip_address", "customer_account_id"}
    _check(isinstance(t, dict) and set(t) == keys, "TRANSACTION_SCHEMA")
    _text(t["arn"], "INVALID_ARN")
    _amount(t["amount"])
    curr = _text(t["currency"], "INVALID_CURRENCY")
    _check(bool(re.fullmatch("[A-Z]{3}", curr)), "INVALID_CURRENCY")
    _text(t["device_fingerprint"], "INVALID_FINGERPRINT")
    _text(t["customer_account_id"], "INVALID_ACCOUNT_ID")
    try:
        ipaddress.ip_address(t["ip_address"])
    except (ValueError, TypeError) as exc:
        raise ContractError("INVALID_IP_ADDRESS") from exc
    return sha256(canonical(t))

def _proof_message(engine: str, transaction_hash: str, decision: str,
                   issued_at: str, expires_at: str) -> dict:
    return {"engine": engine, "transaction_sha256": transaction_hash,
            "decision": decision, "issued_at": issued_at,
            "expires_at": expires_at, "contract": SCHEMA_ID}

def issue_test_receipt(engine: str, transaction_hash: str, issued_at: str,
                       expires_at: str, key: bytes) -> dict:
    """TEST-ONLY helper. Never use it to generate production payment authority."""
    _check(engine in ENGINES and bool(HEX64.fullmatch(transaction_hash)), "INVALID_PROOF_ENGINE_OR_HASH")
    message = _proof_message(engine, transaction_hash, DECISIONS[engine], issued_at, expires_at)
    return {**message, "signature": mac(key, canonical(message))}

def verify_receipts(payload: dict, receipts: dict, keys: dict[str, bytes],
                    *, now: dt.datetime | None = None) -> None:
    clock = now or dt.datetime.now(dt.timezone.utc)
    tx_hash = validate_payload(payload, now=clock)
    _check(isinstance(receipts, dict) and set(receipts) == set(ENGINES), "RECEIPT_SET_INCOMPLETE")
    _check(isinstance(keys, dict) and set(keys) == set(ENGINES), "TRUST_ROOT_SET_INCOMPLETE")
    for engine in ENGINES:
        r = receipts[engine]
        _check(isinstance(r, dict) and set(r) == {"engine", "transaction_sha256",
                  "decision", "issued_at", "expires_at", "contract", "signature"}, "MALFORMED_RECEIPT")
        _check(r["engine"] == engine and r["decision"] == DECISIONS[engine] and
               r["contract"] == SCHEMA_ID, "WRONG_AUTHORITY_OR_RESULT")
        _check(r["transaction_sha256"] == tx_hash, "TRANSACTION_BINDING_MISMATCH")
        start, expiry = _datetime(r["issued_at"]), _datetime(r["expires_at"])
        _check(start <= clock <= expiry and
               0 <= (expiry - start).total_seconds() <= EVENT_WINDOW_SECONDS, "PROOF_EXPIRED")
        signature = r["signature"]
        _check(isinstance(signature, str) and bool(HEX64.fullmatch(signature)), "BAD_PROOF_SIGNATURE")
        unsigned = {k: v for k, v in r.items() if k != "signature"}
        expected = mac(keys[engine], canonical(unsigned))
        _check(hmac.compare_digest(signature, expected), "PROOF_NOT_AUTHENTIC")
    g_start = _datetime(receipts["GEKYUME"]["issued_at"])
    s_start = _datetime(receipts["SCQOS"]["issued_at"])
    commit = _datetime(receipts["EXECUTION"]["issued_at"])
    _check(commit >= max(g_start, s_start), "EXECUTION_PRECEDES_AUTHORITY")

def make_forge_request(payload: dict, receipts: dict, proof_keys: dict[str, bytes],
                       forge_key: bytes, *, now: dt.datetime | None = None) -> tuple[bytes, dict]:
    """Return exact POST bytes and headers. No networking or financial execution."""
    verify_receipts(payload, receipts, proof_keys, now=now)
    body = canonical(payload)
    return body, {"Content-Type": "application/json",
                  "X-Forge-Tenant-ID": TENANT_ID,
                  "X-Signature-HMAC-256": mac(forge_key, body)}

def verify_forge_request(raw: bytes, headers: dict, forge_key: bytes,
                         *, now: dt.datetime | None = None) -> dict:
    _check(headers.get("X-Forge-Tenant-ID") == TENANT_ID, "TENANT_MISMATCH")
    _check(headers.get("Content-Type") == "application/json", "CONTENT_TYPE_MISMATCH")
    supplied = headers.get("X-Signature-HMAC-256")
    _check(isinstance(supplied, str) and bool(HEX64.fullmatch(supplied)), "SIGNATURE_FORMAT")
    _check(hmac.compare_digest(supplied, mac(forge_key, raw)), "FORGE_HMAC_MISMATCH")
    try:
        payload = json.loads(raw, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (ValueError, UnicodeError) as exc:
        raise ContractError("MALFORMED_JSON") from exc
    validate_payload(payload, now=now)
    return payload

def make_synthetic_payload(now: dt.datetime | None = None) -> dict:
    """Demonstration fixture only; not a bank transaction or execution receipt."""
    t = now or dt.datetime.now(dt.timezone.utc)
    _check(t.tzinfo is not None, "CLOCK_NOT_UTC")
    tstamp = t.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {"telemetry_id": "tel_synthetic_" + t.strftime("%Y%m%dT%H%M%S"),
            "timestamp": tstamp,
            "gekyume_validation": {"status": "PASSED", "policy_check_passed": True,
                                  "rule_engine_id": "gekyume_v3_core"},
            "scqos_evaluation": {"authority_state": "AUTHORIZED",
                                 "admissibility_score": 0.98,
                                 "consequence_vector": "EVAL_PASS_X91"},
            "transaction_data": {"arn": "74532112345678901234567",
                                  "amount": 1250.0, "currency": "GBP",
                                  "device_fingerprint": "df_synthetic_a3f9",
                                  "ip_address": "192.168.1.1",
                                  "customer_account_id": "usr_cloud_synthetic"}}
