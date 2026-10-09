"""Independent offline falsification suite for draft Forge synthetic handshake."""
import copy
import datetime as dt
import tempfile
import unittest
import uuid
from pathlib import Path
from integrations.forge_telemetry_v1.adapter import (
    ENGINES, canonical, issue_test_receipt, make_synthetic_payload, sha256, ContractError)
from integrations.forge_telemetry_v1.staging_contract import (
    build_request, verify_request, require_verified_https, SyntheticReceiptStore, ORIGIN)
T = dt.datetime(2026,10,16,15,30,tzinfo=dt.timezone.utc)
KEYS={n: n.encode().ljust(32,b"x") for n in ENGINES}
KEY=b"k"*32
APP="supreme-scqos-staging-01"
NONCE=str(uuid.UUID("b581b126-5e83-4a34-a472-343434343434"))

def fixture():
    payload=make_synthetic_payload(T)
    digest=sha256(canonical(payload["transaction_data"]))
    issue=(T-dt.timedelta(seconds=2)).isoformat()
    commit=(T-dt.timedelta(seconds=1)).isoformat()
    expires=(T+dt.timedelta(seconds=90)).isoformat()
    receipts={n:issue_test_receipt(n,digest,commit if n=="EXECUTION" else issue, expires,KEYS[n]) for n in ENGINES}
    return payload,receipts

class StagingContractTests(unittest.TestCase):
    def setUp(self):
        payload,receipts=fixture()
        self.payload=payload
        self.receipts=receipts
        self.raw,self.headers=build_request(payload,receipts,KEYS,KEY,APP,NONCE,now=T)
    def deny(self,expected,fn,*args,**kw):
        with self.assertRaises(ContractError) as cm:
            fn(*args,**kw)
        self.assertEqual(str(cm.exception),expected)
    def test_signature_and_identity_bound(self):
        parsed=verify_request(self.raw,self.headers,KEY,APP,now=T)
        self.assertEqual(parsed["transaction_id"],NONCE)
        self.assertEqual(parsed["mode"],"SYNTHETIC_ONLY")
    def test_durable_receipt_and_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"receipts.sqlite3"
            store=SyntheticReceiptStore(path)
            receipt=store.accept(self.raw,self.headers,KEY,APP,now=T)
            self.assertEqual(receipt["status"],"VALIDATED_ONLY")
            self.assertFalse(receipt["settlement"])
            self.assertEqual(store.count(),1)
            store.close()
            reopened=SyntheticReceiptStore(path)
            readback=reopened.readback(NONCE)
            self.assertEqual(receipt["canonical_digest"],readback["canonical_digest"])
            self.deny("DUPLICATE_REQUEST_409",reopened.accept,self.raw,self.headers,KEY,APP,now=T)
            self.assertEqual(reopened.count(),1)
            reopened.close()
    def test_wrong_signature_no_write(self):
        with tempfile.TemporaryDirectory() as d:
            s=SyntheticReceiptStore(Path(d)/"r.db")
            self.deny("INVALID_SIGNATURE",s.accept,self.raw+b" ",self.headers,KEY,APP,now=T)
            self.assertEqual(s.count(),0);s.close()
    def test_header_nonce_substitution_rejected(self):
        bad={**self.headers,"X-Forge-Nonce":str(uuid.uuid4())}
        self.deny("NONCE_HEADER_BODY_MISMATCH",verify_request,self.raw,bad,KEY,APP,now=T)
    def test_wrong_app_rejected(self):
        self.deny("APP_ID_MISMATCH",verify_request,self.raw,self.headers,KEY,"other",now=T)
    def test_stale_request_rejected(self):
        self.deny("STALE_OR_FUTURE_EVENT",verify_request,self.raw,self.headers,KEY,APP,now=T+dt.timedelta(seconds=360))
    def test_wrong_key_rejected(self):
        self.deny("INVALID_SIGNATURE",verify_request,self.raw,self.headers,b"x"*32,APP,now=T)
    def test_wrong_contract_schema_rejected(self):
        import hashlib,hmac,json
        decoded=__import__("json").loads(self.raw)
        decoded["mode"]="PRODUCTION"
        raw=canonical(decoded)
        h={**self.headers,"X-Forge-Signature":"hmac-sha256="+hmac.new(KEY,raw,hashlib.sha256).hexdigest()}
        self.deny("WRONG_EXECUTION_BOUNDARY",verify_request,raw,h,KEY,APP,now=T)
    def test_duplicate_json_keys_rejected(self):
        from integrations.forge_telemetry_v1.staging_contract import _parse_raw
        self.deny("DUPLICATE_JSON_KEY",_parse_raw,b'{"nonce":"a","nonce":"b"}')
    def test_endpoint_strict_no_insecure(self):
        require_verified_https(ORIGIN)
        for url in ["http://staging-api.theforge.io/v1/evidence/ingest",
                    "https://34.219.182.104/v1/evidence/ingest",
                    "https://staging-api.theforge.io:3000/v1/evidence/ingest",
                    "https://evil.example/v1/evidence/ingest"]:
            self.deny("UNTRUSTED_ENDPOINT",require_verified_https,url)
    def test_unverified_receipts_cannot_be_signed(self):
        self.deny("RECEIPT_SET_INCOMPLETE",build_request,self.payload,{},KEYS,KEY,APP,NONCE,now=T)
    def test_invalid_nonce_denied(self):
        self.deny("INVALID_NONCE",build_request,self.payload,self.receipts,KEYS,KEY,APP,"123",now=T)

if __name__=="__main__": unittest.main()
