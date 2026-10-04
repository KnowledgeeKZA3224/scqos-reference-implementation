from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .crypto import canonical_bytes, hash_context_entry, sha256_hex, sign_envelope, verify_envelope

ACS_VERSION = "0.1.0"
SUPPORTED_METHODS = {
    "steps/sessionStart",
    "steps/userMessage",
    "steps/agentTrigger",
    "steps/toolCallRequest",
    "steps/toolCallResult",
    "steps/agentResponse",
    "steps/sessionEnd",
    "system/ping",
    "protocols/MCP/tools/call",
}
CONTENT_METHODS = {m for m in SUPPORTED_METHODS if m.startswith("steps/") or m.startswith("protocols/MCP/")}

ERRORS = {
    -32000: "SESSION_REFUSED",
    -32001: "UNSUPPORTED_VERSION",
    -32002: "PROVENANCE_REQUIRED",
    -32003: "CAPABILITY_NOT_NEGOTIATED",
    -32004: "SIGNATURE_INVALID",
    -32005: "REPLAY_DETECTED",
    -32006: "TIMESTAMP_OUT_OF_WINDOW",
    -32007: "CHAIN_MISMATCH",
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> float:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).timestamp()


def _error(rpc_id: Any, code: int, message: str, **data: Any) -> dict[str, Any]:
    payload = {"reason": ERRORS.get(code, "ACS_ERROR"), "message": message}
    payload.update(data)
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": ERRORS.get(code, message), "data": payload}}


@dataclass
class Session:
    session_id: str
    methods: set[str]
    seen_request_ids: set[str] = field(default_factory=set)
    seen_nonces: set[str] = field(default_factory=set)
    chain_hash: str | None = None
    entries: list[dict[str, Any]] = field(default_factory=list)


