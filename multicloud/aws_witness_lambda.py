import os,json,hashlib,datetime,urllib.request,boto3

CONTRACT_ID="SCQOS-MULTICLOUD-CONTINUITY-v1"
CONTRACT_SHA=os.environ["SCQOS_CONTRACT_SHA256"]
AZURE_HEALTH_URL=os.environ["AZURE_HEALTH_URL"]
BUCKET=os.environ["EVIDENCE_BUCKET"]
s3=boto3.client("s3")

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(",",":"))
def response(code,body): return {"statusCode":code,"headers":{"content-type":"application/json"},"body":json.dumps(body,separators=(",",":"))}

def lambda_handler(event,context):
    # Function URL is deliberately read-only: it exposes only continuity health.
    if isinstance(event,dict) and "requestContext" in event:
        return response(200,{"status":"ONLINE","cloud":"AWS","contract_id":CONTRACT_ID,"contract_sha256":CONTRACT_SHA,"rule":"Nothing executes until it proves itself."})
    observed={"status":"HOLD"}
    error=None
    try:
        with urllib.request.urlopen(AZURE_HEALTH_URL,timeout=10) as r:
            observed=json.loads(r.read().decode())
    except Exception as e:
        error=f"{type(e).__name__}:{e}"
    permit=(observed.get("status")=="ONLINE" and observed.get("contract_id")=="SCQOS-UNIVERSAL-TRANSITION-v1")
    receipt={"contract_id":CONTRACT_ID,"contract_sha256":CONTRACT_SHA,"observer":"AWS","observed_cloud":"Azure","observed_at":now(),"decision":"PERMIT" if permit else "HOLD","azure_health":observed}
    if error: receipt["error"]=error
    receipt["receipt_sha256"]=hashlib.sha256(canonical(receipt).encode()).hexdigest()
    stamp=receipt["observed_at"].replace(":","-")
    body=(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode()
    key=f"multicloud/witness/aws/{stamp}-{receipt[receipt_sha256]}.json"
    s3.put_object(Bucket=BUCKET,Key=key,Body=body,ContentType="application/json")
    s3.put_object(Bucket=BUCKET,Key="multicloud/witness/aws/LATEST.json",Body=body,ContentType="application/json")
    return {"decision":receipt["decision"],"receipt_sha256":receipt["receipt_sha256"]}
