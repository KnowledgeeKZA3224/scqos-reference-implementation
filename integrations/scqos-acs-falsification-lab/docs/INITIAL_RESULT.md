# Initial falsification result

The first complete run closed the loop from outside standard to live SCQOS decision to observable reality.

The SCQOS ACS Guardian passed **20/20 laboratory probes** against the live SCQOS ProofGate. Those probes include valid execution, bad authority, missing evidence, missing/tampered signatures, replay, stale/future timestamps, chain mismatch, all five ACS dispositions used by the adapter, lifecycle dispatch and MCP-wrapped dispatch. The mutation harness also detected every deliberately broken implementation it injected: allow-everything, deny-everything, signature-blind, replay-blind, fake-success and skipped-test behavior.

A second adapter drove the portions of the independently published `probityai/agent-evidence-vectors` ACS-Core corpus that can be translated directly into the current ACS wire surface without inventing missing policy state. **9/9 directly driven vectors matched their declared expectation; 25 corpus members are explicitly marked `NOT_DRIVEN`, not silently counted as passes.**

The pinned Microsoft Agent Governance Toolkit / ACS reference implementation was also run rather than treated as an authority by name. Its own upstream suite completed **1112 pass, 1 skip, 0 fail** after providing the test environment's expected `trash` command. Under this lab's stricter cross-Guardian probe assumptions it records differential behavior rather than an official score; raw output is preserved.

The cloud consequence proof used a versioned private S3 evidence plane. The live SCQOS/ACS circuit allowed the permitted transition and the first replay candidate, rejected the wrong-authority transition, held the missing-evidence transition, and rejected the second identical request as `REPLAY_DETECTED`. The cloud executor then created exactly the two allowed objects. Version inspection found **1 permitted version, 0 denied versions, 0 held versions, and 1 replay-object version**. A KMS P-256 signature over the canonical cloud evidence was verified independently with OpenSSL on the terminal.

This is a falsifiable execution record, not third-party certification. Every numeric claim above is backed by a committed raw artifact in `evidence/initial/` and by pinned upstream commits in `pins.json`.
