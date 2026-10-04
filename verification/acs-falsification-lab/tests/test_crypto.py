from scqos_acs_lab.client import ACSClient
from scqos_acs_lab.crypto import sign_envelope, verify_envelope


def test_signature_binds_method_and_session():
    client = ACSClient(process=lambda x: x)
    envelope = client.envelope("steps/toolCallRequest", {"tool": {"name": "lab.write"}, "arguments": {}})
    assert verify_envelope(envelope, client.ikm, client.session_id)
    envelope["method"] = "steps/toolCallResult"
    assert not verify_envelope(envelope, client.ikm, client.session_id)
