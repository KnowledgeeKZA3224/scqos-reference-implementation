import os, json, time, uuid, hashlib, hmac, threading, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, Response, RedirectResponse
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.storage.blob import BlobServiceClient, ContentSettings
from sc_core import compile_batch, HARD_OUTLOOK_CEILING, SAFE_MESSAGES_PER_MINUTE, INVARIANTS

APP_VERSION="2.0.0-azure"
ACCOUNT=os.environ["AZURE_STORAGE_ACCOUNT"]
TABLE_NAME=os.environ.get("AZURE_TABLE","scmailstate")
KV_URL=os.environ["KEY_VAULT_URL"]
QUEUE_NS=os.environ["SERVICEBUS_NAMESPACE"]
QUEUE_NAME=os.environ.get("SERVICEBUS_QUEUE","scmail-mark")
EVIDENCE_CONTAINER=os.environ.get("EVIDENCE_CONTAINER","receipts")
AWS_MARK_BASE=os.environ.get("AWS_MARK_BASE","https://v12t2f3nla.execute-api.us-east-1.amazonaws.com")
CLIENT_ID=os.environ.get("AZURE_CLIENT_ID")
cred=DefaultAzureCredential(managed_identity_client_id=CLIENT_ID) if CLIENT_ID else DefaultAzureCredential()
table=TableServiceClient(endpoint=f"https://{ACCOUNT}.table.core.windows.net",credential=cred).get_table_client(TABLE_NAME)
secrets=SecretClient(vault_url=KV_URL,credential=cred)
servicebus=ServiceBusClient(fully_qualified_namespace=QUEUE_NS,credential=cred)
blob=BlobServiceClient(account_url=f"https://{ACCOUNT}.blob.core.windows.net",credential=cred)
app=FastAPI(title="Supreme Mail Mark",version=APP_VERSION)
def _secret(name):
    return secrets.get_secret(name).value

def provider_cfg():
    try:
        return json.loads(_secret("scmail-mark-microsoft") or "{}")
    except Exception:
        return {}

def provider_ready(c=None):
    c=c or provider_cfg()
    req=("tenant_id","client_id","client_secret","sender_upn","refresh_token")
    return all(c.get(k) and not str(c.get(k)).startswith("REPLACE_") for k in req)

def aws_health():
    try:
        with urllib.request.urlopen(AWS_MARK_BASE+"/health",timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"status":"HOLD","error":type(e).__name__}

def window_usage():
    cutoff=int(time.time())-86400
    used=0
    for e in table.query_entities("PartitionKey eq 'OUTLOOK_WINDOW'"):
        if int(e.get("CreatedAt",0)) >= cutoff:
            used += int(e.get("Count",0))
    return used

def email_hash(email):
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()

def suppressed(email):
    try:
        table.get_entity("SUPPRESS",email_hash(email))
        return True
    except ResourceNotFoundError:
        return False
def unsubscribe_token(email):
    key=_secret("scmail-mark-signing").encode()
    return hmac.new(key,email.strip().lower().encode(),hashlib.sha256).hexdigest()

