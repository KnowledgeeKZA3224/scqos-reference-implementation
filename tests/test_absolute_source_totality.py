import hashlib
import json
import os
import tempfile
from pathlib import Path

tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
tmp.close()
os.environ["SCQOS_UNIVERSAL_DB"] = tmp.name
os.environ["SCQOS_SECRET_KEY"] = "absolute-source-totality-test-" + "a" * 64

from integration.universal_gateway import TransitionRequest, govern_transition


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "integration" / "absolute_source_totality.v1.json"


def manifest():
    return json.loads(MANIFEST_PATH.read_text())


def sha256(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def test_totality_manifest_is_one_closed_cycle():
    state = manifest()
    assert state["contract_id"] == "SCQOS-ABSOLUTE-SOURCE-TOTALITY-v1"
    assert state["supreme_computation"]["fail_closed"] is True
    assert state["supreme_computation"]["receipt_required"] is True
    assert len(state["supreme_computation"]["invariants"]) == 8
    assert set(state["upstreams"]) == {"perception", "cognition", "actuation"}
    assert state["live_aws_observation"]["source_bridge"] == "supreme-source-layer-bridge-v1"
    assert state["live_aws_observation"]["gate"] == "supreme-totality-gate-v1"
    assert state["live_aws_observation"]["witness_bridge"] == "supreme-totality-witness-bridge-v1"


def test_totality_manifest_crosses_existing_universal_gateway():
    state = manifest()
    state_hash = sha256(state)

    request = TransitionRequest.model_validate({
        "tenant_id": "supreme-totality",
        "external_system": "absolute-source-layer-totality",
        "subject": state["contract_id"],
        "authority": {
            "principal_id": "supreme-source-layer-bridge-v1",
            "scope": "totality:release",
        },
        "intent": "bind one source state to one governed consequence",
        "evidence": {
            "manifest_sha256": state_hash,
            "upstreams": state["upstreams"],
            "live_aws_observation": state["live_aws_observation"],
        },
        "current_state": {
            "source_state": "pinned",
            "coherence_required": True,
        },
        "proposed_transition": {
            "operation": "release_candidate",
            "manifest_sha256": state_hash,
        },
        "expected_consequence": {
            "receipt_required": True,
            "next_genesis_required": True,
        },
        "metadata": {
            "contract_id": state["contract_id"],
            "one_cycle": state["one_cycle"],
        },
    })

    result = govern_transition(request)
    assert result.decision == "PERMIT"
    assert result.execution_authorized is True
    assert len(result.gate_proofs) == 9
    assert all(result.gate_proofs.values())


def test_totality_never_inherits_unauthorized_authority():
    state = manifest()

    request = TransitionRequest.model_validate({
        "tenant_id": "supreme-totality",
        "external_system": "absolute-source-layer-totality",
        "subject": state["contract_id"],
        "authority": {
            "principal_id": "external-upstream",
            "scope": "unauthorized",
        },
        "intent": "attempt to inherit authority from an upstream",
        "evidence": {"upstreams": state["upstreams"]},
        "current_state": {},
        "proposed_transition": {"operation": "release_candidate"},
        "expected_consequence": {"receipt_required": True},
    })

    result = govern_transition(request)
    assert result.decision == "REJECT"
    assert result.execution_authorized is False
