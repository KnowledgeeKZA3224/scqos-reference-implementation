import hashlib
import json
import os
import re
import time
import uuid
from decimal import Decimal, InvalidOperation

import boto3

SYSTEM = "GEKYUME"
VERSION = "1.0.0-universal"
TABLE_NAME = os.environ.get("RECEIPT_TABLE", "gekyume-universal-receipts-v1")
table = boto3.resource("dynamodb").Table(TABLE_NAME)

RAIL_ALIASES = {
    "BANK": "BANK_TRANSFER", "BANK_TRANSFER": "BANK_TRANSFER",
    "ACH": "ACH", "FEDNOW": "FEDNOW", "RTP": "RTP",
    "WIRE": "WIRE", "FEDWIRE": "WIRE", "SWIFT": "SWIFT",
    "ISO20022": "ISO20022", "ISO_20022": "ISO20022",
    "CARD": "CARD", "CREDIT_CARD": "CARD", "DEBIT_CARD": "CARD",
    "BLOCKCHAIN": "BLOCKCHAIN", "CRYPTO": "BLOCKCHAIN",
    "ETH": "ETHEREUM", "ETHEREUM": "ETHEREUM", "EVM": "ETHEREUM",
    "BTC": "BITCOIN", "BITCOIN": "BITCOIN",
    "XRPL": "XRPL", "XRP": "XRPL",
    "SOL": "SOLANA", "SOLANA": "SOLANA",
    "STABLECOIN": "STABLECOIN", "WALLET": "WALLET",
    "WALLET_TO_WALLET": "WALLET", "AI_AGENT": "AI_AGENT",
    "AGENT": "AI_AGENT", "GENERIC": "GENERIC",
}
BLOCKCHAIN_RAILS = {"BLOCKCHAIN", "ETHEREUM", "BITCOIN", "XRPL", "SOLANA", "STABLECOIN", "WALLET"}
KNOWN_RAILS = sorted(set(RAIL_ALIASES.values()))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def decimal_value(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def clean(value):
    return None if value is None else str(value).strip()


def first(mapping, *names):
    for name in names:
        if name in mapping and mapping[name] not in (None, ""):
            return mapping[name]
    return None


def rail_name(value):
    key = (clean(value) or "GENERIC").upper().replace("-", "_").replace(" ", "_")
    return RAIL_ALIASES.get(key, "GENERIC")


def normalize(payload):
    raw = payload.get("transaction") if isinstance(payload.get("transaction"), dict) else payload
    binding_raw = payload.get("binding") if isinstance(payload.get("binding"), dict) else raw.get("binding", {})
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), dict) else raw.get("evidence", {})
    policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else raw.get("policy", {})
    now = time.time()

    rail = rail_name(first(raw, "rail", "payment_rail", "domain", "network_type"))
    network = clean(first(raw, "network", "blockchain", "scheme"))
    chain_id = clean(first(raw, "chain_id", "chainId"))
    asset = (clean(first(raw, "asset", "currency", "token", "symbol")) or "USD").upper()
    source = clean(first(raw, "source", "source_account", "sender_account", "from", "from_address"))
    destination = clean(first(raw, "destination", "destination_account", "recipient_account", "to", "to_address", "wallet_address"))
    sender_id = clean(first(raw, "sender_id", "payer_id", "actor_id", "originator_id")) or source
    recipient_id = clean(first(raw, "recipient_id", "payee_id", "beneficiary_id", "merchant_id"))
    amount = decimal_value(first(raw, "amount", "value"))

    if rail == "GENERIC" and network:
        upper = network.upper()
        for candidate in ("ETHEREUM", "BITCOIN", "XRPL", "SOLANA"):
            if candidate in upper:
                rail = candidate
                break

    tx = {
        "transaction_id": clean(first(raw, "transaction_id", "transition_id", "intent_id")) or str(uuid.uuid4()),
        "rail": rail,
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "source": source,
        "destination": destination,
        "amount": format(amount, "f") if amount is not None else None,
        "asset": asset,
        "network": network,
        "chain_id": chain_id,
        "token_contract": clean(first(raw, "token_contract", "contract_address", "issuer")),
        "purpose": clean(first(raw, "purpose", "memo", "description")),
        "authorized_by": clean(first(raw, "authorized_by", "approver_id", "approval_id")),
        "authority_status": (clean(first(raw, "authority_status", "authorization_status")) or "ACTIVE").upper(),
        "created_at": float(first(raw, "created_at", "timestamp") or now),
        "expires_at": float(first(raw, "expires_at", "expiry") or (now + 300)),
    }

    binding = {
        "recipient_id": clean(first(binding_raw, "recipient_id", "payee_id", "beneficiary_id")),
        "destination": clean(first(binding_raw, "destination", "destination_account", "wallet_address", "to_address")),
        "network": clean(first(binding_raw, "network", "blockchain")),
        "chain_id": clean(first(binding_raw, "chain_id", "chainId")),
        "asset": (clean(first(binding_raw, "asset", "currency", "token", "symbol")) or asset).upper(),
        "token_contract": clean(first(binding_raw, "token_contract", "contract_address", "issuer")),
    }

    # Safe normalization may copy already-declared meaning, but never invents authority or destination.
    if not binding["recipient_id"] and recipient_id:
        binding["recipient_id"] = recipient_id
    if not binding["network"] and network:
        binding["network"] = network
    if not binding["chain_id"] and chain_id:
        binding["chain_id"] = chain_id
    if not binding["token_contract"] and tx["token_contract"]:
        binding["token_contract"] = tx["token_contract"]

    return tx, binding, evidence, policy


