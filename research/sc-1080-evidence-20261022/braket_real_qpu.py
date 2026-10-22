#!/usr/bin/env python3
"""One bounded, real AWS Braket QPU experiment with SCQOS authorization and receipts."""
import sys, json, hashlib, datetime, os, pathlib, time
from braket.aws import AwsDevice
from braket.circuits import Circuit
from integration.universal_gateway import TransitionRequest, govern_transition
ROOT=pathlib.Path(__file__).resolve().parent
OUTPUT=ROOT/"output";OUTPUT.mkdir(exist_ok=True)
BUCKET="amazon-braket-us-west-1-327453383912"
DEVICE="arn:aws:braket:us-west-1::device/qpu/rigetti/Cepheus-1-108Q"
SHOTS=256
MAX_APPROX_QPU_USD=0.50
APPROX=0.30 + SHOTS*0.000425
assert APPROX<=MAX_APPROX_QPU_USD
request=TransitionRequest(tenant_id="supreme-computation",external_system="amazon-braket-real-qpu",
 subject="rigetti-cephus-bell256",
 authority={"principal_id":"Supreme-Computation-operator","scope":"requested-quantum-hardware-execution"},
 intent="execute at most one bounded real QPU Bell-state verification",
 evidence={"device_arn":DEVICE,"source":"AWS Braket pricing","max_estimated_hardware_usd":MAX_APPROX_QPU_USD},
 current_state={"shots":0,"task_submitted":False},
 proposed_transition={"shots":SHOTS,"device_arn":DEVICE,"estimated_usd":APPROX},
 expected_consequence={"measurement_counts":True,"quantum_task_arn":True,"receipt_required":True},
 metadata={"purpose":"quantum-hardware self-check; not evidence for cosmic law"})
gate=govern_transition(request)
if gate.decision!="PERMIT":raise RuntimeError("SCQOS denied hardware task: "+gate.reason)
print("SCQOS_QPU_PERMIT",gate.receipt_hash,flush=True)
device=AwsDevice(DEVICE)
task=device.run(Circuit().h(0).cnot(0,1),s3_destination_folder=(BUCKET,"sc-1080/20261022/rigetti-physical"),shots=SHOTS,poll_timeout_seconds=180)
record={"type":"REAL_QPU","provider":"Rigetti via Amazon Braket","device_arn":DEVICE,
"qpu_task_arn":task.id,"shots":SHOTS,"estimated_qpu_usd":APPROX,
"scqos_pre_execution_receipt":gate.receipt_hash,
"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"state":"SUBMITTED"}
dest=OUTPUT/"aws_braket_hardware_job.json"
dest.write_text(json.dumps(record,indent=2)+"\n")
print("AWS_QPU_TASK",task.id,flush=True)
try:
 result=task.result()
 if result is None:raise RuntimeError("Task did not produce a result before polling timeout")
 counts=dict(result.measurement_counts)
 total=sum(counts.values())
 ratio=(counts.get("00",0)+counts.get("11",0))/total if total else 0
 record.update({"state":"COMPLETED","counts":counts,"shots_measured":total,
 "correlated_fraction":ratio,"hardware_check_pass":bool(total==SHOTS and ratio>=0.7),
 "completed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()})
except Exception as exc:
 record.update({"state":"NOT_COMPLETE","error":type(exc).__name__+":"+str(exc)[:260]})
body=json.dumps(record,sort_keys=True,separators=(",",":")).encode()
record["result_sha256"]=hashlib.sha256(body).hexdigest()
dest.write_text(json.dumps(record,indent=2)+"\n")
print("AWS_QPU_RESULT",json.dumps(record),flush=True)
sys.exit(0 if record.get("hardware_check_pass") else 2)
