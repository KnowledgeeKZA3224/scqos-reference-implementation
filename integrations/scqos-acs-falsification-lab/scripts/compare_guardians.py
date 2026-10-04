#!/usr/bin/env python3
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sc_path = root / "run-evidence" / "live-scqos.json"
agt_path = root / "run-evidence" / "agt-reference.json"
sc = json.loads(sc_path.read_text())
agt = json.loads(agt_path.read_text())
by_sc = {x["name"]: x for x in sc["probes"]}
by_agt = {x["name"]: x for x in agt["probes"]}
rows=[]
for name in sorted(set(by_sc) | set(by_agt)):
    a=by_sc.get(name,{})
    b=by_agt.get(name,{})
    rows.append({
        "probe": name,
        "expected": a.get("expected") or b.get("expected"),
        "scqos_observed": a.get("observed"),
        "scqos_pass": a.get("passed"),
        "agt_observed": b.get("observed"),
        "agt_pass_under_same_lab_probe": b.get("passed"),
    })
out={
    "schema":"scqos.acs.differential.v1",
    "claim_boundary":"Same laboratory probes only; this is not an official ACS certification score for either implementation.",
    "scqos":{"passed":sc["passed"],"total":sc["total"]},
    "agt":{"passed":agt["passed"],"total":agt["total"]},
    "rows":rows,
}
path=root/"run-evidence"/"differential.json"
path.write_text(json.dumps(out,indent=2,sort_keys=True))
print(json.dumps({"scqos":out["scqos"],"agt":out["agt"],"rows":len(rows)},indent=2))
