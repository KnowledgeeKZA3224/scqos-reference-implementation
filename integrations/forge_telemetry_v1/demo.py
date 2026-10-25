"""Offline test fixture; never generates real payment authorization."""
import datetime as dt
import json
from .adapter import (ENGINES, canonical, issue_test_receipt,
                      make_forge_request, make_synthetic_payload,
                      sha256, verify_forge_request)
if __name__ == "__main__":
    now=dt.datetime.now(dt.timezone.utc)
    payload=make_synthetic_payload(now)
    digest=sha256(canonical(payload["transaction_data"]))
    keys={"GEKYUME":b"G"*32,"SCQOS":b"S"*32,"EXECUTION":b"E"*32}
    issued=(now-dt.timedelta(seconds=1)).isoformat()
    expires=(now+dt.timedelta(seconds=120)).isoformat()
    proofs={n:issue_test_receipt(n,digest,issued,expires,keys[n]) for n in ENGINES}
    body,headers=make_forge_request(payload,proofs,keys,b"F"*32,now=now)
    verified=verify_forge_request(body,headers,b"F"*32,now=now)
    print(json.dumps({"mode":"SYNTHETIC_ONLY","contract":"SPEC-WA-TELEMETRY-V1",
                      "status":"LOCAL_CONTRACT_VERIFIED",
                      "telemetry_id":verified["telemetry_id"],
                      "body_sha256":sha256(body),
                      "tenant":headers["X-Forge-Tenant-ID"],
                      "payment_executed":False,
                      "external_network_calls":0},indent=2))
