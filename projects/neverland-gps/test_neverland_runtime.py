import unittest

from neverland_runtime import Context, Decision, SafetyState, evaluate, offline_capabilities


class NeverlandRuntimeTests(unittest.TestCase):
    def base(self, **overrides):
        data = dict(
            device_id="NL-DEMO-001",
            safety_state=SafetyState.SAFE,
            gnss_fresh=True,
            guardian_present=True,
            wifi_available=False,
        )
        data.update(overrides)
        return Context(**data)

    def test_wifi_is_not_required_for_core_capabilities(self):
        caps = offline_capabilities(self.base(wifi_available=False))
        self.assertIn("scqos_governance", caps)
        self.assertIn("gnss_position", caps)
        self.assertNotIn("wifi", caps)

    def test_lost_child_enters_guardian_state_offline(self):
        t = evaluate(self.base(child_says_lost=True, guardian_present=False), "observe")
        self.assertEqual(t.decision, Decision.PERMIT)
        self.assertEqual(t.next_state, SafetyState.GUARDIAN)

    def test_guidance_requires_verified_destination(self):
        t = evaluate(self.base(child_says_lost=True, guardian_present=False), "guide")
        self.assertEqual(t.decision, Decision.HOLD)

    def test_verified_offline_guidance_permitted(self):
        t = evaluate(
            self.base(child_says_lost=True, guardian_present=False, trusted_safe_destination=True),
            "guide",
        )
        self.assertEqual(t.decision, Decision.PERMIT)

    def test_unauthorized_location_release_rejected(self):
        t = evaluate(
            self.base(sos_pressed=True, guardian_present=False, direct_radio_link=True),
            "share_location",
        )
        self.assertEqual(t.decision, Decision.REJECT)

    def test_authorized_emergency_release_without_wifi(self):
        t = evaluate(
            self.base(
                sos_pressed=True,
                guardian_present=False,
                recipient_authorized=True,
                direct_radio_link=True,
                wifi_available=False,
            ),
            "share_location",
        )
        self.assertEqual(t.decision, Decision.PERMIT)

    def test_no_link_holds_but_guardian_stays_alive(self):
        t = evaluate(
            self.base(sos_pressed=True, guardian_present=False, recipient_authorized=True),
            "share_location",
        )
        self.assertEqual(t.decision, Decision.HOLD)
        self.assertEqual(t.next_state, SafetyState.GUARDIAN)

    def test_stale_location_holds(self):
        t = evaluate(
            self.base(
                sos_pressed=True,
                guardian_present=False,
                recipient_authorized=True,
                direct_radio_link=True,
                gnss_fresh=False,
            ),
            "share_location",
        )
        self.assertEqual(t.decision, Decision.HOLD)

    def test_tamper_fails_closed(self):
        t = evaluate(
            self.base(
                sos_pressed=True,
                guardian_present=False,
                tamper_detected=True,
                recipient_authorized=True,
                direct_radio_link=True,
            ),
            "share_location",
        )
        self.assertEqual(t.decision, Decision.REJECT)

    def test_receipts_are_deterministic(self):
        ctx = self.base(sos_pressed=True, guardian_present=False)
        self.assertEqual(evaluate(ctx, "observe").receipt_hash, evaluate(ctx, "observe").receipt_hash)


if __name__ == "__main__":
    unittest.main()
