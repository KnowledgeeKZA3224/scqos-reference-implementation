from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .client import ACSClient
from .guardian import SCQOSGuardian


def _digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None



def validate_claimed_effect(path: Path, claimed_sha256: str | None, claimed_exists: bool) -> bool:
    actual_exists = path.exists()
    if actual_exists != claimed_exists:
        return False
    if not actual_exists:
        return claimed_sha256 is None
    return _digest(path) == claimed_sha256


def run(*, live_scqos: bool, root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    for old in root.glob("*.txt"):
        old.unlink()
    guardian = SCQOSGuardian(live_scqos=live_scqos)
    client = ACSClient(process=guardian.process)
    handshake = client.handshake()

    allowed_path = root / "permitted.txt"
    denied_path = root / "denied.txt"
    replay_path = root / "replay.txt"

    def governed_write(path: Path, text: str, roles: list[str] | None = None, envelope=None) -> tuple[dict[str, Any], bool]:
        if envelope is None:
            env, response = client.tool(target=f"file://{path}", effect=f"write:{hashlib.sha256(text.encode()).hexdigest()}", roles=roles)
        else:
            env = envelope
            response = client.send(env, update_chain=False)
        decision = response.get("result", {}).get("decision")
        executed = False
        if decision == "allow":
            path.write_text(text)
            executed = True
        return {"request": env, "response": response}, executed

    valid, valid_exec = governed_write(allowed_path, "SCQOS permitted this bounded terminal consequence.\n")
    denied, denied_exec = governed_write(denied_path, "THIS MUST NOT EXIST\n", roles=["read:only"])

    replay_env = client.envelope(
        "steps/toolCallRequest",
        {
            "tool": {"name": "lab.write", "version": "1"},
            "arguments": {
                "target": {"value": f"file://{replay_path}"},
                "effect": {"value": "write:replay-proof"},
                "evidence_present": {"value": True},
            },
        },
        roles=["challenge:execute"],
    )
    first_response = client.send(replay_env)
    first_exec = False
    if first_response.get("result", {}).get("decision") == "allow":
        replay_path.write_text("executed-once\n")
        first_exec = True
    first_digest = _digest(replay_path)
    second_response = client.send(replay_env, update_chain=False)
    second_exec = False
    if second_response.get("result", {}).get("decision") == "allow":
        replay_path.write_text(replay_path.read_text() + "executed-twice\n")
        second_exec = True
    second_digest = _digest(replay_path)

    assertions = {
        "handshake_fail_closed": handshake.get("result", {}).get("on_decision_failure") == "deny",
        "valid_executed": valid_exec and allowed_path.exists(),
        "denied_not_executed": (not denied_exec) and (not denied_path.exists()),
        "replay_first_executed": first_exec and replay_path.exists(),
        "replay_second_blocked": (not second_exec) and second_response.get("error", {}).get("code") == -32005,
        "replay_state_unchanged": first_digest == second_digest,
    }
    return {
        "schema": "scqos.acs.real-consequence-proof.v1",
        "generated_at": time.time(),
        "mode": "live-scqos-cloud_to_terminal" if live_scqos else "local-scqos_to_terminal",
        "root": str(root),
        "assertions": assertions,
        "all_pass": all(assertions.values()),
        "artifacts": {
            "permitted": {"exists": allowed_path.exists(), "sha256": _digest(allowed_path)},
            "denied": {"exists": denied_path.exists(), "sha256": _digest(denied_path)},
            "replay": {"exists": replay_path.exists(), "sha256_before_replay": first_digest, "sha256_after_replay": second_digest},
        },
        "wire": {"valid": valid, "denied": denied, "replay_first": first_response, "replay_second": second_response},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-scqos", action="store_true")
    parser.add_argument("--root", default="lab/controlled-effects")
    parser.add_argument("--output", default="run-evidence/real-consequence.json")
    args = parser.parse_args(argv)
    result = run(live_scqos=args.live_scqos, root=Path(args.root).resolve())
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({"mode": result["mode"], "all_pass": result["all_pass"], "assertions": result["assertions"], "artifacts": result["artifacts"]}, indent=2))
    return 0 if result["all_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
