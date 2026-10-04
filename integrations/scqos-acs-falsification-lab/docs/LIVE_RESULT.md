# Live result — 2026-10-03

The live run used the deployed SCQOS ProofGate endpoint from the pinned repository metadata and the connected Linux terminal.

- SCQOS ACS probe suite: **20 / 20 PASS** against the live SCQOS decision service.
- Harness integrity: **6 / 6 deliberately broken test conditions detected** — allow-everything, deny-everything, signature-blind, replay-blind, fake-success, and skipped-test runner.
- Real consequence proof: **PASS**.
  - authorized terminal consequence executed;
  - wrong-authority consequence did not exist;
  - first replay target execution occurred once;
  - duplicate request was rejected;
  - target SHA-256 remained unchanged after the rejected replay.
- Microsoft/AGT reference Guardian was driven by the same 20-probe harness and recorded separately. Its result is evidence about that exact pinned pairing, not a universal judgment about AGT or ACS.

Raw machine-readable runs are intentionally generated under `run-evidence/` and are reproducible with `./scripts/verify-everything.sh`.


## Pinned Microsoft/AGT Guardian self-test

The Guardian package itself was tested from the pinned ACS checkout: **259 pass, 0 fail**. The broader monorepo run was also preserved separately and is not represented as green because unrelated upstream-watch tests require fixture clones.