def valid_destination(rail, destination):
    if not destination:
        return False
    if rail == "ETHEREUM":
        return bool(re.fullmatch(r"0x[0-9a-fA-F]{40}", destination))
    if rail == "BITCOIN":
        return bool(re.fullmatch(r"(bc1[a-zA-HJ-NP-Z0-9]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})", destination))
    if rail == "XRPL":
        return bool(re.fullmatch(r"r[1-9A-HJ-NP-Za-km-z]{24,34}", destination))
    if rail == "SOLANA":
        return bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", destination))
    return True


def store(receipt):
    table.put_item(Item={
        "domain_id": receipt["domain_id"],
        "receipt_id": receipt["receipt_id"],
        "receipt_hash": receipt["receipt_hash"],
        "decision": receipt.get("decision", ""),
        "kind": receipt.get("kind", "PRE_EXECUTION"),
        "timestamp": Decimal(str(receipt["timestamp"])),
        "payload": canonical(receipt),
    })


def evaluate(payload):
    tx, binding, evidence, policy = normalize(payload)
    now = time.time()
    checks, reasons = {}, []

    def check(name, ok, reason):
        checks[name] = bool(ok)
        if not ok:
            reasons.append(reason)

    amount = decimal_value(tx["amount"])
    check("time", tx["created_at"] <= now + 5 and tx["expires_at"] > now, "TIME_INVALID_OR_EXPIRED")
    check("identity", bool(tx["sender_id"]), "SENDER_IDENTITY_MISSING")
    check("authority", bool(tx["authorized_by"]) and tx["authority_status"] == "ACTIVE", "AUTHORITY_NOT_PROVEN")
    check("amount", amount is not None and amount > 0, "AMOUNT_INVALID")
    check("source", bool(tx["source"]), "SOURCE_MISSING")
    check("destination", bool(tx["destination"]), "DESTINATION_MISSING")
    check("distinct_endpoint", bool(tx["source"]) and bool(tx["destination"]) and tx["source"] != tx["destination"], "SOURCE_EQUALS_DESTINATION")

    # Recipient binding: the actual execution endpoint must exactly equal the endpoint authorized beforehand.
    check("recipient_binding_present", bool(binding["destination"]), "AUTHORIZED_DESTINATION_MISSING")
    check("recipient_destination_match", bool(binding["destination"]) and tx["destination"] == binding["destination"], "DESTINATION_BINDING_MISMATCH")
    if binding["recipient_id"]:
        check("recipient_identity_match", bool(tx["recipient_id"]) and tx["recipient_id"] == binding["recipient_id"], "RECIPIENT_IDENTITY_MISMATCH")
    else:
        checks["recipient_identity_match"] = True
    check("asset_binding", tx["asset"] == binding["asset"], "ASSET_BINDING_MISMATCH")

    if tx["rail"] in BLOCKCHAIN_RAILS:
        check("blockchain_destination_format", valid_destination(tx["rail"], tx["destination"]), "BLOCKCHAIN_DESTINATION_INVALID")
        check("network_present", bool(tx["network"]), "BLOCKCHAIN_NETWORK_MISSING")
        if binding["network"]:
            check("network_binding", tx["network"] == binding["network"], "NETWORK_BINDING_MISMATCH")
        if binding["chain_id"]:
            check("chain_binding", tx["chain_id"] == binding["chain_id"], "CHAIN_BINDING_MISMATCH")
        if binding["token_contract"]:
            check("token_binding", tx["token_contract"] == binding["token_contract"], "TOKEN_BINDING_MISMATCH")

    max_amount = decimal_value(policy.get("max_amount")) if policy.get("max_amount") is not None else None
    if max_amount is not None and amount is not None:
        check("amount_boundary", amount <= max_amount, "AMOUNT_LIMIT_EXCEEDED")

    allowed_rails = {rail_name(v) for v in policy.get("allowed_rails", [])}
    if allowed_rails:
        check("rail_boundary", tx["rail"] in allowed_rails, "RAIL_NOT_ALLOWED")
    allowed_assets = {str(v).upper() for v in policy.get("allowed_assets", [])}
    if allowed_assets:
        check("asset_boundary", tx["asset"] in allowed_assets, "ASSET_NOT_ALLOWED")
    for field in policy.get("required_evidence", []):
        check("evidence_" + str(field), evidence.get(field) is True, "EVIDENCE_MISSING:" + str(field))
    if payload.get("consumed_transaction_ids"):
        check("replay", tx["transaction_id"] not in set(payload["consumed_transaction_ids"]), "REPLAY_DETECTED")

    reject_codes = {
        "DESTINATION_BINDING_MISMATCH", "RECIPIENT_IDENTITY_MISMATCH", "ASSET_BINDING_MISMATCH",
        "NETWORK_BINDING_MISMATCH", "CHAIN_BINDING_MISMATCH", "TOKEN_BINDING_MISMATCH",
        "AMOUNT_LIMIT_EXCEEDED", "RAIL_NOT_ALLOWED", "ASSET_NOT_ALLOWED", "SOURCE_EQUALS_DESTINATION",
        "REPLAY_DETECTED", "BLOCKCHAIN_DESTINATION_INVALID",
    }
    if any(reason in reject_codes for reason in reasons):
        decision = "REJECT"
    elif reasons:
        decision = "HOLD"
    else:
        decision = "PERMIT"

    receipt = {
        "system": SYSTEM,
        "version": VERSION,
        "kind": "PRE_EXECUTION",
        "receipt_id": str(uuid.uuid4()),
        "domain_id": tx["rail"],
        "timestamp": now,
        "decision": decision,
        "reasons": reasons or ["ALL_REQUIRED_PROOFS_ALIGNED"],
        "checks": checks,
        "normalized": {"transaction": tx, "binding": binding},
        "transaction_hash": digest(tx),
        "binding_hash": digest(binding),
        "consequence": {
            "funds_moved": False,
            "authorized_to_enter_rail": decision == "PERMIT",
            "execution_boundary": "PRE_EXECUTION_ONLY",
        },
    }
    receipt["receipt_hash"] = digest(receipt)
    store(receipt)
    return receipt


