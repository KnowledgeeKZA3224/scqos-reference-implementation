from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .client import ACSClient, iso_now
from .guardian import SCQOSGuardian


@dataclass
class Probe:
    name: str
    expected: str
    observed: str
    passed: bool
    detail: dict[str, Any]


def _obs(response: dict[str, Any]) -> str:
    if isinstance(response.get("error"), dict):
        return f"error:{response['error'].get('code')}"
    if isinstance(response.get("result"), dict):
        return f"decision:{response['result'].get('decision', 'server_hello')}"
    return "invalid-response"


def _probe(name: str, expected: str, response: dict[str, Any], predicate: Callable[[dict[str, Any]], bool]) -> Probe:
    return Probe(name, expected, _obs(response), bool(predicate(response)), response)


def run_suite(client: ACSClient) -> list[Probe]:
    probes: list[Probe] = []

    hs = client.handshake()
    probes.append(_probe("handshake", "ServerHello 0.1.0 + fail-closed posture", hs, lambda r: r.get("result", {}).get("negotiated_version") == "0.1.0" and r.get("result", {}).get("on_decision_failure") == "deny"))

    ping = client.send(client.envelope("system/ping", {"echo": "alive"}, sign=False, include_chain=False))
    probes.append(_probe("unsigned_ping", "allow", ping, lambda r: r.get("result", {}).get("decision") == "allow"))

    env, valid = client.tool(target="acs://sandbox/valid")
    probes.append(_probe("valid_transition", "allow + signed chain head", valid, lambda r: r.get("result", {}).get("decision") == "allow" and len(r.get("result", {}).get("chain_hash", "")) == 64 and client.response_signature_valid(r)))

    _, wrong_authority = client.tool(target="acs://sandbox/wrong-authority", roles=["read:only"])
    probes.append(_probe("wrong_authority", "deny", wrong_authority, lambda r: r.get("result", {}).get("decision") == "deny"))

    _, missing = client.tool(target="acs://sandbox/missing-evidence", evidence_present=False)
    probes.append(_probe("missing_evidence", "defer with deny timeout", missing, lambda r: r.get("result", {}).get("decision") == "defer" and r.get("result", {}).get("defer_details", {}).get("timeout_decision") == "deny"))

    unsigned = client.envelope("steps/toolCallRequest", {"tool": {"name": "lab.write"}, "arguments": {}}, sign=False)
    unsigned_resp = client.send(unsigned, update_chain=False)
    probes.append(_probe("missing_signature", "error:-32004", unsigned_resp, lambda r: r.get("error", {}).get("code") == -32004))

    bad = client.envelope("steps/toolCallRequest", {"tool": {"name": "lab.write"}, "arguments": {}})
    bad["params"]["signature"]["value"] = "AAAA"
    bad_resp = client.send(bad, update_chain=False)
    probes.append(_probe("tampered_signature", "error:-32004", bad_resp, lambda r: r.get("error", {}).get("code") == -32004))

    replay_env = client.envelope("steps/toolCallRequest", {"tool": {"name": "lab.write"}, "arguments": {"target": {"value": "acs://sandbox/replay"}, "effect": {"value": "create"}}})
    first = client.send(replay_env)
    second = client.send(replay_env, update_chain=False)
    probes.append(_probe("replay_first", "allow", first, lambda r: r.get("result", {}).get("decision") == "allow"))
    probes.append(_probe("replay_second", "error:-32005", second, lambda r: r.get("error", {}).get("code") == -32005))

    stale = client.envelope("steps/toolCallRequest", {"tool": {"name": "lab.write"}, "arguments": {}}, timestamp=iso_now(-3600))
    stale_resp = client.send(stale, update_chain=False)
    probes.append(_probe("stale_timestamp", "error:-32006", stale_resp, lambda r: r.get("error", {}).get("code") == -32006))

    future = client.envelope("steps/toolCallRequest", {"tool": {"name": "lab.write"}, "arguments": {}}, timestamp=iso_now(3600))
    future_resp = client.send(future, update_chain=False)
    probes.append(_probe("future_timestamp", "error:-32006", future_resp, lambda r: r.get("error", {}).get("code") == -32006))

    # Sign a request that intentionally claims the wrong prior chain head.
    saved = client.chain_hash
    client.chain_hash = "f" * 64
    mismatch = client.envelope("steps/toolCallRequest", {"tool": {"name": "lab.write"}, "arguments": {}})
    client.chain_hash = saved
    mismatch_resp = client.send(mismatch, update_chain=False)
    probes.append(_probe("chain_mismatch", "error:-32007", mismatch_resp, lambda r: r.get("error", {}).get("code") == -32007))

    _, modify = client.tool(target="acs://sandbox/unsafe", safe_rewrite="acs://sandbox/safe")
    probes.append(_probe("modify_disposition", "modify", modify, lambda r: r.get("result", {}).get("decision") == "modify" and "modifications" in r.get("result", {})))

    _, ask = client.tool(target="acs://sandbox/approval", requires_approval=True)
    probes.append(_probe("ask_disposition", "ask", ask, lambda r: r.get("result", {}).get("decision") == "ask" and r.get("result", {}).get("ask_details", {}).get("timeout_disposition") == "deny"))

    for method in ("steps/sessionStart", "steps/userMessage", "steps/toolCallResult", "steps/agentResponse", "steps/sessionEnd", "protocols/MCP/tools/call"):
        env = client.envelope(method, {"event": method})
        resp = client.send(env)
        probes.append(_probe(f"dispatch_{method}", "non-error decision", resp, lambda r: isinstance(r.get("result"), dict) and r["result"].get("decision") in {"allow", "deny", "modify", "ask", "defer"}))

    return probes


