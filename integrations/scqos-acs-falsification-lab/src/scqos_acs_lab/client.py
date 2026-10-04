from __future__ import annotations

import json
import os
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .crypto import sign_envelope, verify_envelope

ACS_VERSION = "0.1.0"
DEFAULT_METHODS = [
    "steps/sessionStart",
    "steps/userMessage",
    "steps/toolCallRequest",
    "steps/toolCallResult",
    "steps/agentResponse",
    "steps/sessionEnd",
    "system/ping",
    "protocols/MCP/tools/call",
]


def iso_now(offset_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat().replace("+00:00", "Z")


class ACSClient:
    def __init__(
        self,
        endpoint: str | None = None,
        *,
        ikm: bytes | None = None,
        agent_id: str = "falsification-agent",
        process: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.endpoint = (endpoint or "http://127.0.0.1:18888/acs").rstrip("/")
        self.ikm = ikm or os.environ.get("ACS_LAB_PSK", "public-falsification-lab-test-key").encode()
        self.agent_id = agent_id
        self.session_id = str(uuid.uuid4())
        self.chain_hash: str | None = None
        self.process = process

    def _send(self, envelope: dict[str, Any]) -> dict[str, Any]:
        if self.process is not None:
            return self.process(envelope)
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(envelope, separators=(",", ":")).encode(),
            headers={"content-type": "application/json", "accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            value = json.loads(response.read().decode())
        if not isinstance(value, dict):
            raise RuntimeError("Guardian returned non-object JSON-RPC response")
        return value

    def envelope(
        self,
        method: str,
        payload: dict[str, Any],
        *,
        roles: list[str] | None = None,
        request_id: str | None = None,
        timestamp: str | None = None,
        nonce: str | None = None,
        include_chain: bool = True,
        sign: bool = True,
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "environment": "staging",
            "user_context": {
                "user_id": "falsification-operator",
                "roles": roles or ["challenge:execute"],
                "authentication_method": "lab-hmac",
            },
        }
        if include_chain and self.chain_hash:
            metadata["session_state"] = {"chain_hash": self.chain_hash}
        params: dict[str, Any] = {
            "acs_version": ACS_VERSION,
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": timestamp or iso_now(),
            "metadata": metadata,
            "payload": payload,
        }
        if nonce:
            params["nonce"] = nonce
        envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": str(uuid.uuid4()), "params": params}
        if sign:
            params["signature"] = sign_envelope(envelope, self.ikm, self.session_id)
        return envelope

    def handshake(self, *, versions: list[str] | None = None, sign: bool = True) -> dict[str, Any]:
        hello = {
            "acs_versions_supported": versions or [ACS_VERSION],
            "methods_implemented": DEFAULT_METHODS,
            "transports_supported": ["http"],
            "max_payload_size_bytes": 1_048_576,
            "provenance_producer": "none",
            "profiles_supported": ["acs-core"],
            "wrapped_protocols": [{"protocol": "MCP", "version": "2025-06-18"}],
        }
        return self._send(self.envelope("handshake/hello", hello, include_chain=False, sign=sign))

    def send(self, envelope: dict[str, Any], *, update_chain: bool = True) -> dict[str, Any]:
        response = self._send(envelope)
        if update_chain and isinstance(response.get("result"), dict):
            head = response["result"].get("chain_hash")
            if isinstance(head, str):
                self.chain_hash = head
        return response

    def tool(
        self,
        *,
        tool: str = "lab.write",
        target: str = "acs://sandbox/object",
        effect: str = "create:test-object",
        roles: list[str] | None = None,
        evidence_present: bool = True,
        requires_approval: bool = False,
        safe_rewrite: str | None = None,
        **wire: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        args: dict[str, Any] = {
            "target": {"value": target},
            "effect": {"value": effect},
            "evidence_present": {"value": evidence_present},
        }
        if requires_approval:
            args["requires_approval"] = {"value": True}
        if safe_rewrite is not None:
            args["safe_rewrite"] = {"value": safe_rewrite}
        payload = {
            "tool": {"name": tool, "version": "1"},
            "capability": "lab.transition",
            "arguments": args,
            "intent": {"description": "falsification-lab governed transition", "goal": effect},
        }
        env = self.envelope("steps/toolCallRequest", payload, roles=roles, **wire)
        return env, self.send(env)

    def response_signature_valid(self, response: dict[str, Any]) -> bool:
        return verify_envelope(response, self.ikm, self.session_id)
