# GEKYUME × SCQOS × The Forge telemetry v1
**Contract:** SPEC-WA-TELEMETRY-V1 | **Owner:** Supreme Computation LLC | **Target:** October 16, 2026

Fail-closed adapter; no live payments, external HTTP calls or deployed service. Requires independently authentic GEKYUME PERMIT, SCQOS PERMIT and execution COMMITTED receipts for the *same* transaction before producing JSON/HMAC request bytes.

From repo root, run:

    python3 -m unittest discover -s integrations/forge_telemetry_v1/tests -v
    python3 -m integrations.forge_telemetry_v1.demo

Wire details: HTTPS POST /webhook, Content-Type application/json, X-Forge-Tenant-ID FORGE-WA-001, X-Signature-HMAC-256 lowercase hex HMAC-SHA256 over exact UTF-8 JSON bytes (pending Oscar confirmation). Only synthetic test fixtures are available. Under no circumstances should test-issued receipts be treated as authority to move money.

See docs/ARCHITECTURE.md for AWS inventory, eight-invariant proof, security threat model, cost controls, technical acceptance and remaining HOLD gates.
