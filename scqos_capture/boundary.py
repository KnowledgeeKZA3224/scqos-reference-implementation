"""Five independently testable boundaries between evidence and durable memory.

This is a reference contract. A production adapter must enforce the intent's
expected prior version and exact write in a *single database transaction*;
postcommit witnessing cannot retroactively make an unauthorized write safe.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence


def _digest(value: Any) -> str:
    # Local deterministic identity only. Do not substitute for the project's
    # declared SCQOS-C14N-JCS-NFC-1 canonicalization on the production path.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def authority_decision(chain: Sequence[Mapping[str, Any]], *, action: str,
                       subject: str, now: datetime,
                       revoked_ids: set[str] | frozenset[str] = frozenset()) -> dict:
    """Validate an explicit root-to-leaf delegation and current revocation set."""
    try:
        if not chain or not action or not subject or now.tzinfo is None:
            raise ValueError("missing authority context")
        for index, grant in enumerate(chain):
            if not grant["id"] or grant["id"] in revoked_ids:
                raise ValueError("missing or revoked grant")
            if index == 0:
                if grant.get("parent_id") is not None or not grant.get("root_trusted"):
                    raise ValueError("untrusted authority root")
            elif (grant.get("parent_id") != chain[index - 1]["id"] or
                  grant.get("issuer") != chain[index - 1]["subject"]):
                raise ValueError("broken delegation lineage")
            if not (_time(grant["not_before"]) <= now.astimezone(timezone.utc) <
                    _time(grant["expires_at"])):
                raise ValueError("grant not currently valid")
            if action not in grant["actions"]:
                raise ValueError("action exceeds grant scope")
            if index and not set(grant["actions"]).issubset(chain[index - 1]["actions"]):
                raise ValueError("child exceeds parent scope")
        if chain[-1]["subject"] != subject:
            raise ValueError("wrong authority subject")
        return {"state": "PERMIT", "authority_hash": _digest(chain)}
    except (KeyError, TypeError, ValueError) as error:
        return {"state": "HOLD", "reason": str(error)}


def freeze_intent(*, transition_id: str, target: str, prior_hash: str,
                  proposed_state: Any, evidence_hash: str, authority_hash: str,
                  policy_hash: str, expires_at: str) -> dict:
    """Commit to the exact planned write before any permission is evaluated."""
    if not all((transition_id, target, prior_hash, evidence_hash,
                authority_hash, policy_hash)):
        raise ValueError("incomplete intent")
    _time(expires_at)
    body = {"transition_id": transition_id, "target": target,
            "prior_hash": prior_hash, "proposed_hash": _digest(proposed_state),
            "evidence_hash": evidence_hash, "authority_hash": authority_hash,
            "policy_hash": policy_hash, "expires_at": expires_at}
    return {**body, "intent_hash": _digest(body)}


def precommit_decision(intent: Mapping[str, Any], *, current_hash: str,
                       proposed_state: Any, authority_hash: str, evidence_hash: str,
                       policy_hash: str, now: datetime) -> dict:
    """Require exact identity, authority and prior state immediately before write."""
    try:
        body = {key: value for key, value in intent.items() if key != "intent_hash"}
        valid = (intent["intent_hash"] == _digest(body) and
                 _time(intent["expires_at"]) > now.astimezone(timezone.utc) and
                 current_hash == intent["prior_hash"] and
                 _digest(proposed_state) == intent["proposed_hash"] and
                 authority_hash == intent["authority_hash"] and
                 evidence_hash == intent["evidence_hash"] and
                 policy_hash == intent["policy_hash"])
        return {"state": "PERMIT" if valid else "HOLD",
                "intent_hash": intent.get("intent_hash")}
    except (KeyError, TypeError, ValueError, OverflowError):
        return {"state": "HOLD", "reason": "invalid or incomplete intent"}


def witness_effect(intent: Mapping[str, Any], *, read_back: Callable[[str], Any],
                   committed_transition_id: str, committed_intent_hash: str) -> dict:
    """Independently inspect the resulting value; a mismatch remains unresolved."""
    try:
        observed_hash = _digest(read_back(intent["target"]))
        if (observed_hash != intent["proposed_hash"] or
                committed_transition_id != intent["transition_id"] or
                committed_intent_hash != intent["intent_hash"]):
            return {"state": "HOLD", "reason": "effect differs from committed intent",
                    "observed_hash": observed_hash}
        body = {"transition_id": committed_transition_id,
                "intent_hash": committed_intent_hash, "observed_hash": observed_hash}
        return {"state": "PERMIT", **body, "witness_hash": _digest(body)}
    except (KeyError, TypeError, ValueError, RuntimeError, OSError):
        return {"state": "HOLD", "reason": "effect readback failed"}


def compare_shadow(*, candidate_id: str, baseline: Mapping[str, str],
                   simulate: Callable[[str], Mapping[str, str]]) -> dict:
    """Measure candidate decision changes without promoting the candidate."""
    try:
        if not candidate_id or not baseline:
            raise ValueError("missing candidate or baseline")
        shadow = simulate(candidate_id)
        if set(shadow) != set(baseline):
            raise ValueError("shadow and baseline cases differ")
        changes = {key: {"baseline": baseline[key], "candidate": shadow[key]}
                   for key in sorted(baseline) if baseline[key] != shadow[key]}
        return {"state": "HOLD", "candidate_id": candidate_id,
                "changes": changes, "evaluated_cases": len(baseline),
                "reason": "shadow evaluation never promotes a candidate"}
    except (TypeError, ValueError, RuntimeError, KeyError):
        return {"state": "HOLD", "reason": "shadow comparison incomplete"}


def blast_radius(invalidated_id: str, dependencies: Mapping[str, Sequence[str]]) -> dict:
    """Find transitive descendants; require explicit disposition for each one."""
    if not invalidated_id:
        return {"state": "HOLD", "reason": "missing invalidated transition"}
    seen = {invalidated_id}
    queue = deque([invalidated_id])
    descendants = []
    while queue:
        parent = queue.popleft()
        for child in dependencies.get(parent, ()):
            if child not in seen:
                seen.add(child)
                descendants.append(child)
                queue.append(child)
    return {"state": "HOLD", "invalidated_id": invalidated_id,
            "descendants": descendants,
            "required_dispositions": {child: "UNRESOLVED" for child in descendants}}
