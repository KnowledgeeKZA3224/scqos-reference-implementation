import json,datetime,hashlib,pathlib,sys
from shadow_clone.protocol import make_clone_birth,evaluate_clone_birth
m=json.load(open("supreme_mind/v1/supreme_mind_manifest.json"))
roles=m["roles"]; ids=[r["role_id"] for r in roles]
now=datetime.datetime.now(datetime.timezone.utc)
objective="Prepare and verify Mark Supreme Mail Microsoft 365 readiness across AWS and Azure without contacting Mark or sending mail."
receipts=[]
for r in roles:
    role_id=r["role_id"]
    p=make_clone_birth(role_id=role_id,task_id=f"mark-ms-readiness-{role_id}",business_id="mark-supreme-mail",objective=objective,expected_output=f"{r['name']} bounded readiness finding and evidence",evidence_refs=["scqos:multicloud:SCQOS-MULTICLOUD-CONTINUITY-v1","scmail:azure:sc-mail-mark-v2","scmail:aws:sc-mail-mark-v1"],requested_action="inspect",why_multiply=f"Assign {r['name']} faculty to independently verify its bounded slice of Microsoft readiness.",ttl_seconds=1800,max_children=0,spend_limit_usd="0.00",now=now)
    q=evaluate_clone_birth(p,valid_role_ids=ids,now=now)
    receipts.append({"role_id":role_id,"role_name":r["name"],"clone_id":p["clone_id"],"state":q["state"],"reason":q["reason"],"receipt_id":q["receipt_id"]})
out={"proof_type":"SC_MAIL_MARK_59_FACULTY_READINESS_SWARM_V1","architecture_id":m["architecture_id"],"protocol":"SHADOW-CLONE-RECURSIVE-EXECUTION-V1","objective":objective,"authority":"READ_ONLY_AUTONOMY","external_contact_authorized":False,"mail_send_authorized":False,"role_count":len(roles),"permit_count":sum(x["state"]=="PERMIT" for x in receipts),"receipts":receipts,"observed_at":now.isoformat()}
out["sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
path=pathlib.Path("sc-mail/swarm/MARK_MICROSOFT_READINESS_SWARM.json"); path.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({"role_count":out["role_count"],"permit_count":out["permit_count"],"sha256":out["sha256"],"external_contact_authorized":False,"mail_send_authorized":False}))
sys.exit(0 if out["permit_count"]==59 else 12)

# Optional durable cloud receipt when running as the Azure swarm job.
try:
    import os
    account=os.environ.get("AZURE_STORAGE_ACCOUNT")
    if account:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient, ContentSettings
        cid=os.environ.get("AZURE_CLIENT_ID")
        credential=DefaultAzureCredential(managed_identity_client_id=cid) if cid else DefaultAzureCredential()
        svc=BlobServiceClient(account_url=f"https://{account}.blob.core.windows.net",credential=credential)
        data=path.read_bytes()
        svc.get_blob_client(os.environ.get("EVIDENCE_CONTAINER","evidence"),"scmail/mark/microsoft/MARK_MICROSOFT_READINESS_SWARM.json").upload_blob(data,overwrite=True,content_settings=ContentSettings(content_type="application/json"))
        print("AZURE_SWARM_RECEIPT_STORED")
except Exception as exc:
    print("AZURE_SWARM_RECEIPT_HOLD",type(exc).__name__)
    raise