class SCQOSGuardian:
    """Strict ACS Guardian whose policy decision is delegated to SCQOS ProofGate.

    The ACS adapter owns wire integrity, replay protection and audit-chain rules.
    SCQOS owns transition admissibility. Failure to obtain an SCQOS verdict is
    represented as DEFER with a deny timeout, never silently promoted to ALLOW.
    """

    def __init__(
        self,
        *,
        ikm: bytes | None = None,
        scqos_endpoint: str | None = None,
        skew_window_ms: int = 300_000,
        live_scqos: bool = True,
    ) -> None:
        self.ikm = ikm or os.environ.get("ACS_LAB_PSK", "public-falsification-lab-test-key").encode()
        self.scqos_endpoint = (scqos_endpoint or os.environ.get(
            "SCQOS_ENDPOINT", "https://lcnk9bvtz5.execute-api.us-east-1.amazonaws.com"
        )).rstrip("/")
        self.skew_window_ms = skew_window_ms
        self.live_scqos = live_scqos
        self.sessions: dict[str, Session] = {}

    def process(self, envelope: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(envelope, dict) or envelope.get("jsonrpc") != "2.0":
            return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}
        rpc_id = envelope.get("id")
        method = envelope.get("method")
        params = envelope.get("params")
        if not isinstance(method, str) or not isinstance(params, dict):
            return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32600, "message": "Invalid Request"}}
        metadata = params.get("metadata")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("session_id"), str):
            return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32600, "message": "Invalid Request"}}
        session_id = metadata["session_id"]

        # system/ping is deliberately exempt from ACS-specific failures.
        if method == "system/ping":
            return self._result(envelope, session_id, "allow", payload={"status": "ok", "echo": params.get("payload", {}).get("echo"), "server_timestamp": _iso_now()}, sign=False, chain=False)

        basic = self._check_wire(envelope, session_id)
        if basic is not None:
            return basic

        if method == "handshake/hello":
            return self._handshake(envelope, session_id)

        session = self.sessions.get(session_id)
        if session is None:
            return _error(rpc_id, -32000, "session has not completed handshake")
        if method not in session.methods:
            return _error(rpc_id, -32003, "method was not negotiated", method=method)

        request_id = params.get("request_id")
        nonce = params.get("nonce")
        if request_id in session.seen_request_ids or (nonce and nonce in session.seen_nonces):
            return _error(rpc_id, -32005, "request_id or nonce already observed")
        client_head = metadata.get("session_state", {}).get("chain_hash") if isinstance(metadata.get("session_state"), dict) else None
        if client_head is not None and session.chain_hash is not None and client_head != session.chain_hash:
            return _error(rpc_id, -32007, "client chain head differs from Guardian", expected_chain_hash=session.chain_hash)

        session.seen_request_ids.add(request_id)
        if nonce:
            session.seen_nonces.add(nonce)

        if method in {"steps/toolCallRequest", "protocols/MCP/tools/call"}:
            decision = self._tool_decision(envelope)
        else:
            decision = {"decision": "allow", "reasoning": "non-consequential lifecycle step accepted"}
        return self._decision_response(envelope, session, decision)

    def _check_wire(self, envelope: dict[str, Any], session_id: str) -> dict[str, Any] | None:
        rpc_id = envelope.get("id")
        params = envelope["params"]
        required = ("acs_version", "request_id", "timestamp", "metadata", "payload")
        if any(name not in params for name in required):
            return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32600, "message": "Invalid Request"}}
        try:
            drift_ms = abs(time.time() - _parse_time(str(params["timestamp"]))) * 1000
        except Exception:
            return _error(rpc_id, -32006, "timestamp cannot be parsed", skew_window_ms=self.skew_window_ms)
        if drift_ms > self.skew_window_ms:
            return _error(rpc_id, -32006, "timestamp outside negotiated window", skew_window_ms=self.skew_window_ms)
        if params.get("acs_version") != ACS_VERSION and envelope.get("method") != "handshake/hello":
            return _error(rpc_id, -32001, "request ACS version does not match the negotiated version", supported_versions=[ACS_VERSION])
        if not verify_envelope(envelope, self.ikm, session_id):
            return _error(rpc_id, -32004, "required HMAC-SHA256 signature missing or invalid")
        return None

    def _handshake(self, envelope: dict[str, Any], session_id: str) -> dict[str, Any]:
        rpc_id = envelope["id"]
        params = envelope["params"]
        hello = params.get("payload")
        if not isinstance(hello, dict):
            return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32600, "message": "Invalid Request"}}
        versions = hello.get("acs_versions_supported", [])
        if ACS_VERSION not in versions:
            return _error(rpc_id, -32001, "no common ACS version", supported_versions=[ACS_VERSION])
        if hello.get("provenance_producer") not in {"deterministic", "none"}:
            return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32600, "message": "Invalid Request"}}
        requested = set(hello.get("methods_implemented", []))
        negotiated = requested & SUPPORTED_METHODS
        self.sessions[session_id] = Session(session_id=session_id, methods=negotiated)
        server_hello = {
            "negotiated_version": ACS_VERSION,
            "methods_evaluated": sorted(negotiated),
            "selected_transport": "http",
            "signature_algorithms_supported": ["HMAC-SHA256"],
            "timeout_config": {"default_ms": 5000, "per_method_ms": {"steps/toolCallRequest": 5000}},
            "skew_window_ms": self.skew_window_ms,
            "on_decision_failure": "deny",
            "approver_types_supported": ["human", "service"],
            "policy_requires_provenance": False,
            "profiles_accepted": ["acs-core"],
        }
        # The published ServerHello shape has no signature member. The lab does
        # not invent a hidden wire field; all post-handshake decisions are signed.
        return {"jsonrpc": "2.0", "id": rpc_id, "result": server_hello}

    @staticmethod
    def _arg(payload: dict[str, Any], name: str, default: Any = None) -> Any:
        args = payload.get("arguments", {}) if isinstance(payload, dict) else {}
        item = args.get(name)
        if isinstance(item, dict) and "value" in item:
            return item["value"]
        return default

    def _tool_decision(self, envelope: dict[str, Any]) -> dict[str, Any]:
        params = envelope["params"]
        payload = params.get("payload", {})
        if not isinstance(payload, dict):
            return self._defer("tool payload is unavailable", ["payload"])

        if bool(self._arg(payload, "requires_approval", False)):
            return {
                "decision": "ask",
                "reasoning": "policy requires an independent approver",
                "reason_codes": ["approval_required"],
                "ask_details": {
                    "approver": {"type": "human", "id": "lab-operator"},
                    "question": "Approve this exact consequential transition?",
                    "timeout_seconds": 60,
                    "timeout_disposition": "deny",
                },
            }
        rewrite = self._arg(payload, "safe_rewrite")
        if rewrite is not None:
            return {
                "decision": "modify",
                "reasoning": "policy permits only the bounded replacement value",
                "reason_codes": ["bounded_rewrite"],
                "modifications": {"parameter_overrides": {"target": rewrite}},
            }

        transition = self._acs_to_scqos(envelope)
        if not self.live_scqos:
            verdict = self._local_scqos(transition)
            receipt = {"decision": verdict, "receipt_id": "LOCAL-" + sha256_hex(transition)[:24], "execution_mode": "LOCAL_TEST"}
        else:
            try:
                receipt = self._call_scqos(transition)
                verdict = receipt.get("decision")
            except Exception as exc:
                return self._defer(f"SCQOS decision substrate unavailable: {type(exc).__name__}", ["scqos_decision"])

        common = {
            "policy_references": [{"policy_id": "scqos", "policy_version": "live", "policy_name": "Supreme Computation", "rule_id": "transition-admissibility"}],
            "policy_data": {"scqos": {"verdict": verdict, "receipt_id": receipt.get("receipt_id"), "decision_boundary": receipt.get("decision_boundary"), "execution_mode": receipt.get("execution_mode")}},
        }
        if verdict == "PERMIT":
            return {"decision": "allow", "reasoning": "SCQOS proved the proposed transition admissible", **common}
        if verdict == "REJECT":
            return {"decision": "deny", "reasoning": receipt.get("reason", "SCQOS rejected the proposed transition"), "reason_codes": ["scqos_reject"], **common}
        return {**self._defer(receipt.get("reason", "SCQOS could not prove the transition"), ["coherent_transition_evidence"]), **common}

    def _acs_to_scqos(self, envelope: dict[str, Any]) -> dict[str, Any]:
        params = envelope["params"]
        payload = params.get("payload", {})
        metadata = params.get("metadata", {})
        tool = payload.get("tool", {}) if isinstance(payload, dict) else {}
        tool_name = tool.get("name", "unknown-tool") if isinstance(tool, dict) else "unknown-tool"
        target = self._arg(payload, "target", "acs://sandbox/default")
        effect = self._arg(payload, "effect", f"invoke:{tool_name}")
        roles = metadata.get("user_context", {}).get("roles", []) if isinstance(metadata.get("user_context"), dict) else []
        authority_scope = "challenge:execute" if "challenge:execute" in roles else (roles[0] if roles else "none")
        evidence_present = bool(self._arg(payload, "evidence_present", True))
        evidence = {
            "observed_at": _parse_time(params["timestamp"]),
            "source": "acs-wire",
            "reference_id": params["request_id"],
            "target": target,
        } if evidence_present else {}
        return {
            "tenant_id": metadata.get("agent_id", "acs-observed-agent"),
            "external_system": "owasp_acs",
            "subject": str(target),
            "authority": {"principal_id": metadata.get("user_context", {}).get("user_id", "acs-user") if isinstance(metadata.get("user_context"), dict) else "acs-user", "scope": authority_scope},
            "intent": {"action": tool_name, "target": target, "expected_effect": effect},
            "evidence": evidence,
            "current_state": {"source": "acs-guardian", "chain_hash": metadata.get("session_state", {}).get("chain_hash") if isinstance(metadata.get("session_state"), dict) else None},
            "proposed_transition": {"action": tool_name, "target": target, "effect": effect, "reference_id": params["request_id"]},
            "expected_consequence": {"effect": effect},
        }

    def _call_scqos(self, transition: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.scqos_endpoint + "/v1/challenge",
            data=json.dumps({"transition": transition}, separators=(",", ":")).encode(),
            headers={"content-type": "application/json", "accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            value = json.loads(response.read().decode())
        if not isinstance(value, dict) or value.get("decision") not in {"PERMIT", "HOLD", "REJECT"}:
            raise RuntimeError("SCQOS endpoint returned an invalid decision")
        return value

    @staticmethod
    def _local_scqos(transition: dict[str, Any]) -> str:
        if transition.get("authority", {}).get("scope") != "challenge:execute":
            return "REJECT"
        if not transition.get("evidence"):
            return "HOLD"
        return "PERMIT"

    @staticmethod
    def _defer(reason: str, required: list[str]) -> dict[str, Any]:
        return {
            "decision": "defer",
            "reasoning": reason,
            "reason_codes": ["insufficient_context"],
            "defer_details": {
                "reason": "insufficient_context",
                "resolution_method": "additional_context",
                "resolution_timeout_ms": 5000,
                "timeout_decision": "deny",
                "required_context": required,
            },
        }

    def _decision_response(self, request: dict[str, Any], session: Session, decision: dict[str, Any]) -> dict[str, Any]:
        params = request["params"]
        method = request["method"]
        previous = session.chain_hash
        entry = {
            "entry_id": str(uuid.uuid4()),
            "step_id": params["request_id"],
            "step_type": method,
            "request_hash": sha256_hex(params),
            "timestamp": params["timestamp"],
        }
        if previous:
            entry["previous_hash"] = previous
        entry_hash = hash_context_entry(entry, previous)
        entry["entry_hash"] = entry_hash
        session.chain_hash = entry_hash
        session.entries.append(entry)

        result: dict[str, Any] = {
            "type": "final",
            "acs_version": ACS_VERSION,
            "request_id": params["request_id"],
            "decision": decision["decision"],
            "chain_hash": entry_hash,
            "metadata": {"evaluator": "deterministic", "evaluator_version": "scqos-acs-lab/0.1.0"},
        }
        for name in ("reasoning", "reason_codes", "policy_references", "policy_data", "modifications", "ask_details", "defer_details"):
            if name in decision:
                result[name] = decision[name]
        response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
        result["signature"] = sign_envelope(response, self.ikm, session.session_id)
        return response

    def _result(self, request: dict[str, Any], session_id: str, decision: str, *, payload: dict[str, Any] | None = None, sign: bool = True, chain: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": "final",
            "acs_version": ACS_VERSION,
            "request_id": request["params"].get("request_id", str(uuid.uuid4())),
            "decision": decision,
        }
        if payload is not None:
            result["payload"] = payload
        response = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
        if sign:
            result["signature"] = sign_envelope(response, self.ikm, session_id)
        return response
