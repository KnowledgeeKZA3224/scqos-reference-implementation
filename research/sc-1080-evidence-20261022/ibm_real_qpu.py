#!/usr/bin/env python3
"""Small measured Bell-pair experiment on actual IBM Quantum hardware."""
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from datetime import datetime, timezone
from pathlib import Path
import json, hashlib, sys
OUT=Path(__file__).resolve().parent/"output"
OUT.mkdir(exist_ok=True)
service=QiskitRuntimeService(name="scqos")
devices=service.backends(simulator=False,operational=True)
if not devices:raise RuntimeError("No operational IBM hardware")
backend=sorted(devices,key=lambda b:b.status().pending_jobs)[0]
print("REAL_QPU:",backend.name,flush=True)
circuit=QuantumCircuit(2,2)
circuit.h(0)
circuit.cx(0,1)
circuit.measure([0,1],[0,1])
physical=transpile(circuit,backend=backend,optimization_level=1)
sampler=SamplerV2(mode=backend)
job=sampler.run([physical],shots=128)
job_id=job.job_id()
record={"hardware_provider":"IBM Quantum","backend":backend.name,"hardware_qpu":True,
"job_id":job_id,"shots_requested":128,"submitted_utc":datetime.now(timezone.utc).isoformat(),
"circuit_qasm_description":"H q0; CX q0,q1; measure q0,q1. Bell state hardware sanity check, not a cosmology prediction.",
"status":"SUBMITTED"}
(OUT/"ibm_quantum_hardware_job.json").write_text(json.dumps(record,indent=2)+"\n")
print("REAL_HARDWARE_JOB_ID:",job_id,flush=True)
result=job.result()
counts=result[0].data.c.get_counts()
record["counts"]=counts
record["status"]="COMPLETED"
record["finished_utc"]=datetime.now(timezone.utc).isoformat()
record["shots_measured"]=sum(counts.values())
record["correlated_fraction"]=(counts.get("00",0)+counts.get("11",0))/record["shots_measured"]
record["hardware_check_pass"]=bool(record["shots_measured"]==128 and record["correlated_fraction"]>=0.80)
body=json.dumps(record,sort_keys=True,separators=(",",":")).encode()
record["result_sha256"]=hashlib.sha256(body).hexdigest()
(OUT/"ibm_quantum_hardware_job.json").write_text(json.dumps(record,indent=2)+"\n")
print("HARDWARE_RESULT:",json.dumps(record),flush=True)
sys.exit(0 if record["hardware_check_pass"] else 2)