class AllowEverythingMutant:
    def process(self, envelope: dict[str, Any]) -> dict[str, Any]:
        if envelope.get("method") == "handshake/hello":
            return {"jsonrpc": "2.0", "id": envelope.get("id"), "result": {"negotiated_version": "0.1.0", "methods_evaluated": envelope.get("params", {}).get("payload", {}).get("methods_implemented", []), "selected_transport": "http", "timeout_config": {"default_ms": 5000}, "on_decision_failure": "deny"}}
        return {"jsonrpc": "2.0", "id": envelope.get("id"), "result": {"type": "final", "acs_version": "0.1.0", "request_id": envelope.get("params", {}).get("request_id", "x"), "decision": "allow"}}


class DenyEverythingMutant:
    def process(self, envelope: dict[str, Any]) -> dict[str, Any]:
        if envelope.get("method") == "handshake/hello":
            return {"jsonrpc": "2.0", "id": envelope.get("id"), "result": {"negotiated_version": "0.1.0", "methods_evaluated": envelope.get("params", {}).get("payload", {}).get("methods_implemented", []), "selected_transport": "http", "timeout_config": {"default_ms": 5000}, "on_decision_failure": "deny"}}
        return {"jsonrpc": "2.0", "id": envelope.get("id"), "result": {"type": "final", "acs_version": "0.1.0", "request_id": envelope.get("params", {}).get("request_id", "x"), "decision": "deny"}}


class SignatureBlindGuardian(SCQOSGuardian):
    def _check_wire(self, envelope: dict[str, Any], session_id: str):
        from .guardian import _error, _parse_time
        params = envelope["params"]
        required = ("acs_version", "request_id", "timestamp", "metadata", "payload")
        if any(name not in params for name in required):
            return {"jsonrpc": "2.0", "id": envelope.get("id"), "error": {"code": -32600, "message": "Invalid Request"}}
        try:
            drift_ms = abs(time.time() - _parse_time(str(params["timestamp"]))) * 1000
        except Exception:
            return _error(envelope.get("id"), -32006, "timestamp cannot be parsed", skew_window_ms=self.skew_window_ms)
        if drift_ms > self.skew_window_ms:
            return _error(envelope.get("id"), -32006, "timestamp outside negotiated window", skew_window_ms=self.skew_window_ms)
        return None


