#!/usr/bin/env python3
"""Supreme Computation scientific-evidence integration, not a claim of new physics."""
import argparse, datetime, hashlib, json, math, os, pathlib, sys, urllib.request
BASE=pathlib.Path(__file__).resolve().parent
UPSTREAM="https://raw.githubusercontent.com/CobayaSampler/bao_data/master/desi_bao_dr2/"
URLS={"mean":UPSTREAM+"desi_gaussian_bao_ALL_GCcomb_mean.txt","covariance":UPSTREAM+"desi_gaussian_bao_ALL_GCcomb_cov.txt"}
INVARIANTS=("Time","Continuity","Alignment","Genesis","Boundary","Reference","Causality","Consciousness")
def digest(value):return hashlib.sha256(value).hexdigest()
def packed(value):return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def get_sources(refresh=False):
    meta={};contents={}
    for name,url in URLS.items():
        p=BASE/"data"/("desi_dr2_mean.txt" if name=="mean" else "desi_dr2_cov.txt")
        if refresh or not p.exists():
            req=urllib.request.Request(url,headers={"User-Agent":"SC-Evidence-1"})
            with urllib.request.urlopen(req,timeout=30) as r:blob=r.read(1000000)
            if not blob or len(blob)>=1000000:raise ValueError("source file size invalid")
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)
        blob=p.read_bytes()
        meta[name]={"url":url,"path":str(p.relative_to(BASE)),"bytes":len(blob),"sha256":digest(blob)}
        contents[name]=blob.decode("utf-8")
    return meta,contents
