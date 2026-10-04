from scqos_acs_lab.client import ACSClient
from scqos_acs_lab.guardian import SCQOSGuardian
from scqos_acs_lab.harness import run_suite, meta_test


def test_full_direct_suite_passes():
    guardian = SCQOSGuardian(live_scqos=False)
    rows = run_suite(ACSClient(process=guardian.process))
    failed = [(row.name, row.observed, row.detail) for row in rows if not row.passed]
    assert not failed, failed


def test_harness_detects_all_deliberate_mutants():
    result = meta_test()
    assert result["all_detected"] is True
    names = {m["mutant"] for m in result["mutants"] if m["detected"]}
    assert names == {"allow-everything", "deny-everything", "signature-blind", "replay-blind", "fake-success-adapter", "skipped-test-runner"}


def test_wrong_version_refused():
    guardian = SCQOSGuardian(live_scqos=False)
    client = ACSClient(process=guardian.process)
    response = client.handshake(versions=["9.9.9"])
    assert response["error"]["code"] == -32001
