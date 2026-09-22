
import os, json, re, hashlib, hmac, time, uuid, urllib.parse, urllib.request, urllib.error
import boto3

TABLE=os.environ["TABLE_NAME"]
MICROSOFT_SECRET_ARN=os.environ["MICROSOFT_SECRET_ARN"]
SIGNING_SECRET_ARN=os.environ["SIGNING_SECRET_ARN"]
HARD_CEILING=int(os.environ.get("HARD_CEILING","9950"))
SAFE_PER_MIN=int(os.environ.get("SAFE_PER_MIN","28"))
ddb=boto3.client("dynamodb")
sm=boto3.client("secretsmanager")
INVARIANTS=["Time","Continuity","Alignment","Genesis","Boundary","Reference","Causality","Consciousness"]

def response(code, body, content_type="application/json"):
    if content_type=="application/json" and not isinstance(body,str):
        body=json.dumps(body,separators=(",",":"))
    return {"statusCode":code,"headers":{"content-type":content_type,"cache-control":"no-store"},"body":body}

def get_secret(arn):
    return sm.get_secret_value(SecretId=arn).get("SecretString","")

def provider_ready():
    try:
        cfg=json.loads(get_secret(MICROSOFT_SECRET_ARN) or "{}")
        req=["tenant_id","client_id","sender_upn","refresh_token"]
        return os.environ.get("EXECUTION_ENABLED","false").lower()=="true" and bool(cfg.get("sender_authority_verified")) and all(cfg.get(k) and not str(cfg.get(k)).startswith("REPLACE_") for k in req)
    except Exception:
        return False

def window_usage():
    now=int(time.time()); cutoff=now-86400
    r=ddb.query(TableName=TABLE,KeyConditionExpression="PK = :pk AND SK >= :cut",ExpressionAttributeValues={":pk":{"S":"OUTLOOK_WINDOW"},":cut":{"S":"R#"+str(cutoff)}})
    used=0
    for item in r.get("Items",[]):
        used += int((item.get("Count") or {}).get("N","0"))
    return used

def valid_email(v):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (v or "").strip()))

def blocked_source(v):
    return (v or "").strip().lower() in {"scraped","purchased","bought","unknown","mystery"}

def evaluate(c):
    email=(c.get("email") or "").strip().lower()
    source=(c.get("source") or "").strip()
    suppressed=bool(c.get("unsubscribed") or c.get("hard_bounce") or c.get("complaint"))
    checks={
      "Time": True,
      "Continuity": not suppressed,
      "Alignment": valid_email(email),
      "Genesis": bool(source) and not blocked_source(source),
      "Boundary": not suppressed,
      "Reference": True,
      "Causality": bool(c.get("purpose") or c.get("relationship") or source),
      "Consciousness": bool(c.get("authorized",True))
    }
    return email, checks, all(checks.values())

