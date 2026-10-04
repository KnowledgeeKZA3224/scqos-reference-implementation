from __future__ import annotations

import base64
import copy
import hashlib
import hmac
from typing import Any

import rfc8785

DEPLOYMENT_SALT = b"scqos-acs-lab/v0.1.0"
DEPLOYMENT_INFO_PREFIX = b"acs-session:"


def canonical_bytes(value: Any) -> bytes:
    data = rfc8785.dumps(value)
    return data if isinstance(data, bytes) else data.encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def hkdf_sha256(ikm: bytes, session_id: str, length: int = 32) -> bytes:
    """Deployment-defined ACS v0.1 HMAC session-key profile.

    ACS requires an HKDF-derived per-session key but leaves the deployment's
    concrete salt/info profile out of band. The lab freezes it here so both
    sides can reproduce the exact same bytes.
    """
    prk = hmac.new(DEPLOYMENT_SALT, ikm, hashlib.sha256).digest()
    info = DEPLOYMENT_INFO_PREFIX + session_id.encode("utf-8")
    out = b""
    prev = b""
    counter = 1
    while len(out) < length:
        prev = hmac.new(prk, prev + info + bytes([counter]), hashlib.sha256).digest()
        out += prev
        counter += 1
    return out[:length]


def _without_signature(envelope: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(envelope)
    if isinstance(value.get("params"), dict):
        value["params"].pop("signature", None)
    if isinstance(value.get("result"), dict):
        value["result"].pop("signature", None)
    return value


def sign_envelope(envelope: dict[str, Any], ikm: bytes, session_id: str, key_id: str = "lab-hmac-v1") -> dict[str, str]:
    key = hkdf_sha256(ikm, session_id)
    mac = hmac.new(key, canonical_bytes(_without_signature(envelope)), hashlib.sha256).digest()
    return {
        "algorithm": "HMAC-SHA256",
        "value": base64.b64encode(mac).decode("ascii"),
        "key_id": key_id,
    }


def verify_envelope(envelope: dict[str, Any], ikm: bytes, session_id: str) -> bool:
    container = envelope.get("params") if isinstance(envelope.get("params"), dict) else envelope.get("result")
    if not isinstance(container, dict):
        return False
    signature = container.get("signature")
    if not isinstance(signature, dict) or signature.get("algorithm") != "HMAC-SHA256":
        return False
    try:
        supplied = base64.b64decode(signature.get("value", ""), validate=True)
    except Exception:
        return False
    key = hkdf_sha256(ikm, session_id)
    expected = hmac.new(key, canonical_bytes(_without_signature(envelope)), hashlib.sha256).digest()
    return hmac.compare_digest(supplied, expected)


def hash_context_entry(entry_without_hash: dict[str, Any], previous_hash: str | None) -> str:
    content = copy.deepcopy(entry_without_hash)
    content.pop("entry_hash", None)
    content.pop("previous_hash", None)
    prev = bytes.fromhex(previous_hash) if previous_hash else b""
    return hashlib.sha256(canonical_bytes(content) + prev).hexdigest()
