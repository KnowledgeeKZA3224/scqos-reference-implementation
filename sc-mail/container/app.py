import os, json, time, urllib.parse, urllib.request, urllib.error, hashlib, base64, secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import boto3

REGION=os.environ.get("AWS_REGION","us-east-1")
TABLE=os.environ.get("TABLE_NAME","sc-mail-mark-v1-state")
MS_SECRET=os.environ.get("MICROSOFT_SECRET_ARN","arn:aws:secretsmanager:us-east-1:327453383912:secret:sc-mail/mark/microsoft-Er9iLZ")
SETUP_SECRET=os.environ.get("SETUP_TOKEN_SECRET_ID","supreme-mail/mark/setup-token")
TENANT=os.environ.get("MICROSOFT_TENANT_ID","890486d6-532e-4054-a508-02e1e4b48806")
CLIENT_ID=os.environ.get("MICROSOFT_CLIENT_ID","93df0029-70fd-41c3-9640-262cb69f224b")
SENDER=os.environ.get("MICROSOFT_SENDER_UPN","Marks@numbersetcandetc.com")
CALLBACK=os.environ.get("MICROSOFT_CALLBACK_URI","https://v12t2f3nla.execute-api.us-east-1.amazonaws.com/connect/microsoft/callback")

ddb=boto3.client("dynamodb",region_name=REGION)
sm=boto3.client("secretsmanager",region_name=REGION)

def sec(name):
    return json.loads(sm.get_secret_value(SecretId=name).get("SecretString") or "{}")

def setup_ok(tok):
    try:
        x=sec(SETUP_SECRET)
        if x.get("used") or tok != x.get("token"):
            return False
        exp=x.get("expires_at")
        return (not exp) or int(time.time()) < int(exp)
    except Exception as e:
        print("SETUP_CHECK_ERROR",type(e).__name__,str(e)[:400],flush=True)
        return False

