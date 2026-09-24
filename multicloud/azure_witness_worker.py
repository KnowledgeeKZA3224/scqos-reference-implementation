import os,json,hashlib,datetime,urllib.request
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient,ContentSettings

CONTRACT_ID="SCQOS-MULTICLOUD-CONTINUITY-v1"
CONTRACT_SHA=os.environ["SCQOS_CONTRACT_SHA256"]
AWS_URL=os.environ["AWS_WITNESS_URL"]
ACCOUNT=os.environ["AZURE_STORAGE_ACCOUNT"]
CONTAINER=os.environ.get("AZURE_EVIDENCE_CONTAINER","evidence")
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(",",":"))
observed={"status":"HOLD"}; error=None
try:
    with urllib.request.urlopen(AWS_URL,timeout=10) as r: observed=json.loads(r.read().decode())
except Exception as e: error=f"{type(e).__name__}:{e}"
permit=(observed.get("status")=="ONLINE" and observed.get("cloud")=="AWS" and observed.get("contract_id")==CONTRACT_ID and observed.get("contract_sha256")==CONTRACT_SHA)
receipt={"contract_id":CONTRACT_ID,"contract_sha256":CONTRACT_SHA,"observer":"Azure","observed_cloud":"AWS","observed_at":now(),"decision":"PERMIT" if permit else "HOLD","aws_health":observed}
if error: receipt["error"]=error
receipt["receipt_sha256"]=hashlib.sha256(canonical(receipt).encode()).hexdigest()
body=(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode()
cred=DefaultAzureCredential()
svc=BlobServiceClient(account_url=f"https://{ACCOUNT}.blob.core.windows.net",credential=cred)
stamp=receipt["observed_at"].replace(":","-")
for name in [f"multicloud/witness/azure/{stamp}-{receipt[receipt_sha256]}.json","multicloud/witness/azure/LATEST.json"]:
    svc.get_blob_client(CONTAINER,name).upload_blob(body,overwrite=True,content_settings=ContentSettings(content_type="application/json"))
print(json.dumps({"decision":receipt["decision"],"receipt_sha256":receipt["receipt_sha256"]}))
raise SystemExit(0 if permit else 12)
