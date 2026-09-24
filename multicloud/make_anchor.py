#!/usr/bin/env python3
import hashlib,json,subprocess,datetime,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sh(cmd): return subprocess.check_output(cmd,shell=True,text=True).strip()
contract=json.loads((ROOT/"multicloud/continuity_contract.json").read_text())
azure_fqdn=sh("az containerapp show -g rg-supreme-computation-core -n scqos-governance-api --query properties.configuration.ingress.fqdn -o tsv")
azure_health=json.loads(sh(f"curl -fsS --max-time 15 https://{azure_fqdn}/v1/health"))
aws_profile="restored"
aws_arn=sh(f"aws --profile {aws_profile} sts get-caller-identity --query Arn --output text")
payload={
 "contract_id":contract["contract_id"],
 "law":contract["law"],
 "generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "azure":{"fqdn":azure_fqdn,"health":azure_health},
 "aws":{"principal_arn_sha256":hashlib.sha256(aws_arn.encode()).hexdigest()},
 "git_head":sh("git rev-parse HEAD")
}
canon=json.dumps(payload,sort_keys=True,separators=(",",":"))
payload["continuity_anchor_sha256"]=hashlib.sha256(canon.encode()).hexdigest()
out=ROOT/"multicloud/LIVE_CONTINUITY_ANCHOR.json"
out.write_text(json.dumps(payload,indent=2)+"\n")
print(payload["continuity_anchor_sha256"])
