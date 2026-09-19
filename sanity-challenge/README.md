# Supreme Computation × Sanity Context — Totality Evidence Plane

## Plain-English purpose
An AI should not be allowed to turn a plausible sentence into an accepted fact just because it sounds right. Sanity holds structured source material; the agent retrieves that material through Sanity Context; Supreme Computation converts the proposed answer into one transition and checks Time, Continuity, Alignment, Genesis, Boundary, Reference, Causality and Consciousness/Accountability together. The result is PERMIT, HOLD or REJECT, followed by a durable receipt.

## Architecture
Human question → Sanity structured content → Knowledge Base → Sanity Context MCP → agent → AnswerTransitionEnvelope → existing AWS Supreme Totality gate → PERMIT/HOLD/REJECT → answer/consequence → receipt/evidence.

Sanity is the evidence plane, not the authority plane. The existing AWS fail-closed gate remains the consequence boundary.

## Dataset model
- sourceArtifact: provenance, URI, hash, observed time and version.
- claim: current/superseded/disputed/unverified statement with source references and validity window.
- proofReceipt: decision, transition hash and eight-invariant result.
- systemComponent: role and consequence boundary.
- contradiction: conflicting claims and explicit resolution state.

## Knowledge Base / MCP configuration
1. Create or select a Sanity project and production dataset.
2. Import fixtures/public-evidence.ndjson and add the public proof corpus. Never import credentials or private customer material.
3. Create a Sanity Context Knowledge Base backed by this structured content and the public proof sources.
4. Create a Context MCP endpoint backed by the Knowledge Base. Keep the Context Viewer organization token server-side.
5. Set SANITY_CONTEXT_MCP_URL and SANITY_CONTEXT_TOKEN in the AWS agent secret store. Do not commit them.
6. The agent must return source IDs/versions with every factual proposal. Missing, stale or contradictory evidence becomes HOLD; hard invariant failure becomes REJECT.

## Judge flow
Ask an unknown question → inspect retrieved Sanity sources → inspect proposed answer → inspect all eight invariant states → inspect PERMIT/HOLD/REJECT → inspect receipt/hash. A judge must be able to distinguish grounded knowledge from missing, stale, contradictory or boundary-violating evidence.

## Acceptance matrix
valid evidence=PERMIT; stale evidence=HOLD; missing reference=HOLD; contradiction unresolved=HOLD; source superseded=HOLD until current source is bound; replay=REJECT; hard boundary violation=REJECT; valid updated source=PERMIT.

## Deployment blocker discovered from the live AWS account
As of 2026-09-18 the AWS account contains the existing Supreme Totality control plane but no Sanity credential/configuration in Secrets Manager or SSM. Creating a Sanity project/Knowledge Base/MCP and issuing its Context Viewer token requires Sanity account authorization. Everything in this directory is deliberately deploy-ready without inventing credentials.

## Public proof
http://SupremeComputation.org
https://github.com/KnowledgeeKZA3224/scqos-reference-implementation
