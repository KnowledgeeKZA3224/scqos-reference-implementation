#!/usr/bin/env python3
"""Independently verify a generated release; never rely on a status label alone."""
import copy, hashlib, json, pathlib, sys
BASE=pathlib.Path(__file__).resolve().parent
PIN={"mean":"9ac154ab583ce759c0f7eef3c978c7c70a6ead2d18774caceadf1a350a640585","covariance":"252a143274c8a07c78694c119617d36594f6d7965d00319ca611c6ffb886e509"}
def hash_bytes(data):return hashlib.sha256(data).hexdigest()
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def verify(data,root=BASE):
    assert data["schema"]=="SC-1080-EVIDENCE-v1"
    assert data["measurement_count"]==13 and data["covariance_shape"]==[13,13]
    assert len(data["measurements"])==13
    assert all(data["source_files"][k]["sha256"]==v for k,v in PIN.items())
    for k,expected in PIN.items():
        p=root/data["source_files"][k]["path"]
        assert hash_bytes(p.read_bytes())==expected, f"source file modified: {k}"
    previous="0"*64
    for index,row in enumerate(data["measurements"]):
        assert row["index"]==index and row["parent_hash"]==previous
        assert set(row["integrity_checks"])=={"Time","Continuity","Alignment","Genesis","Boundary","Reference","Causality","Consciousness"}
        assert all(row["integrity_checks"].values())
        assert row["source_hash"]==PIN["mean"] and row["covariance_hash"]==PIN["covariance"]
        assert row["scqos"]["decision"]=="PERMIT"
        assert len(row["scqos"]["gate_proofs"])>=8
        assert row["scqos"]["final_proof"] and row["scqos"]["receipt_hash"]
        value={k:v for k,v in row.items() if k!="chain_hash"}
        assert hash_bytes(canonical(value))==row["chain_hash"], f"broken receipt {index}"
        previous=row["chain_hash"]
    assert previous==data["final_chain_hash"]
    assert data["scqos_permit_count"]==13 and data["scqos_hold_count"]==0 and data["status"]=="PERMIT"
    return True
def main():
    raw=(BASE/"output"/"sc_totality_manifest.json").read_bytes()
    obj=json.loads(raw)
    verify(obj)
    broken=copy.deepcopy(obj);broken["measurements"][0]["measurement"]+=1
    try:verify(broken)
    except AssertionError:tamper_detected=True
    else:tamper_detected=False
    assert tamper_detected,"tampering went undetected"
    print(json.dumps({"validation":"PASS","measurements":13,"tamper_negative_test":"PASS","manifest_sha256":hash_bytes(raw),"final_receipt":obj["final_chain_hash"]},indent=2))
if __name__=="__main__":main()
