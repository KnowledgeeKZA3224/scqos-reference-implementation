"""No-network tests for proposed V3 stable logical action vs unique delivery nonce."""
import copy
import datetime as dt
import hashlib
import hmac
import tempfile
import unittest
import uuid
from pathlib import Path

from integrations.forge_telemetry_v1.adapter import ContractError, canonical
from integrations.forge_telemetry_v1.staging_contract_v3 import (
    CONTRACT, SyntheticV3Store, sign_envelope, verify_signed_envelope)

T = dt.datetime(2026, 10, 9, 23, 50, tzinfo=dt.timezone.utc)
KEY = b"test-only-hmac-key-not-for-production" * 2
APP_ID = "supreme-computation-synthetic"

def sample(decision="PERMIT"):
    return {
        "contract": CONTRACT,
        "mode": "SYNTHETIC_ONLY",
        "transaction_id": "11111111-1111-4111-8111-111111111111",
        "logical_action_sha256": "a" * 64,
        "scenario_id": "22222222-2222-4222-8222-222222222222",
        "transition_id": "33333333-3333-4333-8333-333333333333",
        "attempt_nonce": "44444444-4444-4444-8444-444444444444",
        "timestamp": T.isoformat(),
        "decision": decision,
        "gekyume_precheck_sha256": "b" * 64,
        "scqos_decision_sha256": "c" * 64,
        "observed_effect": "ISOLATED_SYNTHETIC_EFFECT" if decision == "PERMIT" else "NO_PROTECTED_EFFECT",
        "execution_receipt_sha256": "d" * 64 if decision == "PERMIT" else None,
        "observer_receipt_sha256": "e" * 64,
    }

def signed(v=None):
    return sign_envelope(sample() if v is None else v, APP_ID, KEY, now=T)

