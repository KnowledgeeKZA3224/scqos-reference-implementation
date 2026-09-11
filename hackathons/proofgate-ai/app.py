import json, os, hashlib, base64, datetime
import boto3
from strands import Agent, tool
from strands.models import BedrockModel

REGION=os.environ.get("AWS_REGION","us-east-1")
TABLE=os.environ["RECEIPT_TABLE"]
KMS_KEY=os.environ["KMS_KEY_ID"]
MODEL_ID=os.environ.get("MODEL_ID","us.amazon.nova-pro-v1:0")
ddb=boto3.client("dynamodb",region_name=REGION)
kms=boto3.client("kms",region_name=REGION)
_last_gate=None

SCENARIOS={
 "permit":{"goal":"Publish a verified status update after all evidence is current and authority is valid.","age":12,"max_age":300,"authority":True,"contradiction":False,"route":"healthy","alternate":False},
 "hold":{"goal":"Execute a cloud action using evidence that has gone stale.","age":1800,"max_age":300,"authority":True,"contradiction":False,"route":"healthy","alternate":False},
 "reject":{"goal":"Change a protected production state without valid authority.","age":20,"max_age":300,"authority":False,"contradiction":False,"route":"healthy","alternate":False},
 "reroute":{"goal":"Complete an approved task while the preferred execution route is degraded.","age":18,"max_age":300,"authority":True,"contradiction":False,"route":"degraded","alternate":True}
}

def evaluate(s):
    checks={
      "time":s["age"]<=s["max_age"],
      "continuity":True,
      "alignment":True,
      "genesis":bool(s.get("goal")),
      "boundary":bool(s["authority"]),
      "reference":not bool(s["contradiction"]),
      "causality":True,
      "accountability":True
    }
    if not checks["boundary"]:
        verdict,reason="REJECT","authority boundary failed"
    elif not checks["time"] or not checks["reference"]:
        verdict,reason="HOLD","evidence/reference is stale or contradictory"
    elif s["route"]!="healthy" and s["alternate"]:
        verdict,reason="REROUTE","primary route degraded; bounded alternate available"
    elif all(checks.values()):
        verdict,reason="PERMIT","all required checks passed"
    else:
        verdict,reason="HOLD","proof incomplete"
    return {"verdict":verdict,"reason":reason,"checks":checks,"route":"alternate" if verdict=="REROUTE" else "primary"}

@tool
def proofgate_assess(scenario: str) -> str:
    '''Evaluate one bounded ProofGate transition.'''
    global _last_gate
    key=scenario.lower().strip()
    _last_gate=evaluate(SCENARIOS[key]) if key in SCENARIOS else {"verdict":"HOLD","reason":"unknown scenario","checks":{},"route":"none"}
    return json.dumps(_last_gate,sort_keys=True)

model=BedrockModel(model_id=MODEL_ID,region_name=REGION,temperature=0)
agent=Agent(model=model,tools=[proofgate_assess],callback_handler=None,system_prompt="You are ProofGate AI. You MUST call proofgate_assess exactly once before giving any verdict. Never invent a verdict.")

def response(code,obj):
    return {"statusCode":code,"headers":{"content-type":"application/json","cache-control":"no-store"},"body":json.dumps(obj,indent=2)}

def run_scenario(scenario):
    global _last_gate
    if scenario not in SCENARIOS:
        return 400,{"error":"scenario must be permit, hold, reject, or reroute"}
    day=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    rid=f"proofgate#{day}#{scenario}"
    cached=ddb.get_item(TableName=TABLE,Key={"receipt_id":{"S":rid}}).get("Item")
    if cached and "payload" in cached:
        out=json.loads(cached["payload"]["S"])
        out["cached"]=True
        return 200,out
    _last_gate=None
    prompt=f'Run scenario "{scenario}". Call proofgate_assess with scenario="{scenario}" first. Then explain the tool verdict in one short sentence.'
    agent_error=None
    try:
        agent_text=str(agent(prompt))
    except Exception as e:
        agent_text=""
        agent_error=type(e).__name__+": "+str(e)
    gate=_last_gate or {"verdict":"HOLD","reason":"Strands agent failed to call the governance tool","checks":{},"route":"none"}
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    core={
      "project":"ProofGate AI",
      "hackathon":"Agents for Humans 2026",
      "scenario":scenario,
      "goal":SCENARIOS[scenario]["goal"],
      "verdict":gate["verdict"],
      "reason":gate["reason"],
      "checks":gate["checks"],
      "route":gate["route"],
      "consequence_confirmed":gate["verdict"] in ("PERMIT","REROUTE"),
      "strands_tool_called":_last_gate is not None,
      "strands_sdk":True,
      "model_id":MODEL_ID,
      "timestamp":now,
      "agent_summary":agent_text[:1200],
      "agent_error":agent_error
    }
    canonical=json.dumps(core,sort_keys=True,separators=(",",":")).encode()
    digest=hashlib.sha256(canonical).hexdigest()
    sig=kms.sign(KeyId=KMS_KEY,Message=bytes.fromhex(digest),MessageType="DIGEST",SigningAlgorithm="ECDSA_SHA_256")
    core["receipt_sha256"]=digest
    core["kms_key_id"]=sig["KeyId"]
    core["kms_signing_algorithm"]="ECDSA_SHA_256"
    core["kms_signature_b64"]=base64.b64encode(sig["Signature"]).decode()
    core["cached"]=False
    ddb.put_item(TableName=TABLE,Item={"receipt_id":{"S":rid},"payload":{"S":json.dumps(core,sort_keys=True)},"verdict":{"S":gate["verdict"]},"created_at":{"S":now}})
    return 200,core

def lambda_handler(event, context):
    q=event.get("queryStringParameters") or {}
    scenario=str(q.get("scenario","")).lower().strip()
    if scenario:
        code,obj=run_scenario(scenario)
        return response(code,obj)
    if q.get("public_key")=="1":
        pk=kms.get_public_key(KeyId=KMS_KEY)
        return response(200,{"signing_algorithm":"ECDSA_SHA_256","public_key_der_b64":base64.b64encode(pk["PublicKey"]).decode()})
    return response(200,{
      "project":"ProofGate AI",
      "message":"Choose a live scenario with ?scenario=permit, ?scenario=hold, ?scenario=reject, or ?scenario=reroute",
      "stack":["AWS Lambda","Amazon Bedrock","Strands Agents SDK","DynamoDB","AWS KMS"],
      "principle":"The agent may propose. ProofGate decides whether consequence is allowed to bind."
    })
