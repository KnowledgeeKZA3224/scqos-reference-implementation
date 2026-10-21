# Forge external staging verification — 2026-10-11

Disposition: HOLD_REAL_FORGE_V3. This record is an external, bounded staging check; it is not a live settlement, signed handoff, independent witness, or production approval.

## Source and immutable context
- Source: direct probes from the owner's connected HP Linux terminal on 2026-10-11, against the public URL Oscar provided in Slack.
- Target: https://staging-api.firewallsflashpoints.com
- The DNS response at probe time was 34.67.179.54. Oscar's earlier Slack report gave 34.67.172.54; reconcile the deployment identity without assuming a cause.
- OpenSSL reported a Let's Encrypt certificate for staging-api.firewallsflashpoints.com, validity 2026-10-11 11:10:38 UTC through 2027-01-09 11:10:37 UTC. Curl SSL verification result: 0.
- Public root GET response Date header: Sun, 11 Oct 2026 16:31:13 GMT.

## Independent network observations
| Request | Result | Meaning |
| --- | --- | --- |
| GET / | 200; JSON status=success, message=Forge Webhook Engine online over HTTPS! | The hostname is publicly reachable through valid TLS. |
| GET /health | 404; Cannot GET /health | Health route reported in previous handoff is not available. |
| OPTIONS /health | 404 | No matching route exposed to OPTIONS. |
| OPTIONS /webhook | 200; Allow: POST | Existing POST route is advertised. |
| OPTIONS /v1/evidence/ingest | 404 | Proposed V3 ingest route is absent. |
| OPTIONS /api/v4/ledger | 404 | Previously reported ledger route is absent to OPTIONS. |
| OPTIONS /v1/evidence/receipt/test-uuid | 404 | Previously reported receipt route is absent to OPTIONS. |
| POST /v1/evidence/ingest | 404; Cannot POST /v1/evidence/ingest | V3 contract cannot be posted to this route. |

## Bounded negative-path verification (critical)
- At 2026-10-11 16:40:34 UTC, one synthetic-only POST was sent to /webhook; payload contained random test ID, HOLD, NO_PROTECTED_EFFECT, moves_funds=false and no actual financial/production information.
- Test request included X-Forge-App-ID and X-Forge-Nonce and deliberately invalid X-Forge-Signature (HMAC-SHA256 set to sixty-four zero hex digits).
- Observed HTTP 200 with body {"received":true}. A fail-closed signed staging ingress should reject this with HTTP 401 rather than acknowledge receipt.
- Conclusion: public handler did not reject this invalidly signed request at the HTTP boundary. Storage, downstream effect, authorization of any separate business lane, and persistence are NOT established by this response. Do not claim it moved money or committed a ledger write.
- An earlier GET /v1/evidence/receipt/not-a-real-id attempt timed out during DNS resolution; it was not counted as an HTTP error.

## Distinct evidence: synthetic reference
- On the HP terminal, fetched PR #26 branch integration/forge-telemetry-20261009 at commit bf7657645d48c5fc4d6bf141d6ce7f8128123404 and ran python3 -m unittest discover -s integrations/forge_telemetry_v1/tests -v.
- Result: 44 tests, all passing, exit 0. This verifies the local Python reference, not Oscar's Node receiver.
- Associated GitHub Actions runs at this code revision: offline synthetic verification 38005962833, main integrity 38005962808, and CI 38005962804 all reported completed success.

## Eight-invariant disposition
1. Time: request/certificate timestamps verified; HMAC freshness/replay enforcement on real receiver NOT verified.
2. Continuity: HTTP root reachable; durable storage, restart recovery and dedupe NOT verified.
3. Alignment: /webhook exposed but previously agreed V3 ingestion/receipt/health interfaces not exposed as expected.
4. Genesis: valid TLS domain only; source app identity/signature rejected? NO, invalid signature was acknowledged, so source authenticity gate FAILED.
5. Boundary: checks used only synthetic fake data; no funds, production data, AWS writes or deployments. Authenticated-ingress fail-closed boundary FAILED.
6. Reference: documented endpoints/results and exact tested PR revision distinguished from live production evidence.
7. Causality: HTTP 200 invalid signature demonstrates acceptance of an unauthenticated delivery at HTTP handler; does not prove protected side effects.
8. Consciousness/Coherence: HOLD_REAL_FORGE_V3 pending repaired receiver and witnessed re-test; production claims prohibited.

## Owner handoff and exit gates
- Oscar notified directly in Slack at https://theforge-2cr5838.slack.com/archives/D0C853LRYKU/p1791737014192529 with exact failure and remedial request.
- Oscar: publish actual versioned POST ingress and /health route, HMAC exact-raw-body verification, app-ID/tenant matching, nonce replay and duplicate rejection, atomic/durable ledger, authenticated receipt retrieval, and nonsecret traces for invalid signature and restart. Confirm canonical version and deployment identity.
- Jerry/integrator: conduct positive and negative bounded HMAC, PERMIT/HOLD/REJECT, replay, duplicate, lost-ack, readback and restart checks after an approved synthetic tenant/key is privately provisioned and routes are corrected.
- AWS scratch write and any further settlement testing remain separately gated by existing owner approvals and budget boundaries. No money movement.

Closure status: PASS_TLS_AND_ROOT; PASS_OFFLINE_44; FAIL_LIVE_V3_ROUTING; FAIL_LIVE_NEGATIVE_SIGNATURE_HTTP_GATE; HOLD_END_TO_END_WITNESS.