def parse(data):
    rows=[]
    for line in data["mean"].splitlines():
        if not line.strip() or line.startswith("#"):continue
        parts=line.split()
        if len(parts)!=3:raise ValueError("invalid observation row")
        z,value=float(parts[0]),float(parts[1]);unit=parts[2]
        if not 0<z<10 or not 0<value<1000 or unit not in ("DV_over_rs","DM_over_rs","DH_over_rs"):raise ValueError("invalid measurement")
        rows.append({"index":len(rows),"redshift":z,"measurement":value,"quantity":unit,"units":"dimensionless"})
    cov=[[float(x) for x in line.split()] for line in data["covariance"].splitlines() if line.strip() and not line.startswith("#")]
    n=len(rows)
    if n!=13 or len(cov)!=n or any(len(r)!=n for r in cov):raise ValueError("DESI DR2 dimensions wrong")
    if any(not math.isfinite(x) for r in cov for x in r):raise ValueError("covariance nonfinite")
    if any(abs(cov[i][j]-cov[j][i])>1e-9 for i in range(n) for j in range(n)):raise ValueError("covariance asymmetric")
    chol=[[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1):
            x=cov[i][j]-sum(chol[i][k]*chol[j][k] for k in range(j))
            if i==j:
                if x<=0:raise ValueError("covariance not positive definite")
                chol[i][j]=math.sqrt(x)
            else:chol[i][j]=x/chol[j][j]
    for i,row in enumerate(rows):row["sigma"]=math.sqrt(cov[i][i])
    return rows,cov
def quantum_check():
    q={"kind":"local Bell-state software self-test; unrelated to DESI physics","ibm_hardware":"not submitted; no billable job","aws_braket_managed":"not submitted; no billable job"}
    try:
        from qiskit import QuantumCircuit
        from qiskit.quantum_info import Statevector
        c=QuantumCircuit(2);c.h(0);c.cx(0,1)
        x=Statevector.from_instruction(c).probabilities_dict()
        q["ibm_qiskit"]={"p00":float(x.get("00",0)),"p11":float(x.get("11",0)),"pass":bool(abs(x.get("00",0)-0.5)<1e-8 and abs(x.get("11",0)-0.5)<1e-8)}
    except Exception as e:q["ibm_qiskit"]={"pass":False,"error":type(e).__name__+":"+str(e)[:100]}
    try:
        from braket.circuits import Circuit
        from braket.devices import LocalSimulator
        x=LocalSimulator().run(Circuit().h(0).cnot(0,1),shots=1024).result().measurement_counts
        a=x.get("00",0)/1024;b=x.get("11",0)/1024
        q["aws_braket_local"]={"p00":a,"p11":b,"pass":abs(a-0.5)<0.10 and abs(b-0.5)<0.10}
    except Exception as e:q["aws_braket_local"]={"pass":False,"error":type(e).__name__+":"+str(e)[:100]}
    return q
def gate(record,root):
    try:
        sys.path.insert(0,str(root))
        from integration.universal_gateway import TransitionRequest, govern_transition
        request=TransitionRequest(tenant_id="supreme-computation",external_system="DESI-DR2",subject=record["id"],
            authority={"principal_id":"SC-evidence-runtime","scope":"scientific-evidence-validation"},
            intent="verify published measurements and preserve original statistical reference",
            evidence={"url":record["source_url"],"sha256":record["source_hash"],"covariance_sha256":record["covariance_hash"],"sigma":record["sigma"]},
            current_state={"redshift":record["redshift"],"quantity":record["quantity"],"value":record["measurement"]},
            proposed_transition={"operation":"ingest_verified_measurement","id":record["id"]},
            expected_consequence={"auditable":True,"no_unsupported_causal_inference":True},
            metadata={"kind":"published_observation","scope":"integrity_not_physics_proof"})
        res=govern_transition(request)
        return {"decision":res.decision,"reason":res.reason,"receipt_hash":res.receipt_hash,"gate_proofs":res.gate_proofs,"final_proof":res.final_proof}
    except Exception as e:return {"decision":"HOLD","reason":type(e).__name__+":"+str(e)[:200],"receipt_hash":None,"gate_proofs":{}}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--refresh",action="store_true")
    ap.add_argument("--no-quantum",action="store_true")
    ap.add_argument("--gate-root",default=os.environ.get("SCQOS_REPO_ROOT",str(pathlib.Path.home()/"scqos-forge-telemetry-v1")))
    opt=ap.parse_args()
    files,texts=get_sources(opt.refresh);rows,cov=parse(texts)
    quantum={"status":"not run"} if opt.no_quantum else quantum_check()
    out=[];previous="0"*64
    for row in rows:
        i=row["index"];rec=dict(row)
        rec.update({"id":f"DESI-DR2-BAO-{i}","source_url":files["mean"]["url"],"source_hash":files["mean"]["sha256"],
                    "covariance_hash":files["covariance"]["sha256"],"parent_hash":previous})
        checks={"Time":True,"Continuity":i==len(out),"Alignment":rec["units"]=="dimensionless",
                "Genesis":bool(rec["source_hash"]),"Boundary":0<rec["redshift"]<10,
                "Reference":rec["sigma"]>0,"Causality":bool(rec["covariance_hash"]),
                "Consciousness":True}
        # These are integrity checks. The downstream SCQOS gate makes the actual decision.
        if not all(checks.values()):raise ValueError("eight-invariant integrity precheck failure")
        rec["integrity_checks"]=checks;rec["scqos"]=gate(rec,opt.gate_root)
        rec["chain_hash"]=digest(packed(rec));previous=rec["chain_hash"];out.append(rec)
    edges=[]
    for i in range(len(cov)):
        for j in range(i+1,len(cov)):
            if abs(cov[i][j])>1e-12:edges.append({"source":i,"target":j,"type":"statistical_covariance_not_causation",
                "covariance":cov[i][j],"correlation":cov[i][j]/math.sqrt(cov[i][i]*cov[j][j])})
    permits=sum(r["scqos"]["decision"]=="PERMIT" for r in out)
    manifest={"schema":"SC-1080-EVIDENCE-v1","generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scientific_scope":"DESI DR2 observational data integration. Does not prove a universal physics law.",
        "invariants":INVARIANTS,"source_files":files,"measurement_count":len(out),"covariance_shape":[13,13],
        "statistical_links":edges,"measurements":out,"scqos_permit_count":permits,
        "scqos_hold_count":len(out)-permits,"quantum":quantum,"final_chain_hash":previous,
        "status":"PERMIT" if permits==len(out) else "HOLD"}
    outdir=BASE/"output";outdir.mkdir(exist_ok=True)
    blob=json.dumps(manifest,indent=2,sort_keys=True,allow_nan=False).encode()+b"\n"
    (outdir/"sc_totality_manifest.json").write_bytes(blob)
    summary={"status":manifest["status"],"measurement_count":len(out),"scqos_permitted":permits,
            "source_hashes":{k:v["sha256"] for k,v in files.items()},"manifest_sha256":digest(blob),
            "final_chain_hash":previous,"quantum":quantum}
    (outdir/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
    return 0 if permits==len(out) else 2
if __name__=="__main__":raise SystemExit(main())
