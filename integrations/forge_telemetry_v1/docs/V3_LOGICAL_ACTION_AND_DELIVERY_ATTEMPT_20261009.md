# Proposed Forge V3 identity and denied-path reference — 2026-10-09

> **Synthetic-only, offline reference. Not deployed to Oscar's Node receiver, not independently witnessed, not a bank/payment integration.** This document preserves the previous V1 and proposed V2 reference unmodified until the multi-owner wire contract is agreed. See `staging_contract_v3.py` and `tests/test_staging_contract_v3.py`.

## Why another versioned contract is necessary

The earlier synthetic V2 proof used `transaction_id == nonce`. This makes a *single delivery attempt* appear identical to the logical transaction: using a fresh nonce to retry creates a different transaction identity. Jerry's October 9 cross-system handoff instead requires (1) a stable identity for one *logical action*, (2) separate scenario/transition identifiers, and (3) a **fresh delivery nonce for every new attempt**. These must not silently collapse into one field.

The proposed V3 envelope makes them explicit:

- `logical_action_sha256`: fixed digest for a declared, canonical bounded action. Treat only as a *claimed* digest until independent source and signature verification.
- `transaction_id`: stable UUID for the same logical transaction across receipt readback and uncertain delivery; a distinct test scenario uses a different transaction ID.
- `scenario_id`: a UUID binding PERMIT/HOLD/REJECT synthetic scenario.
- `transition_id`: decision-transition UUID. Identity for a new decision, not blanket continuing authority.
- `attempt_nonce`: a fresh UUID for every transmission attempt; included in the **HMAC-signed raw UTF-8 JSON bytes**, and must equal the `X-Forge-Nonce` header.
- `decision`: `PERMIT`, `HOLD`, or `REJECT` with distinct claimed effect.
- `gekyume_precheck_sha256`, `scqos_decision_sha256`, `observer_receipt_sha256`, optional `execution_receipt_sha256`: placeholders for **external verified evidence digests**. **This reference does not validate the external signature chains or independent custody of these hashes.**
- `observed_effect`: `ISOLATED_SYNTHETIC_EFFECT` for a PERMIT claim, `NO_PROTECTED_EFFECT` for HOLD/REJECT. A HOLD/REJECT carrying an execution-receipt digest is rejected.

**HMAC and storage:** `sign_envelope` signs the exact canonical raw bytes; `verify_signed_envelope` checks signature, app ID, signed nonce↔header agreement, strict schema/UTF-8, freshness and decision consistency. `SyntheticV3Store` uses SQLite in WAL with `synchronous=FULL` and an immediate atomic transaction to reject repeated attempt nonce (401 semantic code) and repeated transaction ID with a *new* nonce (409 semantic code). Receipt readback survives process restarts. The store records metadata only, no bank writes.

**Critical limit:** the synthetic reference is **NOT an HTTP server**. The 401/409 names are *contract error markers* for Oscar to agree and implement; they are not evidence his Node service returns those codes. The SQLite reference readback sets `settlement=False` and `independent_witness_verified=False` even for a reported PERMIT. It would be unsafe to call this `SEALED` or `COMMITTED` without independently verified protected consequences.

## Safe status and transport gate

As of 2026-10-09, original Forge raw IP TCP:443 could not be reached from our HP. The first public `loca.lt` tunnel returned a provider `503 Tunnel Unavailable`. Oscar's replacement `https://early-olives-marry.loca.lt/` DNS resolved to the tunnel edge, but two non-mutating GETs (`/health`, `/v1/evidence/ingest`) timed out after ten seconds with zero response bytes. **No HMAC secret, bearer token, signed POST, bank/ERP action, Lambda Invoke, or security bypass occurred.** Tunnel edge TLS is not end-to-end origin authentication. Stop before any signed POST; require controlled private ingress/mTLS or stable authenticated cloud transport.

The public repo has *no* live receiver credentials. Shared secrets, signer identities, customer material, Jerry's locally held RINZLER evidence and private receipts must stay in separate authorized private channels.

## Reproducible tests

From repo root:

```bash
python3 -m unittest discover -s integrations/forge_telemetry_v1/tests -v
```

Observed locally after adding V3: **44/44** tests passed, including the 29 earlier V1/V2 tests and 15 additional V3 identity, denied-path, signature, nonce/replay, and SQLite restart tests. No local bank execution or remote Forge interoperability occurred.

## Outstanding owners and acceptance

1. **Oscar:** confirm real Node route and the cross-language raw byte body, app ID, signed nonce, and status/readback scheme; eliminate disposable tunnel 503/408; demonstrate atomic server-side nonce+transaction dedupe, crash durability, and an independently authenticated endpoint. Prefer stable, controlled HTTPS ingress or an outbound authenticated AWS work/response transport that doesn't expose Penguin behind NAT.
2. **Jerry:** preserve his single-host RINZLER proof archive with its SHA-256 and signed local receipt set; supply a reproducible credential-free evidence excerpt or externally verifiable independent witness. An AWS synthetic test still needs separately bounded, explicitly approved IAM/KMS/test writer and stop conditions. His Windows/WSL2 tests do not constitute kernel-level enforcement.
3. **Founder/integration:** validate externally provided GEKYUME/SCQOS/observer signatures against **separate trust roots**, and the exact same transaction/scenario/transition identity across all systems. Demonstrate true protected PERMIT or independently observed HOLD/REJECT no-effect before treating any returned evidence as final.
4. **Release decision:** synthetic-only until origin and contract are verified. The October 16 target remains a future milestone, not a completed bank settlement.

In the eight-invariant model: Time=timestamp/replay, Continuity=stable identity/restart, Alignment=decision versus actual effect, Genesis=actor/source/signer, Boundary=exact authorized action/no money, Reference=canonical digest/receipts, Causality=independent negative control and observed effect, Consciousness/Coherence=independent agreement and closure. Code enforces only its explicitly tested subset; those names alone never establish independent proof.