def write_receipt(campaign_id,email,status,extra=None):
    now=int(time.time()*1000)
    payload={"campaignId":campaign_id,"emailHash":email_hash(email),"status":status,"at":now}
    if extra: payload.update(extra)
    payload["receiptSha256"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    entity={"PartitionKey":"RECEIPT#"+campaign_id,"RowKey":f"{now}#{uuid.uuid4()}",
            "EmailHash":payload["emailHash"],"Status":status,"At":now,"ReceiptSha256":payload["receiptSha256"]}
    table.upsert_entity(entity)
    data=(json.dumps(payload,sort_keys=True,indent=2)+"\n").encode()
    name=f"scmail/{campaign_id}/{payload['receiptSha256']}.json"
    blob.get_blob_client(EVIDENCE_CONTAINER,name).upload_blob(
        data,overwrite=True,content_settings=ContentSettings(content_type="application/json"))
    return payload

def graph_token(c):
    data=urllib.parse.urlencode({
        "client_id":c["client_id"],"client_secret":c["client_secret"],
        "refresh_token":c["refresh_token"],"scope":"offline_access Mail.Send User.Read",
        "grant_type":"refresh_token"}).encode()
    req=urllib.request.Request(
        "https://login.microsoftonline.com/"+c["tenant_id"]+"/oauth2/v2.0/token",
        data=data,headers={"content-type":"application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req,timeout=20) as r:
        out=json.loads(r.read().decode())
    if out.get("refresh_token") and out["refresh_token"] != c.get("refresh_token"):
        c=dict(c); c["refresh_token"]=out["refresh_token"]
        secrets.set_secret("scmail-mark-microsoft",json.dumps(c,separators=(",",":")))
    return out["access_token"]
def send_one(c,token,msg):
    email=msg["email"].strip().lower()
    if suppressed(email):
        return {"status":"SUPPRESSED"}
    base=msg["base_url"].rstrip("/")
    u=base+"/u/"+unsubscribe_token(email)+"?e="+urllib.parse.quote(email)
    body=msg.get("body","").replace("{FirstName}",msg.get("firstName",""))+"\n\nUnsubscribe: "+u
    payload={"message":{
        "subject":msg.get("subject",""),
        "body":{"contentType":"Text","content":body},
        "toRecipients":[{"emailAddress":{"address":email}}],
        "internetMessageHeaders":[
            {"name":"List-Unsubscribe","value":"<"+u+">"},
            {"name":"List-Unsubscribe-Post","value":"List-Unsubscribe=One-Click"}]},
        "saveToSentItems":True}
    req=urllib.request.Request(
        "https://graph.microsoft.com/v1.0/users/"+urllib.parse.quote(c["sender_upn"])+"/sendMail",
        data=json.dumps(payload).encode(),method="POST",
        headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                if r.status==202: return {"status":"ACCEPTED"}
        except urllib.error.HTTPError as x:
            if x.code==429:
                time.sleep(min(int(x.headers.get("Retry-After","10")),120)); continue
            if 500 <= x.code < 600:
                time.sleep(min(2**(attempt+1),20)); continue
            return {"status":"PERMANENT_FAILURE","http":x.code}
        except Exception as x:
            if attempt==3: return {"status":"RETRY_EXHAUSTED","error":type(x).__name__}
            time.sleep(min(2**(attempt+1),20))
    return {"status":"RETRY_EXHAUSTED"}
def decode_message(msg):
    parts=[]
    for part in msg.body:
        parts.append(bytes(part))
    return json.loads(b"".join(parts).decode())

def worker_loop():
    while True:
        c=provider_cfg()
        if not provider_ready(c):
            time.sleep(15); continue
        try:
            token=graph_token(c)
            with servicebus.get_queue_receiver(queue_name=QUEUE_NAME,max_wait_time=10,prefetch_count=1) as receiver:
                for sbmsg in receiver:
                    m=decode_message(sbmsg)
                    result=send_one(c,token,m)
                    write_receipt(m.get("campaignId","unknown"),m.get("email",""),result.get("status","UNKNOWN"),result)
                    if result.get("status")=="RETRY_EXHAUSTED":
                        receiver.abandon_message(sbmsg)
                    else:
                        receiver.complete_message(sbmsg)
                    time.sleep(max(60.0/SAFE_MESSAGES_PER_MINUTE,2.0))
        except Exception:
            time.sleep(10)

@app.on_event("startup")
def startup():
    threading.Thread(target=worker_loop,daemon=True,name="scmail-graph-worker").start()

@app.get("/health")
def health():
    a=aws_health()
    return {"service":"sc-mail-mark-v2","status":"ONLINE","cloud":"Azure","version":APP_VERSION,
            "providerConnected":provider_ready(),"awsWitness":a,
            "rule":"Nothing executes until it proves itself.","invariants":list(INVARIANTS)}
@app.get("/config")
def config():
    used=window_usage()
    c=provider_cfg()
    return {"product":"Supreme Mail","provider":"microsoft365","providerConnected":provider_ready(c),
            "adminConfirmed":bool(c.get("admin_confirmed")),"hardCeiling":HARD_OUTLOOK_CEILING,
            "usedInRollingWindow":used,"remainingInRollingWindow":max(0,HARD_OUTLOOK_CEILING-used),
            "safePerMinute":SAFE_MESSAGES_PER_MINUTE,"invariants":list(INVARIANTS),
            "executionCloud":"Azure","witnessCloud":"AWS"}

def oauth_state():
    raw=f"{int(time.time())}:{uuid.uuid4()}"
    sig=hmac.new(_secret("scmail-mark-signing").encode(),raw.encode(),hashlib.sha256).hexdigest()
    return raw+"."+sig

def verify_oauth_state(value):
    try:
        raw,sig=value.rsplit(".",1)
        ts=int(raw.split(":",1)[0])
        expected=hmac.new(_secret("scmail-mark-signing").encode(),raw.encode(),hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig,expected) and abs(int(time.time())-ts) < 900
    except Exception:
        return False

@app.get("/microsoft/connect")
def microsoft_connect(request:Request):
    # Legacy delegated OAuth entrypoint is retired. Always enter through the
    # canonical multitenant admin-consent + Exchange Application RBAC path.
    return RedirectResponse(url="/microsoft/admin-consent",status_code=307)

@app.get("/microsoft/callback")
def microsoft_callback(request:Request):
    raise HTTPException(status_code=410,detail="legacy_oauth_callback_retired_use_rbac")

@app.get("/manifest.xml")
def manifest(request:Request):
    base="https://"+request.headers["host"]
    return Response(Path("/app/manifest.xml").read_text().replace("__BASE__",base),media_type="application/xml")

@app.get("/taskpane")
@app.get("/")
def taskpane(request:Request):
    base="https://"+request.headers["host"]
    return HTMLResponse(Path("/app/taskpane.html").read_text().replace("__BASE__",base))

@app.get("/icon")
def icon():
    import base64
    png="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    return Response(base64.b64decode(png),media_type="image/png")

@app.post("/api/preflight")
async def preflight(request:Request):
    body=await request.json()
    contacts=body.get("contacts") or []
    requested=min(int(body.get("requestedCount") or len(contacts) or 0),HARD_OUTLOOK_CEILING)
    campaign=dict(body.get("campaign") or {})
    campaign["authorized"]=True
    batch=compile_batch(contacts,campaign,requested)
    return {**batch,"providerConnected":provider_ready(),"awsWitness":aws_health()}
def enqueue_messages(selected,campaign,campaign_id,base):
    with servicebus.get_queue_sender(queue_name=QUEUE_NAME) as sender:
        batch=sender.create_message_batch()
        for c in selected:
            m={"campaignId":campaign_id,"email":c["email"],"firstName":c.get("firstName",""),
               "company":c.get("company",""),"subject":campaign["subject"],
               "body":campaign["body"],"base_url":base}
            sm=ServiceBusMessage(json.dumps(m,separators=(",",":")))
            try:
                batch.add_message(sm)
            except ValueError:
                sender.send_messages(batch)
                batch=sender.create_message_batch(); batch.add_message(sm)
        if len(batch)>0: sender.send_messages(batch)

@app.post("/api/send")
async def send(request:Request):
    if not provider_ready():
        return JSONResponse(status_code=409,content={"decision":"HOLD","error":"microsoft_authorization_required","queued":0})
    body=await request.json()
    contacts=body.get("contacts") or []
    requested=min(int(body.get("requestedCount") or len(contacts) or 0),HARD_OUTLOOK_CEILING)
    campaign=dict(body.get("campaign") or {})
    if not campaign.get("subject") or not campaign.get("body") or not campaign.get("audience") or not campaign.get("authorized"):
        return JSONResponse(status_code=400,content={"decision":"HOLD","error":"campaign_not_fully_authorized","queued":0})
    remaining=max(0,HARD_OUTLOOK_CEILING-window_usage())
    if requested>remaining:
        return JSONResponse(status_code=409,content={"decision":"HOLD","error":"outlook_rolling_window_ceiling","remaining":remaining,"queued":0})
    batch=compile_batch(contacts,campaign,requested)
    if batch["decision"]!="PERMIT":
        return JSONResponse(status_code=409,content={**batch,"queued":0})
    lookup={str(c.get("email","")).strip().lower():c for c in contacts}
    selected=[]
    for p in batch["selected"]:
        src=lookup.get(p["email"],{})
        selected.append({"email":p["email"],"firstName":src.get("firstName",""),"company":src.get("company","")})
    campaign_id=str(uuid.uuid4())
    now=int(time.time())
    table.upsert_entity({"PartitionKey":"OUTLOOK_WINDOW","RowKey":f"{now}#{campaign_id}",
                         "Count":requested,"CampaignId":campaign_id,"CreatedAt":now,"ExpiresAt":now+86400})
    table.upsert_entity({"PartitionKey":"CAMPAIGN","RowKey":campaign_id,"Status":"QUEUED",
                         "Requested":requested,"Queued":len(selected),"BatchReceipt":batch["batch_receipt_sha256"],
                         "CreatedAt":now})
    base=str(request.base_url).rstrip("/")
    enqueue_messages(selected,campaign,campaign_id,base)
    return JSONResponse(status_code=202,content={"decision":"PERMIT","campaignId":campaign_id,
        "queued":len(selected),"receiptSha256":batch["batch_receipt_sha256"]})

@app.get("/api/activity")
def activity(campaignId:str):
    rows=list(table.query_entities(f"PartitionKey eq 'RECEIPT#{campaignId}'"))
    counts={}
    for r in rows:
        st=r.get("Status","UNKNOWN"); counts[st]=counts.get(st,0)+1
    try: state=table.get_entity("CAMPAIGN",campaignId)
    except ResourceNotFoundError: state={}
    return {"campaignId":campaignId,"counts":counts,"items":len(rows),"state":dict(state)}

@app.get("/u/{token}")
def unsubscribe(token:str,e:str):
    email=e.strip().lower()
    if not email or not hmac.compare_digest(token,unsubscribe_token(email)):
        raise HTTPException(status_code=400,detail="Invalid unsubscribe link")
    now=int(time.time())
    table.upsert_entity({"PartitionKey":"SUPPRESS","RowKey":email_hash(email),"Reason":"unsubscribe","At":now})
    return Response("You have been unsubscribed.",media_type="text/plain")

# --- Supreme Mail federated Microsoft boundary (v2.1) ---
# Secretless app-only authentication: Azure managed identity -> Entra app -> customer tenant Graph.
ENTRA_APP_CLIENT_ID=os.environ.get("SCMAIL_ENTRA_APP_CLIENT_ID","")
_graph_token_cache={"token":"","expires_on":0,"roles":[]}

def _jwt_roles(token):
    import base64
    try:
        part=token.split(".")[1]
        part += "=" * (-len(part) % 4)
        claims=json.loads(base64.urlsafe_b64decode(part.encode()).decode())
        return list(claims.get("roles") or [])
    except Exception:
        return []

def graph_token(c):
    now=int(time.time())
    if _graph_token_cache["token"] and int(_graph_token_cache["expires_on"] or 0) > now+120:
        return _graph_token_cache["token"]
    if not ENTRA_APP_CLIENT_ID or not c.get("tenant_id"):
        raise RuntimeError("federated_app_not_configured")
    from azure.identity import ManagedIdentityCredential, ClientAssertionCredential
    mi=ManagedIdentityCredential(client_id=CLIENT_ID)
    fic=ClientAssertionCredential(
        tenant_id=str(c["tenant_id"]),
        client_id=ENTRA_APP_CLIENT_ID,
        func=lambda: mi.get_token("api://AzureADTokenExchange/.default").token,
    )
    tok=fic.get_token("https://graph.microsoft.com/.default")
    roles=_jwt_roles(tok.token)
    if "Mail.Send" not in roles:
        raise RuntimeError("microsoft_mail_send_not_consented")
    _graph_token_cache.update(token=tok.token,expires_on=int(tok.expires_on),roles=roles)
    return tok.token

def provider_ready(c=None):
    c=c or provider_cfg()
    if not (c.get("tenant_id") and c.get("sender_upn") and ENTRA_APP_CLIENT_ID and CLIENT_ID):
        return False
    try:
        graph_token(c)
        return "Mail.Send" in _graph_token_cache.get("roles",[])
    except Exception:
        return False

def microsoft_permission_status():
    c=provider_cfg()
    try:
        ok=provider_ready(c)
        return {"providerConnected":ok,"authMode":"federated_managed_identity","mailSendConsented":bool(ok)}
    except Exception as e:
        return {"providerConnected":False,"authMode":"federated_managed_identity","mailSendConsented":False,"error":type(e).__name__}

@app.get("/microsoft/readiness")
def microsoft_readiness():
    c=provider_cfg()
    s=microsoft_permission_status()
    return {**s,"tenantConfigured":bool(c.get("tenant_id")),"senderConfigured":bool(c.get("sender_upn")),
            "appConfigured":bool(ENTRA_APP_CLIENT_ID),"managedIdentityConfigured":bool(CLIENT_ID),
            "externalContactAuthorized":False,"mailSendExecutionAuthorized":bool(s.get("providerConnected")),
            "rule":"Nothing executes until it proves itself."}

@app.get("/microsoft/admin-consent")
def microsoft_admin_consent(request:Request):
    c=provider_cfg()
    if not c.get("tenant_id") or not ENTRA_APP_CLIENT_ID:
        raise HTTPException(status_code=503,detail="microsoft_tenant_or_app_not_ready")
    redirect="https://"+request.headers["host"]+"/microsoft/admin-consent/callback"
    params={"client_id":ENTRA_APP_CLIENT_ID,"redirect_uri":redirect,"scope":"https://graph.microsoft.com/.default","state":oauth_state()}
    url="https://login.microsoftonline.com/"+str(c["tenant_id"])+"/v2.0/adminconsent?"+urllib.parse.urlencode(params)
    return RedirectResponse(url)

@app.get("/microsoft/admin-consent/callback")
def microsoft_admin_consent_callback(request:Request,admin_consent:str="",tenant:str="",state:str="",error:str="",error_description:str=""):
    c=provider_cfg()
    if error or not verify_oauth_state(state):
        raise HTTPException(status_code=400,detail="microsoft_admin_consent_failed")
    if str(tenant).lower()!=str(c.get("tenant_id","")).lower():
        raise HTTPException(status_code=403,detail="microsoft_tenant_mismatch")
    if str(admin_consent).lower()!="true":
        raise HTTPException(status_code=400,detail="microsoft_admin_consent_not_granted")
    now=int(time.time())
    table.upsert_entity({"PartitionKey":"MICROSOFT_AUTH","RowKey":"ADMIN_CONSENT","Tenant":str(tenant),"At":now,"State":"CONSENT_RECORDED"})
    # Token propagation can take time. The reconciliation path will only move to PERMIT after Mail.Send is observed.
    status=microsoft_permission_status()
    state_label="PERMIT" if status.get("providerConnected") else "HOLD_PROPAGATION_OR_SCOPE"
    table.upsert_entity({"PartitionKey":"MICROSOFT_AUTH","RowKey":"GRAPH_PROBE","At":now,"State":state_label})
    return HTMLResponse("<h2>Supreme Mail Microsoft approval recorded.</h2><p>The governed cloud is verifying Mail.Send authority. You can close this window.</p>")

# --- RBAC-only mailbox scope override (v2.2) ---
# Exchange Application RBAC is authoritative; no tenant-wide Graph Mail.Send grant is used.
def _rbac_proven(c=None):
    c=c or provider_cfg()
    try:
        e=table.get_entity("MICROSOFT_AUTH","RBAC_PROVEN")
        return (str(e.get("State","")).upper()=="PERMIT" and
                str(e.get("Mailbox","")).strip().lower()==str(c.get("sender_upn","")).strip().lower() and
                str(e.get("AppId","")).strip().lower()==ENTRA_APP_CLIENT_ID.lower())
    except Exception:
        return False

def graph_token(c):
    now=int(time.time())
    if _graph_token_cache["token"] and int(_graph_token_cache["expires_on"] or 0) > now+120:
        return _graph_token_cache["token"]
    if not ENTRA_APP_CLIENT_ID or not c.get("tenant_id"):
        raise RuntimeError("federated_app_not_configured")
    from azure.identity import ManagedIdentityCredential, ClientAssertionCredential
    mi=ManagedIdentityCredential(client_id=CLIENT_ID)
    fic=ClientAssertionCredential(
        tenant_id=str(c["tenant_id"]),
        client_id=ENTRA_APP_CLIENT_ID,
        func=lambda: mi.get_token("api://AzureADTokenExchange/.default").token,
    )
    tok=fic.get_token("https://graph.microsoft.com/.default")
    _graph_token_cache.update(token=tok.token,expires_on=int(tok.expires_on),roles=_jwt_roles(tok.token))
    return tok.token

def provider_ready(c=None):
    c=c or provider_cfg()
    if not (c.get("tenant_id") and c.get("sender_upn") and ENTRA_APP_CLIENT_ID and CLIENT_ID and _rbac_proven(c)):
        return False
    try:
        graph_token(c)
        return True
    except Exception:
        return False

def microsoft_permission_status():
    c=provider_cfg()
    auth=False
    try:
        graph_token(c); auth=True
    except Exception:
        auth=False
    rbac=_rbac_proven(c)
    return {"providerConnected":bool(auth and rbac),"authMode":"federated_managed_identity+r bac".replace(" ",""),
            "tokenExchangeReady":auth,"rbacProven":rbac,"mailSendConsented":False,
            "tenantWideMailSendPermission":False}
