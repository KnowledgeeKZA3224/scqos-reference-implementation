#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
items = []
for path in sorted((root / "run-evidence").glob("*")):
    if path.is_file():
        data = path.read_bytes()
        items.append({"file": path.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
summary = {"schema": "scqos.acs.evidence-manifest.v1", "artifacts": items}
out = root / "run-evidence" / "MANIFEST.json"
out.write_text(json.dumps(summary, indent=2, sort_keys=True))
print(json.dumps(summary, indent=2))
