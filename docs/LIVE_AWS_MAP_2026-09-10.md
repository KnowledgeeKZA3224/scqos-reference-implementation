# Live AWS Map — September 10, 2026

This is the nontechnical map of the main verified live pieces.

## Governance core

- **`supreme-mind-v1-governor`** — main Supreme Mind governance decision point.
- **`scqos-router`** — routes governed work to the correct path.
- **GrassRootsAI/Anabelle inference and release validators** — keep model inference and release as separate transitions, including dedicated Terra/Grok validation paths.

## Worker layer

- **`shadow-clone-v1-executor`** — runs bounded Shadow Clone work under the Supreme Mind structure.
- **Supreme Mind SQS action queue** — carries admitted work between decision and execution.

## State and proof

- **`supreme-mind-v1-state`** — governed task/clone state.
- **`supreme-mind-v1-receipts`** — durable governance/execution receipts.
- **Versioned S3 evidence** — frozen proof artifacts and version-addressable material.
- **AWS KMS signing** — cryptographic signing/verification. The live Phase 4.9 decision key uses ML-DSA-65 / `ML_DSA_SHAKE_256`.

## Public proof

- **`scqos-public-execution-challenge-v1`** — public execution challenge endpoint with receipts/signing.
- **Public-proof sandboxes** — isolated validator, executor, evidence, queue and publisher resources for reproducibility.

## SupremeComputation.org operating layer

- **`supreme-totality-ingress-v1`** — accepts objectives.
- **`supreme-objective-orchestrator-v1`** — coordinates objectives into bounded work.
- **`supreme-live-public-evidence-v1`** — collects public evidence.
- **`supreme-mind-v1-business-executor`** — executes registered business actions.
- **`supreme-lead-followup-v1`** — qualified consent-based follow-up.
- **`supreme-social-oauth-v1` + `supreme-linkedin-publisher-v1`** — governed social authentication/publishing.
- **`supremecomputation-email-forwarder`** — domain email forwarding.

## Scheduled loops

Observed enabled EventBridge rules include the Supreme Mind heartbeat, business growth cycle and lead follow-up cycle. The LinkedIn distribution rule exists but was observed **disabled**, showing the difference between “component exists” and “component is active.”

## Containers, Anabelle and quantum

The account includes ECS clusters for SCQOS Docker work and GrassRootsAI/Anabelle, separate build infrastructure for Anabelle Totality and Shadow Clone browser/runtime work, sports quantum receipt storage, IBM Quantum credentials, repository Qiskit adapter code and AWS quantum experimentation.

## Whole circuit

**objective → governance → bounded worker/tool → consequence → receipt → next state**

Every cloud service supports one part of that circuit. The cloud service itself is not the governing principle.