class ReplayBlindGuardian(SCQOSGuardian):
    def process(self, envelope: dict[str, Any]) -> dict[str, Any]:
        params = envelope.get("params", {}) if isinstance(envelope, dict) else {}
        metadata = params.get("metadata", {}) if isinstance(params, dict) else {}
        sid = metadata.get("session_id") if isinstance(metadata, dict) else None
        rid = params.get("request_id") if isinstance(params, dict) else None
        nonce = params.get("nonce") if isinstance(params, dict) else None
        if sid in self.sessions:
            if rid:
                self.sessions[sid].seen_request_ids.discard(rid)
            if nonce:
                self.sessions[sid].seen_nonces.discard(nonce)
        return super().process(envelope)


REQUIRED_PROBES = {
    "handshake", "unsigned_ping", "valid_transition", "wrong_authority", "missing_evidence",
    "missing_signature", "tampered_signature", "replay_first", "replay_second", "stale_timestamp",
    "future_timestamp", "chain_mismatch", "modify_disposition", "ask_disposition",
    "dispatch_steps/sessionStart", "dispatch_steps/userMessage", "dispatch_steps/toolCallResult",
    "dispatch_steps/agentResponse", "dispatch_steps/sessionEnd", "dispatch_protocols/MCP/tools/call",
}


def _mutant_result(name: str, process) -> dict[str, Any]:
    rows = run_suite(ACSClient(process=process))
    failed = [p.name for p in rows if not p.passed]
    present = {p.name for p in rows}
    return {
        "mutant": name,
        "detected": bool(failed) or present != REQUIRED_PROBES,
        "failed_probes": failed,
        "missing_probes": sorted(REQUIRED_PROBES - present),
    }


def meta_test() -> dict[str, Any]:
    allow = AllowEverythingMutant()
    deny = DenyEverythingMutant()
    signature_blind = SignatureBlindGuardian(live_scqos=False)
    replay_blind = ReplayBlindGuardian(live_scqos=False)
    rows = run_suite(ACSClient(process=SCQOSGuardian(live_scqos=False).process))
    intentionally_skipped = rows[:-1]
    skip_detected = {p.name for p in intentionally_skipped} != REQUIRED_PROBES
    from .side_effect import validate_claimed_effect
    fake_path = Path(tempfile.gettempdir()) / "scqos-acs-fake-success-must-not-exist"
    if fake_path.exists():
        fake_path.unlink()
    fake_success_detected = not validate_claimed_effect(fake_path, "0" * 64, True)
    mutants = [
        _mutant_result("allow-everything", allow.process),
        _mutant_result("deny-everything", deny.process),
        _mutant_result("signature-blind", signature_blind.process),
        _mutant_result("replay-blind", replay_blind.process),
        {
            "mutant": "fake-success-adapter",
            "detected": fake_success_detected,
            "failed_probes": ["physical-state-check"] if fake_success_detected else [],
            "missing_probes": [],
        },
        {
            "mutant": "skipped-test-runner",
            "detected": skip_detected,
            "failed_probes": [],
            "missing_probes": sorted(REQUIRED_PROBES - {p.name for p in intentionally_skipped}),
        },
    ]
    return {"all_detected": all(m["detected"] for m in mutants), "mutants": mutants}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:18888/acs")
    parser.add_argument("--direct-local", action="store_true")
    parser.add_argument("--live-scqos", action="store_true", help="with --direct-local, call the live SCQOS endpoint")
    parser.add_argument("--output", default="run-evidence/latest.json")
    args = parser.parse_args(argv)

    if args.direct_local:
        guardian = SCQOSGuardian(live_scqos=args.live_scqos)
        client = ACSClient(process=guardian.process)
        mode = "direct-live-scqos" if args.live_scqos else "direct-local-scqos"
    else:
        client = ACSClient(endpoint=args.endpoint)
        mode = "http"
    rows = run_suite(client)
    meta = meta_test()
    result = {
        "schema": "scqos.acs.falsification.run.v1",
        "mode": mode,
        "generated_at": time.time(),
        "passed": sum(p.passed for p in rows),
        "total": len(rows),
        "all_pass": all(p.passed for p in rows),
        "meta_test": meta,
        "probes": [asdict(p) for p in rows],
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({k: result[k] for k in ("mode", "passed", "total", "all_pass", "meta_test")}, indent=2))
    return 0 if result["all_pass"] and meta["all_detected"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