class V3Tests(unittest.TestCase):
    def reject(self, reason, fn, *args, **kwargs):
        with self.assertRaises(ContractError) as e:
            fn(*args, **kwargs)
        self.assertEqual(str(e.exception), reason)

    def test_stable_logical_tx_separate_from_attempt_nonce(self):
        raw, headers = signed()
        obj = verify_signed_envelope(raw, headers, APP_ID, KEY, now=T)
        self.assertNotEqual(obj["transaction_id"], obj["attempt_nonce"])
        self.assertEqual(obj["logical_action_sha256"], "a" * 64)

    def test_permit_is_validation_not_money(self):
        with tempfile.TemporaryDirectory() as p:
            s = SyntheticV3Store(Path(p) / "test.db")
            raw, headers = signed()
            receipt = s.accept(raw, headers, APP_ID, KEY, now=T)
            self.assertEqual(receipt["status"], "VALIDATED_ONLY")
            self.assertFalse(receipt["settlement"])
            self.assertFalse(receipt["independent_witness_verified"])
            s.close()

    def test_denied_paths_not_forged_exec(self):
        for decision in ("HOLD", "REJECT"):
            with self.subTest(decision=decision), tempfile.TemporaryDirectory() as p:
                s = SyntheticV3Store(Path(p) / "test.db")
                raw, headers = signed(sample(decision))
                got = s.accept(raw, headers, APP_ID, KEY, now=T)
                self.assertEqual(got["status"], "VALIDATED_DENIAL")
                self.assertFalse(got["settlement"])
                self.assertEqual(s.count(), 1)
                s.close()

    def test_denied_execution_receipt_prohibited(self):
        v = sample("HOLD")
        v["execution_receipt_sha256"] = "f" * 64
        self.reject("FABRICATED_DENIED_EXECUTION_RECEIPT", sign_envelope,
                    v, APP_ID, KEY, now=T)

    def test_false_denied_effect_prohibited(self):
        v = sample("REJECT")
        v["observed_effect"] = "ISOLATED_SYNTHETIC_EFFECT"
        self.reject("DENIAL_EFFECT_MISMATCH", sign_envelope,
                    v, APP_ID, KEY, now=T)

    def test_fake_permit_without_execution_digest_prohibited(self):
        v = sample()
        v["execution_receipt_sha256"] = None
        self.reject("INVALID_EXECUTION_RECEIPT_SHA256", sign_envelope,
                    v, APP_ID, KEY, now=T)

    def test_replay_nonce_no_extra_row(self):
        with tempfile.TemporaryDirectory() as p:
            s = SyntheticV3Store(Path(p) / "test.db")
            raw, headers = signed()
            s.accept(raw, headers, APP_ID, KEY, now=T)
            self.reject("REPLAY_NONCE_401", s.accept, raw, headers, APP_ID, KEY, now=T)
            self.assertEqual(s.count(), 1)
            s.close()

    def test_new_nonce_same_tx_rejected(self):
        with tempfile.TemporaryDirectory() as p:
            s = SyntheticV3Store(Path(p) / "test.db")
            raw, headers = signed()
            s.accept(raw, headers, APP_ID, KEY, now=T)
            v = sample()
            v["attempt_nonce"] = "55555555-5555-4555-8555-555555555555"
            retried, new_headers = signed(v)
            self.reject("DUPLICATE_TRANSACTION_409", s.accept, retried, new_headers, APP_ID, KEY, now=T)
            self.assertEqual(s.count(), 1)
            s.close()

    def test_readback_survives_process_restart(self):
        with tempfile.TemporaryDirectory() as p:
            db = Path(p) / "test.db"
            s = SyntheticV3Store(db)
            raw, headers = signed()
            first = s.accept(raw, headers, APP_ID, KEY, now=T)
            s.close()
            s = SyntheticV3Store(db)
            got = s.readback(sample()["transaction_id"])
            self.assertEqual(first["canonical_digest"], got["canonical_digest"])
            self.assertEqual(s.count(), 1)
            self.reject("REPLAY_NONCE_401", s.accept, raw, headers, APP_ID, KEY, now=T)
            s.close()

    def test_wrong_signature_never_persists(self):
        with tempfile.TemporaryDirectory() as p:
            s = SyntheticV3Store(Path(p) / "test.db")
            raw, headers = signed()
            self.reject("INVALID_SIGNATURE", s.accept, raw + b" ", headers, APP_ID, KEY, now=T)
            self.assertEqual(s.count(), 0)
            s.close()

    def test_nonce_header_substitution(self):
        raw, headers = signed()
        bad = {**headers, "X-Forge-Nonce": "66666666-6666-4666-8666-666666666666"}
        self.reject("NONCE_HEADER_BODY_MISMATCH", verify_signed_envelope, raw, bad, APP_ID, KEY, now=T)

    def test_stale_message_rejected(self):
        raw, headers = signed()
        self.reject("STALE_OR_FUTURE_EVENT", verify_signed_envelope, raw, headers, APP_ID, KEY,
                    now=T + dt.timedelta(minutes=6))

    def test_noncanonical_bytes_rejected_even_when_signed(self):
        raw, headers = signed()
        obj = sample()
        # Whitespace produces valid JSON and a matching HMAC but is not canonical.
        modified = b" " + raw
        digest = hmac.new(KEY, modified, hashlib.sha256).hexdigest()
        newheaders = {**headers, "X-Forge-Signature": "hmac-sha256=" + digest}
        self.reject("NONCANONICAL_BYTES", verify_signed_envelope,
                    modified, newheaders, APP_ID, KEY, now=T)

    def test_duplicate_json_keys_rejected_even_when_signed(self):
        raw, headers = signed()
        modified = raw[:-1] + b', "decision":"PERMIT"}'
        digest = hmac.new(KEY, modified, hashlib.sha256).hexdigest()
        newheaders = {**headers, "X-Forge-Signature": "hmac-sha256=" + digest}
        self.reject("DUPLICATE_JSON_KEY", verify_signed_envelope,
                    modified, newheaders, APP_ID, KEY, now=T)

    def test_same_uuid_for_nonce_tx_rejected(self):
        v = sample()
        v["attempt_nonce"] = v["transaction_id"]
        self.reject("TRANSACTION_NONCE_NOT_SEPARATE", sign_envelope, v, APP_ID, KEY, now=T)

if __name__ == "__main__":
    unittest.main()
