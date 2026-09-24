from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from shadow_clone.protocol import (
    evaluate_clone_birth,
    make_clone_birth,
    role_ids_from_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "supreme_mind/v1/supreme_mind_manifest.json").read_text())
VALID_ROLE_IDS = role_ids_from_manifest(MANIFEST)

TASKS = [
    (
        "R54",
        "governance",
        "Verify Azure policy assignments and governed resource inventory.",
        [
            "bash",
            "-lc",
            "az policy assignment list --resource-group rg-supreme-computation-core -o json && "
            "az resource list -g rg-supreme-computation-core -o json",
        ],
    ),
    (
        "R55",
        "continuity",
        "Verify live SCQOS Container App revision, image, and health.",
        [
            "bash",
            "-lc",
            "az containerapp show -g rg-supreme-computation-core -n scqos-governance-api -o json && "
            "F=$(az containerapp show -g rg-supreme-computation-core -n scqos-governance-api "
            "--query properties.configuration.ingress.fqdn -o tsv) && "
            "curl -fsS --max-time 20 https://$F/v1/health",
        ],
    ),
    (
        "R57",
        "institutional-memory",
        "Freeze Git and Azure deployment state for migration evidence.",
        [
            "bash",
            "-lc",
            "git status --short && git log -1 --oneline origin/main && "
            "az acr repository show-tags -n acrscqosc9f1a2b2 --repository scqos-runtime -o json",
        ],
    ),
    (
        "R58",
        "council",
        "Independently verify queue, signing key, and runtime identity surfaces.",
        [
            "bash",
            "-lc",
            "az servicebus queue list -g rg-supreme-computation-core "
            "--namespace-name sb-scqos-c9f1a2b2 -o json && "
            "az keyvault key show --vault-name kv-scqos-c9f1a2b2 "
            "-n scqos-signing-key -o json && "
            "az identity show -g rg-supreme-computation-core -n id-scqos-runtime -o json",
        ],
    ),
]


def run_clone(role_id: str, lane: str, objective: str, command: list[str]) -> dict:
    birth = make_clone_birth(
        role_id=role_id,
        task_id=f"azure-migration-{lane}",
        business_id="supreme-computation",
        objective=objective,
        expected_output="Current live-state evidence and bounded verification.",
        evidence_refs=[
            "azure:rg-supreme-computation-core",
            "git:scqos-reference-implementation",
        ],
        requested_action="inspect",
        why_multiply=(
            "Parallel independent verification shortens migration closure "
            "without merging authority."
        ),
        ttl_seconds=900,
        max_children=0,
        spend_limit_usd="0.00",
    )
    decision = evaluate_clone_birth(birth, valid_role_ids=VALID_ROLE_IDS)
    state = decision.get("decision") or decision.get("state")
    if state != "PERMIT":
        return {
            "role_id": role_id,
            "lane": lane,
            "state": state,
            "birth": birth,
            "qualification": decision,
        }

    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    return {
        "role_id": role_id,
        "lane": lane,
        "state": "COMPLETED" if completed.returncode == 0 else "FAILED",
        "birth": birth,
        "qualification": decision,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-20000:],
        "stderr": completed.stderr[-4000:],
    }


def main() -> int:
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(run_clone, *task) for task in TASKS]
        for future in as_completed(futures):
            results.append(future.result())

    evidence = ROOT / "proofs/azure/2026-09-24-shadow-clones"
    evidence.mkdir(parents=True, exist_ok=True)
    receipt = evidence / "TERMINAL_SHADOW_CLONE_RECEIPTS.json"
    receipt.write_text(json.dumps(results, indent=2, default=str) + "\n")

    summary = [
        {
            "role_id": item["role_id"],
            "lane": item["lane"],
            "state": item["state"],
            "birth_decision": (
                item["qualification"].get("decision")
                or item["qualification"].get("state")
            ),
        }
        for item in results
    ]
    print(json.dumps(summary, indent=2))
    return 0 if all(item["state"] == "COMPLETED" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
