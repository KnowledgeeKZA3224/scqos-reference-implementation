
import os, json, time, urllib.request, urllib.parse, urllib.error, hashlib, hmac, base64
import boto3
TABLE=os.environ["TABLE_NAME"]; MICROSOFT_SECRET_ARN=os.environ["MICROSOFT_SECRET_ARN"]; SIGNING_SECRET_ARN=os.environ["SIGNING_SECRET_ARN"]
SAFE_PER_MIN=int(os.environ.get("SAFE_PER_MIN","28"))
ddb=boto3.client("dynamodb"); sm=boto3.client("secretsmanager")
def secret(arn): return sm.get_secret_value(SecretId=arn).get("SecretString","")
def cfg():
    x=json.loads(secret(MICROSOFT_SECRET_ARN) or "{}")
    x["tenant_id"]=os.environ.get("MICROSOFT_TENANT_ID",x.get("tenant_id"))
    x["sender_upn"]=os.environ.get("MICROSOFT_SENDER_UPN",x.get("sender_upn"))
    return x
def access_token(c):
    data=urllib.parse.urlencode({"client_id":c["client_id"],"scope":"openid offline_access User.Read Mail.Send Mail.Send.Shared","grant_type":"refresh_token","refresh_token":c["refresh_token"]}).encode()
    req=urllib.request.Request("https://login.microsoftonline.com/"+c["tenant_id"]+"/oauth2/v2.0/token",data=data,headers={"content-type":"application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req,timeout=20) as r:
        x=json.loads(r.read().decode())
    if x.get("refresh_token") and x["refresh_token"]!=c.get("refresh_token"):
        c["refresh_token"]=x["refresh_token"]
        sm.put_secret_value(SecretId=MICROSOFT_SECRET_ARN,SecretString=json.dumps(c,separators=(",",":")))
    return x["access_token"]

def is_suppressed(e):
    return "Item" in ddb.get_item(TableName=TABLE,Key={"PK":{"S":"SUPPRESS#"+e},"SK":{"S":"STATE"}})
def unsub(base,e):
    sig=hmac.new(secret(SIGNING_SECRET_ARN).encode(),e.encode(),hashlib.sha256).hexdigest()
    return base.rstrip("/")+"/u/"+sig+"?e="+urllib.parse.quote(e)
def send_one(c,t,m):
    e=m["email"].strip().lower()
    if is_suppressed(e): return {"status":"SUPPRESSED"}
    u=unsub(m["base_url"],e); body=m.get("body","").replace("{FirstName}",m.get("firstName",""))+"\\n\\nUnsubscribe: "+u
    mime=("From: "+c["sender_upn"]+"\\r\\nTo: "+e+"\\r\\nSubject: "+m.get("subject","")+"\\r\\nMIME-Version: 1.0\\r\\nContent-Type: text/plain; charset=UTF-8\\r\\nList-Unsubscribe: <"+u+">\\r\\nList-Unsubscribe-Post: List-Unsubscribe=One-Click\\r\\n\\r\\n"+body).encode()
    req=urllib.request.Request("https://graph.microsoft.com/v1.0/me/sendMail",data=base64.b64encode(mime),method="POST",headers={"Authorization":"Bearer "+t,"Content-Type":"text/plain"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                if r.status==202: return {"status":"ACCEPTED"}
        except urllib.error.HTTPError as x:
            if x.code==429:
                time.sleep(min(int(x.headers.get("Retry-After","10")),120)); continue
            if 500<=x.code<600:
                time.sleep(min(2**(attempt+1),20)); continue
            try: detail=x.read().decode(errors="ignore")[:1200]
            except Exception: detail=""
            print("GRAPH_SEND_PERMANENT_FAILURE",json.dumps({"http":x.code,"detail":detail}))
            return {"status":"PERMANENT_FAILURE","http":x.code,"detail":detail[:500]}
    return {"status":"RETRY_EXHAUSTED"}
def handler(event,context):
    if os.environ.get("EXECUTION_ENABLED","false").lower()!="true":
        return {"batchItemFailures":[{"itemIdentifier":r["messageId"]} for r in event.get("Records",[])]}
    c=cfg(); required=["tenant_id","client_id","sender_upn","refresh_token"]
    if not c.get("sender_authority_verified") or not all(c.get(k) and not str(c.get(k)).startswith("REPLACE_") for k in required):
        return {"batchItemFailures":[{"itemIdentifier":r["messageId"]} for r in event.get("Records",[])]}
    t=access_token(c); failures=[]; delay=max(60.0/SAFE_PER_MIN,2.0)
    for r in event.get("Records",[]):
        m=json.loads(r["body"]); result=send_one(c,t,m); now=str(int(time.time()*1000)); campaign=m.get("campaignId","unknown")
        ddb.put_item(TableName=TABLE,Item={"PK":{"S":"CAMPAIGN#"+campaign},"SK":{"S":"RECEIPT#"+now+"#"+r["messageId"]},"EmailHash":{"S":hashlib.sha256(m["email"].lower().encode()).hexdigest()},"Status":{"S":result.get("status","UNKNOWN")},"At":{"N":str(int(time.time()))}})
        if result.get("status")=="RETRY_EXHAUSTED": failures.append({"itemIdentifier":r["messageId"]})
        time.sleep(delay)
    return {"batchItemFailures":failures}