def get_receipt(domain_id, receipt_id):
    item = table.get_item(Key={"domain_id": domain_id, "receipt_id": receipt_id}, ConsistentRead=True).get("Item")
    return json.loads(item["payload"]) if item else None


def reconcile(payload):
    domain_id = rail_name(payload.get("domain_id") or payload.get("rail"))
    receipt_id = clean(payload.get("receipt_id"))
    if not receipt_id:
        return {"error": "receipt_id is required"}, 400
    prior = get_receipt(domain_id, receipt_id)
    if not prior:
        return {"error": "authorization receipt not found"}, 404
    if prior.get("decision") != "PERMIT":
        return {"error": "only a PERMIT receipt can be reconciled"}, 409

    expected = prior["normalized"]["transaction"]
    settlement = payload.get("settlement") if isinstance(payload.get("settlement"), dict) else {}
    settled_amount = decimal_value(first(settlement, "amount", "value"))
    actual = {
        "destination": clean(first(settlement, "destination", "to", "to_address", "wallet_address")),
        "amount": format(settled_amount, "f") if settled_amount is not None else None,
        "asset": (clean(first(settlement, "asset", "currency", "token", "symbol")) or "").upper(),
        "network": clean(first(settlement, "network", "blockchain")),
        "chain_id": clean(first(settlement, "chain_id", "chainId")),
    }
    checks = {
        "destination": actual["destination"] == expected["destination"],
        "amount": actual["amount"] == expected["amount"],
        "asset": actual["asset"] == expected["asset"],
    }
    if expected.get("network"):
        checks["network"] = actual["network"] == expected["network"]
    if expected.get("chain_id"):
        checks["chain_id"] = actual["chain_id"] == expected["chain_id"]

    result = "SETTLED_AS_AUTHORIZED" if all(checks.values()) else "SETTLEMENT_MISMATCH"
    receipt = {
        "system": SYSTEM,
        "version": VERSION,
        "kind": "POST_SETTLEMENT",
        "receipt_id": str(uuid.uuid4()),
        "domain_id": domain_id,
        "timestamp": time.time(),
        "decision": result,
        "authorization_receipt_id": receipt_id,
        "authorization_receipt_hash": prior["receipt_hash"],
        "checks": checks,
        "expected": {k: expected.get(k) for k in ("destination", "amount", "asset", "network", "chain_id")},
        "settlement": settlement,
        "settlement_reference": clean(first(settlement, "transaction_hash", "tx_hash", "reference", "trace_id")),
    }
    receipt["receipt_hash"] = digest(receipt)
    store(receipt)
    return receipt, 200


