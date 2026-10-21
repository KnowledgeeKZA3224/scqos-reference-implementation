import copy
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from integrations.forge_telemetry_v1.adapter import (
    ContractError, ENGINES, TENANT_ID, canonical, issue_test_receipt, mac,
    make_forge_request, make_synthetic_payload, sha256,
    validate_payload, verify_forge_request, verify_receipts)
from integrations.forge_telemetry_v1.outbox import Outbox

T = dt.datetime(2026, 10, 16, 15, 30, tzinfo=dt.timezone.utc)
KEYS = {"GEKYUME": b"G"*32, "SCQOS": b"S"*32, "EXECUTION": b"E"*32}
FORGE_KEY = b"F"*32

def proofs(payload, *, now=T):
    digest = sha256(canonical(payload["transaction_data"]))
    before = (now-dt.timedelta(seconds=2)).isoformat()
    after = (now+dt.timedelta(seconds=60)).isoformat()
    execution_at = (now-dt.timedelta(seconds=1)).isoformat()
    return {engine: issue_test_receipt(engine, digest,
               execution_at if engine=="EXECUTION" else before,
               after, KEYS[engine]) for engine in ENGINES}

class ForgeContractTests(unittest.TestCase):
    def setUp(self):
        self.payload = make_synthetic_payload(T)
        self.receipts = proofs(self.payload)
    def assertDenied(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as cm: function(*args, **kwargs)
        self.assertEqual(str(cm.exception), code)
    def test_valid_contract_and_signature_roundtrip(self):
        body, headers = make_forge_request(self.payload, self.receipts, KEYS, FORGE_KEY, now=T)
        self.assertEqual(headers["X-Forge-Tenant-ID"], TENANT_ID)
        self.assertEqual(headers["X-Signature-HMAC-256"], mac(FORGE_KEY, body))
        self.assertEqual(verify_forge_request(body, headers, FORGE_KEY, now=T), self.payload)
    def test_hmac_rejects_tampering(self):
        body, headers = make_forge_request(self.payload, self.receipts, KEYS, FORGE_KEY, now=T)
        changed = body.replace(b"1250.0", b"2250.0")
        self.assertNotEqual(changed, body)
        self.assertDenied("FORGE_HMAC_MISMATCH", verify_forge_request, changed, headers, FORGE_KEY, now=T)
    def test_different_tenant_rejected(self):
        body, headers = make_forge_request(self.payload, self.receipts, KEYS, FORGE_KEY, now=T)
        self.assertDenied("TENANT_MISMATCH", verify_forge_request, body,
                          {**headers,"X-Forge-Tenant-ID":"UNKNOWN"}, FORGE_KEY, now=T)
    def test_unauthorized_state_rejected(self):
        p=copy.deepcopy(self.payload);p["scqos_evaluation"]["authority_state"]="DENIED"
        self.assertDenied("SCQOS_NOT_AUTHORIZED", validate_payload, p, now=T)
    def test_gekyume_false_rejected(self):
        p=copy.deepcopy(self.payload);p["gekyume_validation"]["policy_check_passed"]=False
        self.assertDenied("GEKYUME_NOT_PERMITTED", validate_payload, p, now=T)
    def test_mismatched_transaction_denied(self):
        p=copy.deepcopy(self.payload);p["transaction_data"]["amount"]=1500
        self.assertDenied("TRANSACTION_BINDING_MISMATCH", verify_receipts, p, self.receipts, KEYS, now=T)
    def test_fake_approval_signature_denied(self):
        r=copy.deepcopy(self.receipts);r["SCQOS"]["signature"]="0"*64
        self.assertDenied("PROOF_NOT_AUTHENTIC", verify_receipts, self.payload, r, KEYS, now=T)
    def test_receipts_missing_denied(self):
        r=copy.deepcopy(self.receipts);del r["SCQOS"]
        self.assertDenied("RECEIPT_SET_INCOMPLETE", verify_receipts, self.payload, r, KEYS, now=T)
    def test_expired_receipts_denied(self):
        self.assertDenied("PROOF_EXPIRED", verify_receipts, self.payload, self.receipts, KEYS,
                          now=T+dt.timedelta(seconds=120))
    def test_stale_payload_denied(self):
        self.assertDenied("STALE_OR_FUTURE_EVENT", validate_payload, self.payload,
                          now=T+dt.timedelta(seconds=360))
    def test_unauthenticated_claim_is_not_sufficient(self):
        self.assertDenied("RECEIPT_SET_INCOMPLETE", make_forge_request,
                          self.payload, {}, KEYS, FORGE_KEY, now=T)
    def test_amount_bounds_and_nan(self):
        for amount in [-1, 0, 12.345, float("nan"), float("inf"), True]:
            p=copy.deepcopy(self.payload);p["transaction_data"]["amount"]=amount
            with self.assertRaises(ContractError): validate_payload(p, now=T)
    def test_unknown_fields_denied(self):
        p=copy.deepcopy(self.payload);p["transaction_data"]["secret"]="exfiltration"
        self.assertDenied("TRANSACTION_SCHEMA", validate_payload, p, now=T)
    def test_missing_executed_receipt_denied(self):
        r=copy.deepcopy(self.receipts);del r["EXECUTION"]
        self.assertDenied("RECEIPT_SET_INCOMPLETE", verify_receipts, self.payload, r, KEYS, now=T)
    def test_no_replay_in_local_outbox(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Outbox(Path(folder)/"outbox.sqlite");raw=canonical(self.payload)
            digest=out.reserve(self.payload["telemetry_id"], raw)
            self.assertDenied("DUPLICATE_OR_UNKNOWN_DELIVERY", out.reserve, self.payload["telemetry_id"], raw)
            out.mark_acknowledged(self.payload["telemetry_id"],digest,b'{"ok":true}')
            self.assertEqual(out.state(self.payload["telemetry_id"])[0],"ACKED")
            self.assertDenied("ACKNOWLEDGMENT_STATE_MISMATCH",out.mark_acknowledged,self.payload["telemetry_id"],digest,b'ok')
            out.close()
    def test_uncertain_delivery_is_not_auto_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Outbox(Path(folder)/"outbox.sqlite")
            digest=out.reserve(self.payload["telemetry_id"], canonical(self.payload))
            out.mark_uncertain(self.payload["telemetry_id"],digest)
            self.assertEqual(out.state(self.payload["telemetry_id"])[0],"UNCERTAIN")
            self.assertDenied("DUPLICATE_OR_UNKNOWN_DELIVERY",out.reserve,
                             self.payload["telemetry_id"],canonical(self.payload))
            out.close()
    def test_ordering_of_execution_and_gates(self):
        r=copy.deepcopy(self.receipts)
        r["EXECUTION"]=issue_test_receipt("EXECUTION",sha256(canonical(self.payload["transaction_data"])),
            (T-dt.timedelta(seconds=5)).isoformat(),(T+dt.timedelta(seconds=10)).isoformat(),KEYS["EXECUTION"])
        self.assertDenied("EXECUTION_PRECEDES_AUTHORITY",verify_receipts,self.payload,r,KEYS,now=T)

if __name__=="__main__": unittest.main()
