from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .client import ACSClient

SUPPORTED_REQUIREMENTS = {"ACS-R-001", "ACS-R-002", "ACS-R-003", "ACS-R-006", "ACS-R-017", "ACS-R-019", "ACS-R-020"}


def _now_iso(offset_seconds: float = 0.0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat().replace("+00:00", "Z")


def _result_code(response: dict[str, Any]) -> int | None:
    err = response.get("error")
    return err.get("code") if isinstance(err, dict) else None


def _decision(response: dict[str, Any]) -> str | None:
    result = response.get("result")
    return result.get("decision") if isinstance(result, dict) else None


def _expect(vector: dict[str, Any], response: dict[str, Any]) -> bool:
    expected = vector["expected"]
    if expected["verdict"] == "deny":
        code = expected.get("codeValue")
        if code is not None:
            return _result_code(response) == code
        return isinstance(response.get("error"), dict) or _decision(response) in {"deny", "defer"}
    if expected["verdict"] == "allow":
        # Handshake accepts with ServerHello; ordinary traffic accepts with allow.
        return isinstance(response.get("result"), dict) and (
            response["result"].get("negotiated_version") == "0.1.0"
            or response["result"].get("decision") == "allow"
        )
    return False


def _base_tool(client: ACSClient, *, request_id: str | None = None, timestamp: str | None = None, sign: bool = True):
    payload = {
        "tool": {"name": "records.lookup", "version": "1"},
        "arguments": {
            "target": {"value": "acs://external-vector/c-1"},
            "effect": {"value": "lookup:c-1"},
            "evidence_present": {"value": True},
        },
    }
    return client.envelope("steps/toolCallRequest", payload, roles=["challenge:execute"], request_id=request_id, timestamp=timestamp, sign=sign)


def drive_vector(vector: dict[str, Any], client: ACSClient) -> tuple[str, dict[str, Any]]:
    reqs = set(vector.get("requirements", []))
    expected = vector.get("expected", {})
    if expected.get("verdict") == "unmeasurable":
        return "UNMEASURABLE", {"reason": expected.get("unmeasurableBecause")}
    if not reqs or not reqs.issubset(SUPPORTED_REQUIREMENTS):
        return "NOT_DRIVEN", {"reason": "requires framework/deployment/approver semantics outside this wire adapter", "requirements": sorted(reqs)}

    payload = vector.get("payload", {})
    response: dict[str, Any]

    if "ACS-R-017" in reqs:
        request = payload.get("request", {})
        versions = request.get("params", {}).get("acs_versions_supported", ["0.1.0"])
        response = client.handshake(versions=versions)
        return ("PASS" if _expect(vector, response) else "FAIL"), {"response": response}

    if "ACS-R-019" in reqs:
        steps = payload.get("steps", [])
        if not steps:
            request = payload.get("request", {})
            versions = request.get("params", {}).get("acs_versions_supported", ["0.1.0"])
            response = client.handshake(versions=versions)
            return ("PASS" if _expect(vector, response) else "FAIL"), {"response": response}
        hs_req = steps[0].get("request", {})
        versions = hs_req.get("params", {}).get("acs_versions_supported", ["0.1.0"])
        hs = client.handshake(versions=versions)
        if hs.get("result", {}).get("negotiated_version") != "0.1.0":
            return "FAIL", {"reason": "setup handshake failed", "response": hs}
        raw_version = str(steps[1].get("request", {}).get("acs", "1.0"))
        wire_version = raw_version + ".0" if raw_version.count(".") == 1 else raw_version
        env = _base_tool(client)
        env["params"]["acs_version"] = wire_version
        from .crypto import sign_envelope
        env["params"]["signature"] = sign_envelope(env, client.ikm, client.session_id)
        response = client.send(env, update_chain=False)
        return ("PASS" if _expect(vector, response) else "FAIL"), {"handshake": hs, "response": response, "post_handshake_version": wire_version}

    # Every non-handshake wire vector runs inside a valid negotiated session.
    hs = client.handshake()
    if hs.get("result", {}).get("negotiated_version") != "0.1.0":
        return "FAIL", {"reason": "setup handshake failed", "response": hs}

    if "ACS-R-001" in reqs or "ACS-R-020" in reqs:
        state = payload.get("signature_state", "VALID")
        env = _base_tool(client, sign=(state != "ABSENT"))
        if state in {"INVALID", "COVERS_SUBSET"}:
            env["params"]["signature"]["value"] = "AAAA"
        response = client.send(env, update_chain=False)
        return ("PASS" if _expect(vector, response) else "FAIL"), {"response": response, "signature_state": state}

    if "ACS-R-002" in reqs:
        steps = payload.get("steps", [])
        ids = [s.get("request", {}).get("request_id") for s in steps]
        rid1 = ids[0] if ids and ids[0] else "11111111-1111-4111-8111-111111111111"
        rid2 = ids[1] if len(ids) > 1 and ids[1] else rid1
        first = client.send(_base_tool(client, request_id=rid1))
        second = client.send(_base_tool(client, request_id=rid2), update_chain=False)
        response = second if vector["expected"]["verdict"] == "deny" else second
        return ("PASS" if _expect(vector, response) else "FAIL"), {"first": first, "response": second, "request_ids": [rid1, rid2]}

    if "ACS-R-003" in reqs:
        clock = payload.get("guardian_clock")
        raw = payload.get("request", {}).get("timestamp")
        if clock and raw:
            def parse(x: str) -> datetime:
                return datetime.fromisoformat(x.replace("Z", "+00:00"))
            delta = (parse(raw) - parse(clock)).total_seconds()
        else:
            delta = 0
        env = _base_tool(client, timestamp=_now_iso(delta))
        response = client.send(env, update_chain=False)
        return ("PASS" if _expect(vector, response) else "FAIL"), {"response": response, "relative_timestamp_offset_seconds": delta}

    if "ACS-R-006" in reqs:
        if vector.get("evidenceBasis") == "artifact":
            return "NOT_DRIVEN", {"reason": "artifact-verification vector; this wire adapter does not rewrite the supplied artifact into a live request"}
        response = client.send(_base_tool(client))
        result = response.get("result", {})
        ok = isinstance(result.get("chain_hash"), str) and len(result["chain_hash"]) == 64 and client.response_signature_valid(response)
        expected_allow = vector["expected"]["verdict"] == "allow"
        passed = ok if expected_allow else not ok
        return ("PASS" if passed else "FAIL"), {"response": response, "chain_and_response_signature_valid": ok}

    return "NOT_DRIVEN", {"reason": "adapter has no deterministic mapping"}


def run(corpus: Path, endpoint: str | None, direct: bool, live_scqos: bool) -> dict[str, Any]:
    if direct:
        from .guardian import SCQOSGuardian
        guardian = SCQOSGuardian(live_scqos=live_scqos)
        factory = lambda: ACSClient(process=guardian.process)
        mode = "scqos-live" if live_scqos else "scqos-local"
    else:
        factory = lambda: ACSClient(endpoint=endpoint)
        mode = endpoint or "http"
    manifest = json.loads((corpus / "MANIFEST.json").read_text())
    rows = []
    for item in manifest.get("vectors", []):
        vector = json.loads((corpus / item["file"]).read_text())
        client = factory()
        status, detail = drive_vector(vector, client)
        rows.append({"id": vector["id"], "family": vector["family"], "requirements": vector["requirements"], "expected": vector["expected"], "status": status, "detail": detail})
    counts = {k: sum(1 for r in rows if r["status"] == k) for k in ("PASS", "FAIL", "NOT_DRIVEN", "UNMEASURABLE")}
    return {
        "schema": "scqos.acs.external-vector-run.v1",
        "mode": mode,
        "corpus_digest": manifest.get("corpusDigest"),
        "spec_upstream_commit": manifest.get("specUpstreamCommit"),
        "counts": counts,
        "all_driven_pass": counts["FAIL"] == 0,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--endpoint")
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--live-scqos", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    result = run(Path(args.corpus), args.endpoint, args.direct, args.live_scqos)
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({"mode": result["mode"], "counts": result["counts"], "all_driven_pass": result["all_driven_pass"], "corpus_digest": result["corpus_digest"]}, indent=2))
    return 0 if result["all_driven_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
