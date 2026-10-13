# Durable capture boundary — reference contract

This package implements five fail-closed **reference** decisions for the next
SCQOS persistence phase. It does not modify the deployed Supreme Mind governor,
the live DynamoDB tables, or Jerry's separate PostgreSQL 16 implementation.

| Boundary | End state | Implemented here | Production closure still required |
| --- | --- | --- | --- |
| Authority lineage | Every capture grant has a trusted origin, scope, time window and revocation check | `authority_decision` validates root-to-leaf delegation | Trusted root registry, authenticated grants and transactional revocation lookup |
| Frozen intent | One commitment binds proposed bytes, evidence, authority, policy, prior state, target and transition | `freeze_intent` and `precommit_decision` | Use the canonical SCQOS-C14N-JCS-NFC-1 identity; enforce conditional write and one-time transition ID in the same PostgreSQL transaction |
| Effect witness | Independently observed durable result matches the approved transition | `witness_effect` checks readback and transition identity | Separate read path or witness, durable signed witness receipt, and quarantine on mismatch |
| Shadow learning | Candidate lesson changes are visible before promotion | `compare_shadow` returns the exact differing decisions and always HOLD | Replay a fixed corpus from frozen production inputs; governed human/policy promotion transition |
| Causal repair | Invalidated state exposes every descendant consequence | `blast_radius` discovers reachable descendants, including cycles | Persist complete dependency edges, classify each effect, execute governed compensation and record closure receipts |

All five are evaluated against Time, Continuity, Alignment, Genesis, Boundary,
Reference, Causality, and Consciousness at the production gate. These local
functions express only the narrow predicates their names specify; a successful
local decision is **not** a production PERMIT. The PostgreSQL adapter must keep
the precommit compare-and-write atomic. A readback witness detects damage but
cannot undo a bad external effect. Revocation needs a current authoritative
lookup, not only a caller supplied set.

Run: `python3 -m unittest tests.test_capture_boundary -v`.
