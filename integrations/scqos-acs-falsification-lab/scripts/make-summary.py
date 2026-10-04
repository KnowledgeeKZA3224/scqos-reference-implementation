from __future__ import annotations
import hashlib, json, time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = [
    root / "run-evidence/local.json",
    root / "run-evidence/live-scqos.json",
    root / "run-evidence/cloud-to-terminal.json",
]
summary = {"schema":"scqos.acs.falsification.summary.v1","generated_at":time.time(),"artifacts":[]}
for path in files:
    data = path.read_bytes()
    value = json.loads(data)
    summary["artifacts"].append({
        "path": str(path.relative_to(root)),
        "sha256": hashlib.sha256(data).hexdigest(),
        "all_pass": value.get("all_pass"),
        "mode": value.get("mode"),
    })
summary["all_pass"] = all(x["all_pass"] is True for x in summary["artifacts"])
out = root / "run-evidence/SUMMARY.json"
out.write_text(json.dumps(summary, indent=2, sort_keys=True))
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary["all_pass"] else 2)
