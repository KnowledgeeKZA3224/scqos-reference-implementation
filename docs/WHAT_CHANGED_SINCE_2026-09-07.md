# What Changed Since the September 7 Public Update

The previous public README update landed on **September 7, 2026**. The verified environment continued moving after that point. This document records the delta through September 10.

## Public business infrastructure

Live pieces now cover inbound lead handling, consent-based follow-up, public evidence gathering, website execution, email routing and scheduled business-growth cycles. This moves Supreme Computation beyond a governance demo toward an operating digital organization whose work can be routed through the same governance plane.

## Governed social publishing

A dedicated LinkedIn OAuth path and `supreme-linkedin-publisher-v1` Lambda are live. Drafting and publishing are treated as different actions, so creating text does not automatically authorize external publication.

## Totality ingress and orchestration

`supreme-totality-ingress-v1` and `supreme-objective-orchestrator-v1` provide a front door for objectives that can be decomposed into governed work.

## Router update

`scqos-router` was updated on September 10 and is part of the live routing surface.

## Codex read-only boundary proof

A real public Codex issue reported a state-changing `mv` command inside an explicitly read-only task. Supreme Computation froze the report and tested the boundary:

- READ_ONLY + read operation → PERMIT
- READ_ONLY + state-changing move operation → HOLD

The proof package was versioned in S3, bound to SHA-256, signed with AWS KMS ML-DSA, published publicly, and linked back into the upstream issue.

## Supreme Computation challenged itself too

A live Shadow Clone independently assigned to inspect the Codex case drifted into unrelated evidence. SCQOS did **not** release that result. The consequence stage returned HOLD. The experiment therefore tested both an external reported failure class and the system's own worker-drift boundary.

## Repository synchronization itself is evidence-bearing

This September 10 synchronization is driven from the verified live AWS state plus the current public GitHub state, not reconstructed from memory.
