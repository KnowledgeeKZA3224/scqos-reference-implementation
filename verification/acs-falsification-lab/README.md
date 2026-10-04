# SCQOS × OWASP ACS Falsification Lab

**The simple version:** an AI asks to do something. OWASP ACS carries the request in a standard format. SCQOS decides whether that exact action is allowed to become real. This lab then tries to prove the whole circuit wrong.

This repository is intentionally not a marketing benchmark and not a certification badge. It is an **executable falsification system**. A claim is accepted only when the same public harness can attempt valid requests, tampered requests, stale requests, replayed requests, authority failures, chain failures and Guardian failures and then inspect what actually happened.

## What this proves

The lab separates four roles that must not silently trust one another:

1. **Observed Agent** — proposes an action.
2. **ACS wire contract** — describes the request and the Guardian response in an outside standard.
3. **SCQOS Guardian** — maps the proposed consequence into Supreme Computation and returns an ACS decision.
4. **Falsification harness** — attacks the Guardian, checks the raw wire traffic, checks the resulting state and writes reproducible evidence.

The harness also attacks **itself** with deliberately broken Guardians. If an allow-everything, replay-blind or signature-blind implementation can pass, the lab fails. That prevents a green score from meaning only that the test was easy to game.

## Why this is different from an isolated SCQOS demo

The governing interface and mandatory behavior come from OWASP ACS, not from SCQOS. The external negative corpus is pinned from `probityai/agent-evidence-vectors`. The Microsoft Agent Governance Toolkit reference Guardian can be placed beside SCQOS and receive the same probes. The result is a differential record: **spec expectation → AGT observation → SCQOS observation → real side effect → evidence**.

## One-command local reproduction

```bash
./scripts/bootstrap.sh
./scripts/verify-everything.sh
```

The run writes a machine-readable evidence bundle under `run-evidence/` and exits non-zero if any required assertion or meta-test fails.

## Live SCQOS substrate

By default the SCQOS Guardian calls the already-deployed public ProofGate endpoint named in `pins.json`. Local unit tests can use an in-process deterministic fake so the repository remains reproducible when the network is unavailable. The live mode is always identified in the evidence bundle.

## Claim boundary

A green run means the pinned implementation behaved as recorded for the pinned probes in that run. It does **not** mean OWASP certified SCQOS, that no undiscovered defect exists, or that every future ACS revision will behave the same way. See [`docs/CLAIM_BOUNDARY.md`](docs/CLAIM_BOUNDARY.md).

## Public challenge

If you disagree with a green result, the strongest rebuttal is executable: add or submit a case that violates the pinned ACS requirement and makes the harness turn red.

## Initial executed result — 2026-10-03

The initial end-to-end execution is preserved under `evidence/initial/`.

- SCQOS Guardian laboratory probes: **20/20 passed** against the live AWS ProofGate path.
- Harness self-falsification: **all 6 deliberate mutants detected** — allow-everything, deny-everything, signature-blind, replay-blind, fake-success and skipped-test runner.
- Live cloud → terminal consequence proof: **all 6 state assertions passed**. A permitted sandbox file was created; a denied file did not exist; a replayed request was blocked and the file digest remained unchanged.
- Pinned external ACS-Core corpus: **11 wire-driving vectors passed, 0 failed** against the live SCQOS path; **22 were explicitly NOT_DRIVEN** because they test framework/deployment/approver semantics rather than this wire adapter; **1 is marked UNMEASURABLE by the corpus itself**.
- Same external wire-driving subset against the pinned AGT-backed reference Guardian: **2 passed, 9 failed**, preserved as a differential observation rather than an official certification score.
- Same 20 laboratory probes against the AGT-backed reference Guardian: **2/20 passed under this lab's expectations**. This is a comparison record, not a claim that AGT is generally "2/20 conformant."
- The upstream AGT repository's own test run on this machine produced **1086 pass, 1 skip, 26 fail**; the raw log is preserved so the environment-specific failures are auditable rather than hidden.

The strongest claim is therefore not “certified” or “unbreakable.” It is: **the exact artifacts, inputs, failures, successes and physical side effects are published so another engineer can reproduce or falsify them.**
