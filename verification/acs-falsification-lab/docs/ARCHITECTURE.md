# Architecture in plain English

The circuit is intentionally simple:

**AI / script proposes an action → ACS carries the request → SCQOS decides → the executor obeys → the lab checks reality → evidence is written.**

The ACS adapter does not replace SCQOS. It translates the outside wire format into a Supreme Computation transition proposition, asks SCQOS for `PERMIT`, `HOLD`, or `REJECT`, and translates the result back into the ACS disposition vocabulary.

| SCQOS | ACS |
| --- | --- |
| `PERMIT` | `allow` |
| `REJECT` | `deny` |
| `HOLD` | `defer` with `timeout_decision: deny` |
| bounded rewrite | `modify` |
| independent approval required | `ask` |

The lab separately checks ACS wire integrity before SCQOS is asked to judge the consequence. Missing or bad signatures, stale timestamps, duplicate request IDs, and chain mismatches are wire-level failures and must never be upgraded into a policy allow.

## Why the harness attacks itself

A benchmark is worthless if an implementation can ignore the request, always allow, always deny, skip tests, or merely print success and still get a green result. The meta-tests deliberately inject those failures. A release is green only when the normal implementation passes and the known-bad mutants fail.

## Live consequence proof

The terminal proof uses a real filesystem state transition. The authorized request creates one controlled file. A request with the wrong authority must not create its file. A valid request is then replayed; the first execution creates the file and the second must not change the file. The before/after SHA-256 values are recorded.
