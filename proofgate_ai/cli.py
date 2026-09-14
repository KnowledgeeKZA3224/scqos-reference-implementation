from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict

from .client import DEFAULT_ENDPOINT, DEMO_ENDPOINT, ProofGateClient, ProofGateError


def _print(value: Dict[str, Any]) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _load_transition(path: str) -> Dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("transition JSON must be an object")
    return value


def _demo(scenario: str, timeout: float) -> Dict[str, Any]:
    url = DEMO_ENDPOINT + "?" + urllib.parse.urlencode({"scenario": scenario})
    with urllib.request.urlopen(url, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("demo returned an unexpected response shape")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="proofgate", description="Challenge a proposed transition before it becomes real.")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="SCQOS public challenge endpoint")
    parser.add_argument("--timeout", type=float, default=20.0)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health")
    sub.add_parser("matrix")
    challenge = sub.add_parser("challenge")
    source = challenge.add_mutually_exclusive_group(required=True)
    source.add_argument("--case", dest="case_id", choices=["valid", "authority_mismatch", "missing_evidence", "stale_evidence", "reference_mismatch", "effect_mismatch"])
    source.add_argument("--transition", metavar="FILE", help="JSON file containing a proposed transition")
    demo = sub.add_parser("demo")
    demo.add_argument("scenario", choices=["permit", "hold", "reject", "reroute"])
    args = parser.parse_args(argv)

    try:
        if args.command == "demo":
            result = _demo(args.scenario, args.timeout)
            _print(result)
            return 0 if result.get("verdict") in {"PERMIT", "REROUTE"} else 2

        client = ProofGateClient(endpoint=args.endpoint, timeout=args.timeout)
        if args.command == "health":
            result = client.health()
            _print(result)
            return 0 if result.get("status") == "operational" else 2
        if args.command == "matrix":
            result = client.matrix()
            _print(result)
            return 0 if result.get("all_pass") is True else 2
        if args.case_id:
            result = client.challenge_case(args.case_id)
        else:
            result = client.challenge_transition(_load_transition(args.transition))
        _print(result)
        return 0 if result.get("decision") == "PERMIT" else 2
    except (OSError, ValueError, ProofGateError) as exc:
        print(f"proofgate: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