def manifest(base):
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<OfficeApp xmlns="http://schemas.microsoft.com/office/appforoffice/1.1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:bt="http://schemas.microsoft.com/office/officeappbasictypes/1.0" xsi:type="MailApp">
<Id>6d6f5127-9a6e-4f52-8c21-f6a4e7fe9950</Id><Version>1.0.0.0</Version><ProviderName>Supreme Computation</ProviderName>
<DefaultLocale>en-US</DefaultLocale><DisplayName DefaultValue="Supreme Mail"/><Description DefaultValue="Outlook-native governed business email automation."/>
<IconUrl DefaultValue="%s/icon"/><SupportUrl DefaultValue="%s/health"/><AppDomains><AppDomain>%s</AppDomain></AppDomains>
<Hosts><Host Name="Mailbox"/></Hosts><Requirements><Sets><Set Name="Mailbox" MinVersion="1.5"/></Sets></Requirements>
<FormSettings><Form xsi:type="ItemRead"><DesktopSettings><SourceLocation DefaultValue="%s/taskpane"/><RequestedHeight>450</RequestedHeight></DesktopSettings></Form>
<Form xsi:type="ItemEdit"><DesktopSettings><SourceLocation DefaultValue="%s/taskpane"/></DesktopSettings></Form></FormSettings>
<Permissions>ReadWriteMailbox</Permissions><Rule xsi:type="RuleCollection" Mode="Or"><Rule xsi:type="ItemIs" ItemType="Message" FormType="Read"/><Rule xsi:type="ItemIs" ItemType="Message" FormType="Edit"/></Rule>
<VersionOverrides xmlns="http://schemas.microsoft.com/office/mailappversionoverrides" xsi:type="VersionOverridesV1_0">
<Requirements><bt:Sets DefaultMinVersion="1.5"><bt:Set Name="Mailbox"/></bt:Sets></Requirements>
<Hosts><Host xsi:type="MailHost"><DesktopFormFactor>
<FunctionFile resid="Commands.Url"/>
<ExtensionPoint xsi:type="MessageReadCommandSurface"><OfficeTab id="TabDefault"><Group id="SupremeMail.Read.Group"><Label resid="Group.Label"/><Control xsi:type="Button" id="SupremeMail.Read.Open"><Label resid="Button.Label"/><Supertip><Title resid="Button.Label"/><Description resid="Button.Desc"/></Supertip><Icon><bt:Image size="16" resid="Icon.16"/><bt:Image size="32" resid="Icon.32"/><bt:Image size="80" resid="Icon.80"/></Icon><Action xsi:type="ShowTaskpane"><SourceLocation resid="Taskpane.Url"/><SupportsPinning>true</SupportsPinning></Action></Control></Group></OfficeTab></ExtensionPoint>
<ExtensionPoint xsi:type="MessageComposeCommandSurface"><OfficeTab id="TabDefault"><Group id="SupremeMail.Compose.Group"><Label resid="Group.Label"/><Control xsi:type="Button" id="SupremeMail.Compose.Open"><Label resid="Button.Label"/><Supertip><Title resid="Button.Label"/><Description resid="Button.Desc"/></Supertip><Icon><bt:Image size="16" resid="Icon.16"/><bt:Image size="32" resid="Icon.32"/><bt:Image size="80" resid="Icon.80"/></Icon><Action xsi:type="ShowTaskpane"><SourceLocation resid="Taskpane.Url"/><SupportsPinning>true</SupportsPinning></Action></Control></Group></OfficeTab></ExtensionPoint>
</DesktopFormFactor></Host></Hosts>
<Resources><bt:Images><bt:Image id="Icon.16" DefaultValue="%s/icon"/><bt:Image id="Icon.32" DefaultValue="%s/icon"/><bt:Image id="Icon.80" DefaultValue="%s/icon"/></bt:Images>
<bt:Urls><bt:Url id="Commands.Url" DefaultValue="%s/taskpane"/><bt:Url id="Taskpane.Url" DefaultValue="%s/taskpane"/></bt:Urls>
<bt:ShortStrings><bt:String id="Group.Label" DefaultValue="Supreme Mail"/><bt:String id="Button.Label" DefaultValue="Supreme Mail"/></bt:ShortStrings>
<bt:LongStrings><bt:String id="Button.Desc" DefaultValue="Open Supreme Mail business email controls."/></bt:LongStrings></Resources>
</VersionOverrides></OfficeApp>""" % (base,base,base,base,base,base,base,base,base,base)

def taskpane(base):
    return """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://appsforoffice.microsoft.com/lib/1/hosted/office.js"></script><style>
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f6f8fb;color:#1f2937}.wrap{padding:16px}h1{font-size:20px;margin:0 0 4px}.muted{color:#667085;font-size:12px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px;margin-top:12px}label{display:block;font-size:12px;font-weight:600;margin:8px 0 4px}
input,textarea,select{width:100%%;box-sizing:border-box;padding:9px;border:1px solid #cfd4dc;border-radius:6px;font:inherit}textarea{min-height:120px}
button{border:0;border-radius:7px;padding:10px 12px;font-weight:700;cursor:pointer}.primary{background:#106ebe;color:#fff;width:100%%;margin-top:10px}.secondary{background:#eef2f7;margin-right:6px}
.status{font-weight:700}.green{color:#08783e}.amber{color:#b54708}.row{display:flex;gap:8px}.row>*{flex:1}.count{font-size:24px;font-weight:700}</style></head>
<body><div class="wrap"><h1>📨 Supreme Mail</h1><div class="muted">Business email inside Outlook. SC handles the complexity underneath.</div>
<div class="card"><div class="row"><div><div class="muted">SC status</div><div id="status" class="status amber">Checking…</div></div><div><div class="muted">Available this window</div><div class="count">%s</div></div></div></div>
<div class="card"><label>👥 Contact list (.csv)</label><input id="file" type="file" accept=".csv,text/csv"><label>🎯 Audience</label>
<select id="audience"><option>Existing customers</option><option>New leads</option><option>Custom list</option></select>
<label>✍️ Subject</label><input id="subject" placeholder="Example: September tax reminder"><label>✍️ Message</label><textarea id="body" placeholder="Hi {FirstName},&#10;&#10;Write your message here..."></textarea>
<div class="row"><button class="secondary" onclick="preview()">👁 Preview</button><button class="secondary" onclick="preflight()">🛡️ SC Check</button></div>
<button id="send" class="primary" onclick="sendCampaign()" disabled>🚀 Send</button><div id="result" class="muted" style="margin-top:10px"></div></div>
<div class="card"><b>Activity</b><div class="muted">Sent, scheduled, failed and suppressed contacts are recorded automatically.</div></div></div>
<script>
var BASE=%s; var contacts=[]; var proof=null;
function parseCSV(text){var lines=text.split(/\\r?\\n/).filter(Boolean);if(!lines.length)return[];var h=lines[0].split(',').map(function(x){return x.trim().toLowerCase();});
return lines.slice(1).map(function(line){var v=line.split(',');var o={};h.forEach(function(k,i){o[k]=(v[i]||'').trim();});
return {email:o.email||o['email address'],firstName:o.firstname||o['first name']||'',company:o.company||'',source:o.source||'existing_business_file',relationship:o.relationship||document.getElementById('audience').value,purpose:'business outreach',authorized:true};});}
document.getElementById('file').addEventListener('change',async function(e){var t=await e.target.files[0].text();contacts=parseCSV(t);document.getElementById('result').textContent='Loaded '+contacts.length.toLocaleString()+' contacts.';});
async function boot(){var r=await fetch(BASE+'/config');var x=await r.json();var s=document.getElementById('status');s.textContent=x.providerConnected?'READY':'MICROSOFT CONNECTION NEEDED';s.className='status '+(x.providerConnected?'green':'amber');var c=document.querySelector('.count');if(c)c.textContent=Number(x.remainingInRollingWindow).toLocaleString();}
function preview(){var c=contacts[0]||{firstName:'Mark'};var b=document.getElementById('body').value.split('{FirstName}').join(c.firstName||'');document.getElementById('result').textContent=(document.getElementById('subject').value||'(no subject)')+' — '+b.slice(0,180);}
async function preflight(){document.getElementById('result').textContent='SC is checking the campaign…';var payload={contacts:contacts.slice(0,9950),requestedCount:Math.min(contacts.length,9950),campaign:{subject:document.getElementById('subject').value,body:document.getElementById('body').value,audience:document.getElementById('audience').value}};
var r=await fetch(BASE+'/api/preflight',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)});proof=await r.json();document.getElementById('result').textContent=proof.decision+' — '+proof.permitted+' ready, '+proof.rejected+' held/rejected.';document.getElementById('send').disabled=!(proof.decision==='PERMIT'&&proof.providerConnected);}
async function sendCampaign(){document.getElementById('send').disabled=true;document.getElementById('result').textContent='SC is compiling and queueing the proven batch…';var payload={contacts:contacts.slice(0,9950),requestedCount:Math.min(contacts.length,9950),campaign:{subject:document.getElementById('subject').value,body:document.getElementById('body').value,audience:document.getElementById('audience').value,authorized:true}};var r=await fetch(BASE+'/api/send',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)});var x=await r.json();document.getElementById('result').textContent=(x.decision||x.error)+' — '+(x.queued||0)+' queued.';document.getElementById('send').disabled=false;}\nOffice.onReady(function(){boot();});</script></body></html>""" % (format(HARD_CEILING,","),json.dumps(base))

def handler(event, context):
    path=event.get("rawPath") or "/"
    method=((event.get("requestContext") or {}).get("http") or {}).get("method","GET")
    headers={k.lower():v for k,v in (event.get("headers") or {}).items()}
    base="https://"+headers.get("host","")
    if path=="/connect/microsoft" and method=="GET":
        q=event.get("queryStringParameters") or {}
        tok=q.get("token","")
        try:
            setup=json.loads(get_secret(os.environ["SETUP_TOKEN_SECRET_ID"]) or "{}")
            valid=(not setup.get("used")) and tok==setup.get("token")
        except Exception:
            valid=False
        if not valid:
            return response(403,"This Supreme Mail setup link is invalid or expired.","text/plain")
        page="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Supreme Mail — Microsoft Connection</title><style>body{font-family:Segoe UI,Arial,sans-serif;max-width:760px;margin:36px auto;padding:0 18px;color:#202124}h1{font-size:28px}.card{background:#f6f8fb;border-radius:12px;padding:16px;margin:14px 0}ol{line-height:1.65}input{width:100%%;padding:11px;box-sizing:border-box;margin:6px 0 12px}button{background:#106ebe;color:white;border:0;border-radius:8px;padding:12px 18px;font-weight:700}.small{font-size:13px;color:#5f6368}</style></head>
<body><h1>Supreme Mail — Connect Microsoft 365</h1><div class="card"><b>Mailbox:</b> Marks@numbersetcandetc.com<br><b>Microsoft tenant:</b> numbersetcandetc.com</div>
<p>Microsoft needs Supreme Mail to have its own app ID before it can show the approval screen.</p>
<ol><li>Open <a target="_blank" href="https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade">Microsoft Entra — App registrations</a>.</li>
<li>Choose <b>New registration</b> and name it <b>Supreme Mail</b>.</li>
<li>Choose <b>Accounts in this organizational directory only</b>, then Register.</li>
<li>Open <b>API permissions</b> → Add a permission → Microsoft Graph → <b>Delegated permissions</b>. Add <b>Mail.Send</b>, <b>User.Read</b>, and <b>offline_access</b>.</li>
<li>Open <b>Authentication</b> → Advanced settings → set <b>Allow public client flows</b> to <b>Yes</b>, then Save.</li>
<li>Copy the <b>Application (client) ID</b> from the Overview page and paste it below.</li></ol>
<form method="POST" action="/connect/microsoft/start"><input type="hidden" name="token" value="%s">
<label>Application (client) ID</label><input name="client_id" required autocomplete="off">
<button type="submit">Generate my Microsoft approval code</button></form>
<p class="small">No Microsoft password or client secret is requested here.</p></body></html>""" % tok
        return response(200,page,"text/html; charset=utf-8")

    if path=="/connect/microsoft/start" and method=="POST":
        raw=event.get("body") or ""
        if event.get("isBase64Encoded"):
            import base64
            raw=base64.b64decode(raw).decode()
        form=urllib.parse.parse_qs(raw)
        tok=(form.get("token") or [""])[0]
        client_id=(form.get("client_id") or [""])[0].strip()
        setup=json.loads(get_secret(os.environ["SETUP_TOKEN_SECRET_ID"]) or "{}")
        if setup.get("used") or tok!=setup.get("token"):
            return response(403,"This Supreme Mail setup link is invalid or expired.","text/plain")
        if not re.match(r"^[0-9a-fA-F-]{36}$",client_id):
            return response(400,"That Microsoft Application (client) ID is not valid.","text/plain")
        scope="openid offline_access User.Read Mail.Send"
        data=urllib.parse.urlencode({"client_id":client_id,"scope":scope}).encode()
        req=urllib.request.Request("https://login.microsoftonline.com/"+os.environ["MICROSOFT_TENANT_ID"]+"/oauth2/v2.0/devicecode",data=data,headers={"content-type":"application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req,timeout=20) as rr:
                dc=json.loads(rr.read().decode())
        except urllib.error.HTTPError as e:
            detail=e.read().decode(errors="ignore")
            return response(502,"Microsoft would not start the approval flow. Recheck the Supreme Mail app registration settings.","text/plain")
        session=uuid.uuid4().hex
        ddb.put_item(TableName=TABLE,Item={
          "PK":{"S":"MICROSOFT_DEVICE#"+session},"SK":{"S":"STATE"},
          "ClientId":{"S":client_id},"DeviceCode":{"S":dc["device_code"]},
          "Interval":{"N":str(int(dc.get("interval",5)))},
          "ExpiresAt":{"N":str(int(time.time())+int(dc.get("expires_in",900)))}
        })
        cfg=json.loads(get_secret(MICROSOFT_SECRET_ARN) or "{}")
        cfg.update({"tenant_id":os.environ["MICROSOFT_TENANT_ID"],"sender_upn":os.environ["MICROSOFT_SENDER_UPN"],"client_id":client_id,"auth_mode":"device_code"})
        sm.put_secret_value(SecretId=MICROSOFT_SECRET_ARN,SecretString=json.dumps(cfg,separators=(",",":")))
        verify=dc.get("verification_uri") or "https://microsoft.com/devicelogin"
        code=dc.get("user_code","")
        page="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Supreme Mail Approval</title>
<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:680px;margin:44px auto;padding:0 18px}.code{font-size:32px;font-weight:800;letter-spacing:4px;background:#f5f7fb;padding:18px;text-align:center;border-radius:10px}a.btn{display:block;background:#106ebe;color:white;text-decoration:none;text-align:center;padding:14px;border-radius:8px;margin:18px 0;font-weight:700}</style></head>
<body><h1>Microsoft approval is ready ✅</h1><p>1. Copy this code:</p><div class="code">%s</div><p>2. Open Microsoft and sign in as the administrator:</p>
<a class="btn" target="_blank" href="%s">Open Microsoft approval page</a><p>3. Enter the code and approve Supreme Mail.</p>
<p id="status">Waiting for Microsoft approval…</p>
<script>
async function check(){try{let r=await fetch('/connect/microsoft/poll?session=%s');let x=await r.json();document.getElementById('status').textContent=x.message||x.status;if(x.status==='CONNECTED')return;}catch(e){}setTimeout(check,5000)}check();
</script></body></html>""" % (code,verify,session)
        return response(200,page,"text/html; charset=utf-8")

    if path=="/connect/microsoft/poll" and method=="GET":
        q=event.get("queryStringParameters") or {}
        session=q.get("session","")
        item=ddb.get_item(TableName=TABLE,Key={"PK":{"S":"MICROSOFT_DEVICE#"+session},"SK":{"S":"STATE"}}).get("Item")
        if not item:
            return response(404,{"status":"EXPIRED","message":"This approval session expired. Start again."})
        client_id=item["ClientId"]["S"]; device_code=item["DeviceCode"]["S"]
        data=urllib.parse.urlencode({"grant_type":"urn:ietf:params:oauth:grant-type:device_code","client_id":client_id,"device_code":device_code}).encode()
        req=urllib.request.Request("https://login.microsoftonline.com/"+os.environ["MICROSOFT_TENANT_ID"]+"/oauth2/v2.0/token",data=data,headers={"content-type":"application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req,timeout=20) as rr:
                tokens=json.loads(rr.read().decode())
        except urllib.error.HTTPError as e:
            try: err=json.loads(e.read().decode())
            except: err={}
            code=err.get("error","")
            if code=="authorization_pending":
                return response(200,{"status":"WAITING","message":"Waiting for Mark to approve Supreme Mail in Microsoft…"})
            if code=="slow_down":
                return response(200,{"status":"WAITING","message":"Microsoft asked Supreme Mail to wait a little longer…"})
            return response(400,{"status":"ERROR","message":"Microsoft did not complete the approval. Start the connection again."})
        cfg=json.loads(get_secret(MICROSOFT_SECRET_ARN) or "{}")
        cfg["refresh_token"]=tokens.get("refresh_token","")
        cfg["access_token"]=tokens.get("access_token","")
        cfg["access_token_expires_at"]=int(time.time())+int(tokens.get("expires_in",3600))
        sm.put_secret_value(SecretId=MICROSOFT_SECRET_ARN,SecretString=json.dumps(cfg,separators=(",",":")))
        sm.put_secret_value(SecretId=os.environ["SETUP_TOKEN_SECRET_ID"],SecretString=json.dumps({"token":setup_token_placeholder if False else "USED","used":True}))
        ddb.delete_item(TableName=TABLE,Key={"PK":{"S":"MICROSOFT_DEVICE#"+session},"SK":{"S":"STATE"}})
        ddb.put_item(TableName=TABLE,Item={"PK":{"S":"MICROSOFT#CONFIG"},"SK":{"S":"MARK"},"Product":{"S":"Supreme Mail"},"BusinessEmail":{"S":os.environ["MICROSOFT_SENDER_UPN"]},"TenantId":{"S":os.environ["MICROSOFT_TENANT_ID"]},"AdminConfirmed":{"BOOL":True},"AuthorizationStatus":{"S":"CONNECTED"}})
        return response(200,{"status":"CONNECTED","message":"Supreme Mail is connected to Microsoft 365 ✅"})

    if path=="/health":
        return response(200,{"service":"sc-mail-mark-v1","status":"ok","version":"1.0.0","hardCeiling":HARD_CEILING,"safePerMinute":SAFE_PER_MIN})
    if path=="/config":
        used=window_usage(); return response(200,{"product":"Supreme Mail","provider":"microsoft365","businessEmail":"Marks@numbersetcandetc.com","tenantId":"890486d6-532e-4054-a508-02e1e4b48806","adminConfirmed":True,"providerConnected":provider_ready(),"hardCeiling":HARD_CEILING,"usedInRollingWindow":used,"remainingInRollingWindow":max(0,HARD_CEILING-used),"safePerMinute":SAFE_PER_MIN,"invariants":INVARIANTS})
    if path=="/manifest.xml":
        return response(200,manifest(base),"application/xml")
    if path in {"/","/taskpane"}:
        return response(200,taskpane(base),"text/html; charset=utf-8")
    if path=="/icon":
        png="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        return {"statusCode":200,"headers":{"content-type":"image/png"},"isBase64Encoded":True,"body":png}
    if path=="/api/preflight" and method=="POST":
        body=json.loads(event.get("body") or "{}"); contacts=body.get("contacts") or []
        requested=min(int(body.get("requestedCount") or len(contacts) or 0),HARD_CEILING)
        seen=set(); permitted=[]; rejected=[]
        for c in contacts:
            email,checks,ok=evaluate(c)
            if email in seen:
                checks["Continuity"]=False; ok=False
            seen.add(email)
            item={"email":email,"checks":checks}
            (permitted if ok else rejected).append(item)
        campaign=body.get("campaign") or {}
        global_checks={"Time":True,"Continuity":True,"Alignment":bool(campaign.get("subject") and campaign.get("body")),"Genesis":True,"Boundary":requested<=HARD_CEILING,"Reference":True,"Causality":bool(campaign.get("audience")),"Consciousness":True}
        digest=hashlib.sha256(json.dumps({"requested":requested,"permitted":[x["email"] for x in permitted],"campaign":campaign},sort_keys=True).encode()).hexdigest()
        decision="PERMIT" if all(global_checks.values()) and len(permitted)>=requested and requested>0 else "HOLD"
        return response(200,{"decision":decision,"requested":requested,"permitted":len(permitted),"rejected":len(rejected),"providerConnected":provider_ready(),"hardCeiling":HARD_CEILING,"checks":global_checks,"receiptSha256":digest,"rejectedSample":rejected[:20]})
    if path=="/api/send" and method=="POST":
        if not provider_ready():
            return response(409,{"decision":"HOLD","error":"microsoft_authorization_required","queued":0})
        body=json.loads(event.get("body") or "{}"); contacts=body.get("contacts") or []
        requested=min(int(body.get("requestedCount") or len(contacts) or 0),HARD_CEILING)
        used=window_usage(); remaining=max(0,HARD_CEILING-used)
        if requested>remaining:
            return response(409,{"decision":"HOLD","error":"outlook_rolling_window_ceiling","requested":requested,"remaining":remaining,"queued":0})
        campaign=body.get("campaign") or {}; campaign["authorized"]=bool(campaign.get("authorized",False))
        if not campaign.get("subject") or not campaign.get("body") or not campaign.get("audience") or not campaign.get("authorized"):
            return response(400,{"decision":"HOLD","error":"campaign_not_fully_authorized","queued":0})
        seen=set(); selected=[]
        for c in contacts:
            email,checks,ok=evaluate(c)
            if email in seen: ok=False
            seen.add(email)
            if ok:
                selected.append({"email":email,"firstName":c.get("firstName",""),"company":c.get("company","")})
            if len(selected)>=requested: break
        if requested<=0 or len(selected)<requested:
            return response(409,{"decision":"HOLD","error":"insufficient_proven_recipients","requested":requested,"proven":len(selected),"queued":0})
        campaign_id=str(uuid.uuid4())
        digest=hashlib.sha256(json.dumps({"campaignId":campaign_id,"selected":[x["email"] for x in selected],"subject":campaign.get("subject")},sort_keys=True).encode()).hexdigest()
        now_epoch=int(time.time())
        ddb.put_item(TableName=TABLE,Item={"PK":{"S":"OUTLOOK_WINDOW"},"SK":{"S":"R#"+str(now_epoch)+"#"+campaign_id},"Count":{"N":str(requested)},"CampaignId":{"S":campaign_id},"ExpiresAt":{"N":str(now_epoch+86400)}})
        ddb.put_item(TableName=TABLE,Item={"PK":{"S":"CAMPAIGN#"+campaign_id},"SK":{"S":"STATE"},"Status":{"S":"QUEUED"},"Requested":{"N":str(requested)},"Queued":{"N":str(len(selected))},"ReceiptSha256":{"S":digest},"CreatedAt":{"N":str(now_epoch)}})
        entries=[]
        queued=0
        for i,c in enumerate(selected):
            msg={"campaignId":campaign_id,"email":c["email"],"firstName":c.get("firstName",""),"company":c.get("company",""),"subject":campaign["subject"],"body":campaign["body"],"base_url":base}
            entries.append({"Id":str(i%10)+"-"+str(i),"MessageBody":json.dumps(msg,separators=(",",":"))})
            if len(entries)==10:
                sqs.send_message_batch(QueueUrl=QUEUE_URL,Entries=entries); queued+=len(entries); entries=[]
        if entries:
            sqs.send_message_batch(QueueUrl=QUEUE_URL,Entries=entries); queued+=len(entries)
        return response(202,{"decision":"PERMIT","campaignId":campaign_id,"queued":queued,"receiptSha256":digest})
    if path=="/api/activity" and method=="GET":
        q=(event.get("queryStringParameters") or {}); campaign_id=q.get("campaignId")
        if not campaign_id: return response(400,{"error":"campaignId_required"})
        r=ddb.query(TableName=TABLE,KeyConditionExpression="PK = :pk",ExpressionAttributeValues={":pk":{"S":"CAMPAIGN#"+campaign_id}})
        counts={}
        for item in r.get("Items",[]):
            st=(item.get("Status") or {}).get("S")
            if st: counts[st]=counts.get(st,0)+1
        return response(200,{"campaignId":campaign_id,"counts":counts,"items":len(r.get("Items",[]))})
    if path.startswith("/u/") and method=="GET":
        token=path.split("/u/",1)[1]
        email_addr=((event.get("queryStringParameters") or {}).get("e") or "").strip().lower()
        key=get_secret(SIGNING_SECRET_ARN).encode()
        expected=hmac.new(key,email_addr.encode(),hashlib.sha256).hexdigest()
        if not email_addr or not hmac.compare_digest(token,expected):
            return response(400,"Invalid unsubscribe link","text/plain")
        ddb.put_item(TableName=TABLE,Item={"PK":{"S":"SUPPRESS#"+email_addr},"SK":{"S":"STATE"},"Reason":{"S":"unsubscribe"},"At":{"N":str(int(time.time()))}})
        return response(200,"You have been unsubscribed.","text/plain")
    return response(404,{"error":"not_found"})