def html(msg):
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Supreme Mail</title><style>body{{font-family:Segoe UI,Arial,sans-serif;max-width:720px;margin:48px auto;padding:0 20px;color:#202124;line-height:1.5}}.card{{padding:18px;border-radius:12px;background:#f5f7fb}}</style></head>
<body><h1>Supreme Mail</h1><div class="card">{msg}</div></body></html>"""

class H(BaseHTTPRequestHandler):
    server_version="SupremeMail/1.0"

    def log_message(self, fmt, *args):
        print("HTTP",self.address_string(),fmt%args,flush=True)

    def send(self,status,body,ctype="text/html; charset=utf-8",headers=None):
        if isinstance(body,(dict,list)):
            body=json.dumps(body,separators=(",",":"))
            ctype="application/json"
        raw=body.encode() if isinstance(body,str) else body
        self.send_response(status)
        self.send_header("Content-Type",ctype)
        self.send_header("Cache-Control","no-store")
        self.send_header("Content-Length",str(len(raw)))
        if headers:
            for k,v in headers.items():
                self.send_header(k,v)
        self.end_headers()
        self.wfile.write(raw)

    def parse(self):
        u=urllib.parse.urlsplit(self.path)
        return u.path, urllib.parse.parse_qs(u.query)

    def start_auth(self,tok):
        if not setup_ok(tok):
            return self.send(403,html("This Supreme Mail setup link is invalid or expired."))
        state=secrets.token_urlsafe(24)
        verifier=secrets.token_urlsafe(64)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        ddb.put_item(TableName=TABLE,Item={
            "PK":{"S":"MICROSOFT_BROWSER#"+state},
            "SK":{"S":"STATE"},
            "Verifier":{"S":verifier},
            "ExpiresAt":{"N":str(int(time.time())+900)}
        })
        params={
            "client_id":CLIENT_ID,
            "response_type":"code",
            "redirect_uri":CALLBACK,
            "response_mode":"query",
            "scope":"openid offline_access User.Read Mail.Send Mail.Send.Shared",
            "state":state,
            "code_challenge":challenge,
            "code_challenge_method":"S256",
            "prompt":"select_account"
        }
        url="https://login.microsoftonline.com/"+TENANT+"/oauth2/v2.0/authorize?"+urllib.parse.urlencode(params)
        self.send_response(302)
        self.send_header("Location",url)
        self.send_header("Cache-Control","no-store")
        self.send_header("Content-Length","0")
        self.end_headers()

    def do_GET(self):
        path,q=self.parse()
        if path=="/connect/microsoft/health":
            return self.send(200,{"service":"supreme-mail-auth-container-v1","status":"ok","flow":"authorization_code_pkce","sending_enabled":False})
        if path=="/connect/microsoft":
            return self.start_auth((q.get("token") or [""])[0])
        if path=="/connect/microsoft/poll":
            return self.send(410,{"status":"REPLACED","message":"Supreme Mail now uses normal Microsoft browser sign-in."})
        if path=="/connect/microsoft/callback":
            return self.callback(q)
        return self.send(404,{"error":"not_found","path":path})

    def do_POST(self):
        path,_=self.parse()
        n=int(self.headers.get("Content-Length","0") or "0")
        raw=self.rfile.read(n).decode(errors="ignore")
        if path=="/connect/microsoft/start":
            form=urllib.parse.parse_qs(raw)
            return self.start_auth((form.get("token") or [""])[0])
        return self.send(404,{"error":"not_found","path":path})

    def callback(self,q):
        if q.get("error"):
            desc=(q.get("error_description") or q.get("error") or ["Microsoft rejected the connection."])[0]
            return self.send(400,html("Microsoft blocked the connection:<br><br>"+desc[:900]))
        state=(q.get("state") or [""])[0]
        code=(q.get("code") or [""])[0]
        item=ddb.get_item(TableName=TABLE,Key={"PK":{"S":"MICROSOFT_BROWSER#"+state},"SK":{"S":"STATE"}}).get("Item")
        if not item or not code:
            return self.send(400,html("This Microsoft approval session is invalid or expired. Open the Supreme Mail setup link again."))
        if int(item.get("ExpiresAt",{}).get("N","0")) <= int(time.time()):
            return self.send(400,html("This Microsoft approval session expired. Open the Supreme Mail setup link again."))
        verifier=item["Verifier"]["S"]
        data=urllib.parse.urlencode({
            "grant_type":"authorization_code",
            "client_id":CLIENT_ID,
            "code":code,
            "redirect_uri":CALLBACK,
            "code_verifier":verifier,
            "scope":"openid offline_access User.Read Mail.Send Mail.Send.Shared"
        }).encode()
        req=urllib.request.Request(
            "https://login.microsoftonline.com/"+TENANT+"/oauth2/v2.0/token",
            data=data,
            headers={"content-type":"application/x-www-form-urlencoded"}
        )
        try:
            with urllib.request.urlopen(req,timeout=20) as rr:
                tokens=json.loads(rr.read().decode())
        except urllib.error.HTTPError as ex:
            raw=ex.read().decode(errors="ignore")
            try: err=json.loads(raw)
            except Exception: err={"error":"token_exchange_failed","error_description":raw[:900]}
            print("MICROSOFT_TOKEN_ERROR",json.dumps(err)[:1600],flush=True)
            msg=str(err.get("error_description") or err.get("error") or "Microsoft token exchange failed.")
            return self.send(400,html("Microsoft blocked the connection:<br><br>"+msg[:900]))
        access=tokens.get("access_token","")
        if not access:
            return self.send(400,html("Microsoft returned no usable access token."))
        me_req=urllib.request.Request(
            "https://graph.microsoft.com/v1.0/me?$select=mail,userPrincipalName,id",
            headers={"Authorization":"Bearer "+access}
        )
        try:
            with urllib.request.urlopen(me_req,timeout=20) as rr:
                me=json.loads(rr.read().decode())
        except urllib.error.HTTPError as ex:
            detail=ex.read().decode(errors="ignore")
            print("GRAPH_ME_ERROR",detail[:1600],flush=True)
            return self.send(502,html("Microsoft approved the login, but Supreme Mail could not verify the signed-in identity.<br><br>"+detail[:700]))
        actuals={str(me.get("mail") or "").strip().lower(),str(me.get("userPrincipalName") or "").strip().lower()}
        actuals.discard("")
        observed=me.get("mail") or me.get("userPrincipalName") or "unknown"
        direct_sender=SENDER.lower() in actuals
        cfg=sec(MS_SECRET)
        cfg.update({
            "tenant_id":TENANT,
            "client_id":CLIENT_ID,
            "sender_upn":SENDER,
            "auth_mode":"authorization_code_pkce",
            "authorized_identity":observed,
            "authorized_mail":str(me.get("mail") or ""),
            "authorized_upn":str(me.get("userPrincipalName") or ""),
            "sender_authority_verified":bool(direct_sender),
            "refresh_token":tokens.get("refresh_token",""),
            "access_token":access,
            "access_token_expires_at":int(time.time())+int(tokens.get("expires_in",3600))
        })
        cfg.pop("client_secret",None)
        sm.put_secret_value(SecretId=MS_SECRET,SecretString=json.dumps(cfg,separators=(",",":")))
        setup=sec(SETUP_SECRET)
        setup["used"]=True
        sm.put_secret_value(SecretId=SETUP_SECRET,SecretString=json.dumps(setup,separators=(",",":")))
        ddb.delete_item(TableName=TABLE,Key={"PK":{"S":"MICROSOFT_BROWSER#"+state},"SK":{"S":"STATE"}})
        ddb.put_item(TableName=TABLE,Item={
            "PK":{"S":"MICROSOFT#CONFIG"},
            "SK":{"S":"MARK"},
            "Product":{"S":"Supreme Mail"},
            "BusinessEmail":{"S":SENDER},
            "TenantId":{"S":TENANT},
            "MailboxConfirmed":{"BOOL":True},
            "AuthorizedIdentity":{"S":str(observed)},
            "AuthorizedMail":{"S":str(me.get("mail") or "")},
            "AuthorizedUPN":{"S":str(me.get("userPrincipalName") or "")},
            "SenderAuthorityVerified":{"BOOL":bool(direct_sender)},
            "AuthorizationStatus":{"S":"CONNECTED_DIRECT" if direct_sender else "CONNECTED_NEEDS_SEND_AS_VERIFICATION"}
        })
        if direct_sender:
            return self.send(200,html("Microsoft connection complete ✅<br><br>Supreme Mail is still safely locked until the controlled final send test."))
        return self.send(200,html("Microsoft connection complete ✅<br><br>Supreme Mail is still safely locked because the sending address is different from the signed-in account. The next check is Send As permission."))

if __name__=="__main__":
    port=int(os.environ.get("PORT","8080"))
    print("SUPREME_MAIL_AUTH_START",port,flush=True)
    ThreadingHTTPServer(("0.0.0.0",port),H).serve_forever()
