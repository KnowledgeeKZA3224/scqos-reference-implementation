# Supreme Computation × Azure — Totality Receipt
Generated from live Azure execution on 2026-09-24 UTC (September 23, 2026 America/Phoenix).

- Time → governed state is timestamp-tagged and the transition receipt records when the foundation was created.
- Continuity → SC continuity tags + `CanNotDelete` lock `sc-continuity-lock` on `rg-supreme-computation-core`.
- Alignment → coherence-first tags and CLI defaults bound to West US 3 / the governed resource group.
- Genesis → governed resources must present genesis evidence before execution.
- Boundary → West US 3/global only; public IPs denied; subnet default outbound disabled; Internet egress denied.
- Reference → SC reference tags plus Azure resource/policy IDs act as authoritative receipts.
- Causality → pre-execution proof is enforced by Azure Policy before resource creation.
- Consciousness / Observer → observer evidence is required; `id-sc-governance-observer` has Reader only on the governed resource group.

Governance initiative: Supreme Computation Totality Governance
Assignments enforced: `sc-totality-enforced`, `sc-eight-invariants-gate`, `sc-boundary-gate`
Private network: `vnet-sc-core` — 10.42.0.0/16
Subnets: `snet-app` 10.42.1.0/24; `snet-data` 10.42.2.0/24; `snet-management` 10.42.3.0/24
NSG: `nsg-sc-private` — explicit Deny Internet Egress
Proof allow: exit 0
Proof missing invariants: exit 1 / denied by policy
Proof wrong region: exit 1 / denied by policy
Proof public IP: exit 1 / denied by policy
Budget template: `budget.json` stages a $25/month guardrail, but live verification found no active Azure budget object yet.
No VM, SQL database, public IP, NAT Gateway, or paid compute was created during this foundation pass.
Raw templates, logs, and SHA-256 hashes are stored beside this receipt.
