# Forge staging handshake — synthetic-only implementation / 2026-10-09

Status: **client reference implemented and locally falsifiable; Oscar's receiver NOT updated or independently verified.** Existing PR #26 still draft. No payments, no live HTTP transmission, no production resources created.

## Source of truth and critical contract delta

Oscar specified `POST https://staging-api.theforge.io/v1/evidence/ingest`, headers `Content-Type: application/json`, `X-Forge-App-ID`, `X-Forge-Signature: hmac-sha256=<hex>`, `X-Forge-Nonce`, and HMAC-SHA256 over the **exact raw UTF-8 request body**. Original PR adapter instead used `/webhook`, `X-Forge-Tenant-ID`, and `X-Signature-HMAC-256`. This is a **proposed V2 client contract**, not a claim that Oscar's live server accepts the new synthetic envelope. His complete body schema and app ID remain to be agreed.

### Fixes achievable from our side
- `staging_contract.py` constructs **offline-only** canonical UTF-8 bytes following verification of distinct GEKYUME, SCQOS and synthetic execution **test receipts**, computes exact raw-body HMAC, emits Oscar's header names and enforces nonce equality with a transaction ID **inside the signed body**. This is essential because his current HMAC does not cover headers directly.
- Restricts the synthetic wire envelope to `SYNTHETIC_ONLY` / `SIMULATED_NO_EXTERNAL_WRITES`; does **not** claim a live payment.
- Rejects bad signature, mismatched app/nonce, stale timestamp, noncanonical JSON, duplicate JSON object keys, and oversized bodies; URL guard never accepts plain HTTP or `-k`.
- `SyntheticReceiptStore` provides indexed SQLite/WAL durable receipts and survives restart; replay returns **409** in the reference. It stores only SHA-256 and metadata, no secret, payment details, or full payload.
- Local readback returns `VALIDATED_ONLY`; the **same machine's readback is not independent external witnessing**.
- Tests: `python3 -m unittest discover -s integrations/forge_telemetry_v1/tests -v` from repo root.

### Oscar-owned mandatory receiver work
1. Publish/repair DNS and inbound network route; obtain valid CA certificate with Certbot (or a specifically trusted private CA). **No `--insecure`, `-k`, or disabled certificate/hostname verification.**
2. Agree on actual versioned request body/schema and staging app ID; implement exact canonical bytes and HMAC interop with a nonsecret cross-language test vector. Remove unused contradictory header aliases.
3. Enforce signature, timestamp, nonce-to-body binding, replay and transaction uniqueness atomically against a durable store **before** reporting accepted status. Persist across PM2 restart. Return 401 invalid signature/nonce, 409 duplicate; a repeated POST must create no new effect.
4. Use a memory-bounded database (SQLite or similar), not an in-memory full ledger. Add authenticated GET receipt by ID (and access-control tests). Return `VALIDATED_ONLY` for validation with no ledger write, **not** `SEALED`. To claim a genuine sealed record, persist an append-only digest commitment and make it independently verifiable.
5. Provide a verifiable failure-mode bundle: bad signature, replay, wrong nonce/app ID, stale timestamp, duplicate request, restart, and authenticated readback. Never publish shared secrets in Slack.

### Connected-environment observations
AWS Lambda configurations of GEKYUME universal/execution gate and SCQOS authority witness show Active/Successful, **not genuine financial settlement**. On user's connected HP Linux terminal, `staging-api.theforge.io` failed ordinary DNS lookup and direct TCP to the supplied 34.219.182.104:443 timed out (2026-10-09). No transmission was attempted.

### Exit gates
- **SYNTHETIC_CONTRACT_TESTED** after repeatable local code+tests+CI.
- **RECEIVER_INTEROPERABLE** only after Oscar's trusted TLS, schema, atomic dedupe, independent readback and authentic positive/negative endpoint receipts are observed from our side.
- **GENUINE_LIVE_SETTLEMENT** only after independent authority/execution and third-party witness on the same real transaction; requires separate approval, privacy and budgets.

This is an integration protocol and reference verifier, not a drop-in patch for Oscar's Node service.
