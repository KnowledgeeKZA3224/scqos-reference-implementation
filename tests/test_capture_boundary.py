import unittest
from datetime import datetime, timedelta, timezone

from scqos_capture import (authority_decision, blast_radius, compare_shadow,
                           freeze_intent, precommit_decision, witness_effect)
from scqos_capture.boundary import _digest


NOW = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)


class CaptureBoundaryTests(unittest.TestCase):
    def grants(self):
        start = (NOW - timedelta(hours=1)).isoformat()
        end = (NOW + timedelta(hours=1)).isoformat()
        return [
            {"id": "root", "parent_id": None, "root_trusted": True,
             "subject": "human", "actions": ["capture", "review"],
             "not_before": start, "expires_at": end},
            {"id": "worker", "parent_id": "root", "issuer": "human",
             "subject": "capture-worker", "actions": ["capture"],
             "not_before": start, "expires_at": end},
        ]

    def intent(self):
        authority = authority_decision(self.grants(), action="capture",
                                       subject="capture-worker", now=NOW)
        self.assertEqual(authority["state"], "PERMIT")
        state = {"receipt": "r1", "status": "HOLD"}
        intent = freeze_intent(transition_id="T1", target="receipts/r1",
                               prior_hash=_digest(None), proposed_state=state,
                               evidence_hash="e1", authority_hash=authority["authority_hash"],
                               policy_hash="p1", expires_at=(NOW + timedelta(minutes=1)).isoformat())
        return intent, state, authority

    def test_revoked_parent_stale_grant_and_broadened_child_hold(self):
        grants = self.grants()
        self.assertEqual(authority_decision(grants, action="capture", subject="capture-worker",
                                            now=NOW, revoked_ids={"root"})["state"], "HOLD")
        grants[1]["expires_at"] = (NOW - timedelta(seconds=1)).isoformat()
        self.assertEqual(authority_decision(grants, action="capture", subject="capture-worker",
                                            now=NOW)["state"], "HOLD")
        grants = self.grants()
        grants[1]["actions"].append("delete")
        self.assertEqual(authority_decision(grants, action="capture", subject="capture-worker",
                                            now=NOW)["state"], "HOLD")

    def test_frozen_intent_detects_changed_state_authority_and_prior_version(self):
        intent, state, authority = self.intent()
        common = dict(current_hash=_digest(None), proposed_state=state,
                      authority_hash=authority["authority_hash"], evidence_hash="e1",
                      policy_hash="p1", now=NOW)
        self.assertEqual(precommit_decision(intent, **common)["state"], "PERMIT")
        for changed in ({"proposed_state": {"receipt": "r1", "status": "PERMIT"}},
                        {"authority_hash": "revoked"}, {"current_hash": "competing-writer"},
                        {"policy_hash": "p2"}, {"evidence_hash": "stale"}):
            self.assertEqual(precommit_decision(intent, **(common | changed))["state"], "HOLD")
        self.assertEqual(precommit_decision(intent, **(common | {"now": NOW + timedelta(minutes=2)}))["state"], "HOLD")

    def test_witness_requires_exact_readback_and_committed_identity(self):
        intent, state, _ = self.intent()
        success = witness_effect(intent, read_back=lambda _: state,
                                 committed_transition_id="T1",
                                 committed_intent_hash=intent["intent_hash"])
        self.assertEqual(success["state"], "PERMIT")
        self.assertIn("witness_hash", success)
        self.assertEqual(witness_effect(intent, read_back=lambda _: {"status": "wrong"},
                                        committed_transition_id="T1",
                                        committed_intent_hash=intent["intent_hash"])["state"], "HOLD")
        self.assertEqual(witness_effect(intent, read_back=lambda _: state,
                                        committed_transition_id="T2",
                                        committed_intent_hash=intent["intent_hash"])["state"], "HOLD")

    def test_shadow_reports_counterfactual_without_promotion(self):
        baseline = {"case-a": "HOLD", "case-b": "PERMIT"}
        result = compare_shadow(candidate_id="lesson-1", baseline=baseline,
                                simulate=lambda _: {"case-a": "PERMIT", "case-b": "PERMIT"})
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["changes"], {"case-a": {"baseline": "HOLD", "candidate": "PERMIT"}})
        self.assertEqual(compare_shadow(candidate_id="lesson-1", baseline=baseline,
                                        simulate=lambda _: {"case-a": "PERMIT"})["state"], "HOLD")

    def test_reversal_finds_indirect_consequences_with_cycle(self):
        result = blast_radius("T1", {"T1": ["cache", "message"], "cache": ["payment"],
                                     "payment": ["T1", "external-api"]})
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(set(result["descendants"]), {"cache", "message", "payment", "external-api"})
        self.assertTrue(all(v == "UNRESOLVED" for v in result["required_dispositions"].values()))


if __name__ == "__main__":
    unittest.main()
