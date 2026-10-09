# Supreme Computation LLC — The Forge telemetry integration
**SPEC-WA-TELEMETRY-V1 | Engineering review 2026-10-09 | Demo target 2026-10-16**

## Verified live source state
AWS account 327453383912, region us-east-1, contains active Lambda functions: gekyume-universal-gate-v1, gekyume-bank-demo-v1, scqos-authority-witness-v1, plus workbench witness functions. AWS HTTP API vakkhcgpuk exposes GET /health and POST /evaluate, /execute and /reconcile, each using AWS_IAM authorization. GEKYUME uses DynamoDB receipt tables gekyume-universal-receipts-v1 and gekyume-bank-receipts-v1; an SCQOS authority-witness table exists. Existing evidence S3 buckets include gekyume-proof-327453383912-us-east-1 and gekyume-audit-327453383912-us-east-1. These inventory observations do NOT prove end-to-end trusted transaction/witness integration.

Existing GitHub reference source has a GEKYUME universal gate. A distinct local GEKYUME ledger simulation is not a banking execution system.

## End-to-end authority boundary
1. Untrusted payment request reaches GEKYUME. The financial policy gate must independently validate payment intent, amount, destination, limits and provenance. If not PERMIT, stop.
2. SCQOS independently evaluates admissibility and the eight invariants against the same immutable transaction digest. If not PERMIT, stop.
3. An outside payment executor performs a separately authorized payment and produces a independently authentic post-execution COMMITTED proof. If proof unavailable, HOLD. The telemetry adapter does NOT move funds.
4. Adapter validates three independently signed bound receipts: GEKYUME PERMIT, SCQOS PERMIT, EXECUTION COMMITTED, verifies time order and expiration, and verifies that the payment fields are identical across trust domains.
5. Adapter creates deterministic UTF-8 JSON with top-level telemetry_id, timestamp, gekyume_validation, scqos_evaluation and transaction_data.
6. Adapter signs the exact transmitted body with HMAC-SHA256 and sends only to the pinned The Forge HTTPS POST /webhook endpoint, with Content-Type application/json, X-Forge-Tenant-ID FORGE-WA-001 and X-Signature-HMAC-256. This external send is NOT wired in this release.
7. The Forge verifies tenant, HMAC, time, identity, replay controls and schema. Its signed acknowledgment and ledger commitment proof must be reconciled to the original payment proof.

A self-declared PASSED status, a numerical admissibility score or a locally generated sample must NEVER constitute authority.

## Eight invariant table
| Invariant | Proof condition | Reject/HOLD behavior |
|---|---|---|
| Time | Bounded UTC timestamp, no stale proof | no send |
| Continuity | Identical transaction SHA256 across stages; durable delivery record | no send |
| Alignment | All three domain outcomes agree | reject |
| Genesis | Proven source for each authorization/execution domain | reject |
| Boundary | Tenant-scoped cryptography and least-privilege; no payment capability in publisher | reject |
| Reference | Pinned contract, engine IDs, policy version and transaction digest | reject |
| Causality | Execution cannot predate valid pre-execution permits | reject |
| Consciousness/Coherence | Aggregate decision respects all constraints, including uncertain/unknown states | HOLD |

## Wire contract captured from Oscar's four-page preview
The provided screenshots display HTTPS POST /webhook, the required tenant/signature headers, and canonical field names. Synthetic sample GBP amount 1250.00, private synthetic IP, ARN, account ID and device fingerprint. The full original four-page PDF was not supplied as machine-readable source. Therefore signature canonicalization, accepted response code/body, idempotency, precise HTTPS origin and potential supplemental requirements remain unverified.

**Must confirm with Oscar through a secure process:** real HTTPS hostname, sandbox tenant, shared HMAC key delivery, exact HMAC body canonicalization, key rotation, signature encoding, time tolerance, retries and idempotent duplicate semantics, receipt/ledger-readback format, complete schema and legal basis for transmitting account/device/IP fields.

## AWS-grade target topology (design, NOT deployed)
- Existing IAM-authenticated GEKYUME API and SCQOS authority witness remain independent; do not expose GEKYUME /execute to The Forge.
- Dedicated post-commit adapter Lambda with scoped IAM: can verify receipts and publish bounded telemetry, cannot execute payments.
- Separate KMS-backed signing/verifying rights for trusted financial and admissibility receipts. Use Secrets Manager or KMS GenerateMac for The Forge tenant secret; never embed cloud secrets in Git or test fixtures.
- SQS FIFO + dead-letter queue for tenant/transaction ordered delivery; DynamoDB conditional event ID state machine RESERVED / ACKED / UNCERTAIN. No optimistic or automatic retry of unknown outcomes absent server-side idempotency. Exactly-once processing requires receiver guarantees.
- Signed receipts with SHA-256 provenance; S3 SSE-KMS/retention rules after policy approval; no raw customer data or keys in logs.
- CloudWatch structured telemetry and alarms for HOLD, DENY, queue age, proof failure, latency, failure mode, error budget, costs. Least-privilege network egress to allowlisted TLS host; block SSRF.
- Enterprise stages: sandbox → canary → load test → regional failure/reconciliation → security audit → approved production. Define and measure p95/p99, throughput, RPO, RTO and cost/transaction before calling the system globally scaled.
- Data minimization: tokenize/obfuscate ARN/account/device/IP where The Forge contract allows; establish retention, residency and cross-border privacy controls.

## Test and acceptance protocol
Run synthetic signature roundtrip and negative cases: tampered body, mismatched tenant, GEKYUME false, SCQOS unauthorized, forged receipts, stale receipts, altered amount, missing receipt, bad score/currency/precision, replay attempt, ambiguous acknowledgment and commit preceding authorization. Run with no network and no real money.

Before real pilot: demonstrate three genuine signed AWS-origin receipts bound to one transaction; prove rejection of unauthorized bank execution, actual commit witness and no claim of success before it; verify The Forge's signed ledger acknowledgment and independent readback; run matched baseline, adverse network conditions, regional failover, audited load tests and budget controls.

## Release gates
HOLD-01 complete Oscar interface specification, host and secure tenant secret.
HOLD-02 actual GEKYUME authenticated financial permit and state digest.
HOLD-03 actual SCQOS independently authentic pre-execution admissibility receipt.
HOLD-04 independently witnessed real execution proof and reconciliation semantics.
HOLD-05 The Forge server-side test, replay/idempotency agreement, authoritative acknowledgment.
HOLD-06 deployment approval, budget, privacy, load, DR and pen-testing.
Until all close, status is SYNTHETIC_CONTRACT_VERIFIED, not bank-connected or global-scale certified.