def response(status, body):
    return {"statusCode": status, "headers": {"content-type": "application/json"}, "body": json.dumps(body, separators=(",", ":"), default=str)}


def handler(event, context):
    try:
        event = event if isinstance(event, dict) else {}
        rc = event.get("requestContext") if isinstance(event.get("requestContext"), dict) else {}
        http = rc.get("http") if isinstance(rc.get("http"), dict) else {}
        path = http.get("path") or event.get("rawPath") or ""
        method = (http.get("method") or "").upper()
        body = event.get("body")
        if isinstance(body, str):
            try:
                payload = json.loads(body)
            except Exception:
                return response(400, {"error": "body must be valid JSON"})
        elif isinstance(body, dict):
            payload = body
        else:
            payload = event if not rc else {}

        action = (clean(payload.get("action")) or "").lower()
        if (method == "GET" and path.endswith("/health")) or action == "health":
            return response(200, {
                "system": SYSTEM, "version": VERSION, "status": "READY",
                "mode": "PAYMENT_AGNOSTIC_PRE_EXECUTION_GOVERNOR",
                "supported_rails": KNOWN_RAILS,
                "blockchain_recipient_binding": True,
                "post_settlement_reconciliation": True,
                "moves_funds": False,
            })
        if path.endswith("/reconcile") or action == "reconcile":
            result, status = reconcile(payload)
            return response(status, result)
        return response(200, evaluate(payload))
    except Exception as error:
        return response(503, {
            "system": SYSTEM, "version": VERSION, "decision": "HOLD",
            "reasons": ["GOVERNOR_INTERNAL_FAILURE"], "error_type": type(error).__name__,
            "timestamp": time.time(),
            "consequence": {"funds_moved": False, "authorized_to_enter_rail": False},
        })
