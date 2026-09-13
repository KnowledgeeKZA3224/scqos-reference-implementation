# SCQOS Authority Witness — Production Cutover Proof

**Date:** 2026-09-13  
**Region:** `us-east-1`  
**Status:** **EXECUTED / PRODUCTION PATH CUT OVER**

## Purpose

This proof closes the operational step after the SCQOS Authority & Trust Chain Foundation milestone: establish a real witness, bind it to independently rooted current authority and policy state, place it in front of the production backend, close the direct public bypass, and challenge the resulting boundary.

The governing distinction is explicit:

- a signature is not authority;
- approval is not execution;
- execution is not durable state;
- durable state is not necessarily current state;
- historically valid evidence is not automatically current truth.

The production release path now enforces those distinctions rather than only documenting them.

## Live authority identities

- Witness ID: `SCQOS-AUTHORITY-WITNESS-V1`
- Root hash: `f96d4a408e211857c639fcd0673c12cc25ba33992ea94e547e90682ad365f7cd`
- Current policy hash: `4edb9018a89e1f84cc2a351b6a5bf4b04223d2225d5353b83584c4a4d925b2b9`
- Bound production-backend artifact hash: `754ab7c8beafb8234c0c9b55827da98c1b0ea267224d038acc52d5b30fd52a2d`
- Backend ARN: `arn:aws:lambda:us-east-1:327453383912:function:supreme-totality-ingress-v1`
- Backend code identity (`CodeSha256`): `TKyVYlsr+Yg8OKcpfa9IxVt5OQeaTVkP3qMPFD6C7MQ=`
- Current succession epoch at cutover: `0`

## Live AWS enforcement components

CloudFormation stack: `scqos-authority-witness-v1`

The stack establishes:

- independent root-authority table: `scqos-authority-root-v1`;
- monotonic witness/receipt table: `scqos-authority-witness-v1`;
- witness Lambda: `scqos-authority-witness-v1`;
- production bridge Lambda: `supreme-totality-witness-bridge-v1`;
- root-approval KMS key alias: `alias/scqos-root-approval-v1`;
- receipt-signing KMS key alias: `alias/scqos-authority-witness-receipts-v1`;
- dedicated witness role: `scqos-authority-witness-v1-role`;
- dedicated bridge role: `supreme-totality-witness-bridge-v1-role`.

Both DynamoDB tables use on-demand billing, server-side encryption and point-in-time recovery.

## Independent root boundary

The authority root is deliberately separated from the witness's writable state.

The witness role can read `scqos-authority-root-v1` but cannot write it. The production bridge has no DynamoDB or KMS authority at all. Root and current-policy records were installed from the independently privileged AWS root context using conditional, create-only writes.

The root table contains:

- `ROOT`;
- `CURRENT_POLICY`;
- immutable `POLICY#<policy_hash>` history.

The witness recomputes the canonical root and policy hashes before trusting them and checks that the root binds the exact production-backend artifact identity.

Policy succession is not an operation available to the witness. An attempted `INSTALL_SUCCESSOR` operation returns `REJECT / ROOT_ONLY_OPERATION`. A policy therefore cannot widen its own authority from inside the governed execution runtime.

## Monotonic witness

For every governed production transition the witness requires the exact current:

- root hash;
- policy hash;
- backend artifact hash;
- monotonic sequence number;
- transition identity;
- consequence hash;
- nonce.

A successful qualification atomically performs two operations in one DynamoDB transaction:

1. advances the current monotonic sequence;
2. creates the single-use transition receipt.

If either side fails, the transition does not become a valid PERMIT.

The receipt is signed with the dedicated receipt KMS key.

## Production execution circuit

The public production chat path is now:

`API Gateway /chat → supreme-totality-witness-bridge-v1 → scqos-authority-witness-v1 → PERMIT → supreme-totality-ingress-v1 → OBSERVE → durable observation receipt → release response`

The bridge does not release the backend response merely because the backend executed. It first requires a durable observation against the same permitted transition. If execution occurs but observation cannot be durably recorded, the bridge returns HOLD instead of releasing the result as governed success.

This makes approval, execution, durable consequence and current observation distinct machine-enforced stages.

## Production cutover

REST API: `supreme-website-twin-v1`  
API ID: `6j3q5tela6`  
Stage: `prod`  
Resource: `/chat`

Before cutover, `/chat` invoked `supreme-totality-ingress-v1` directly.

After cutover, `/chat` invokes:

`arn:aws:lambda:us-east-1:327453383912:function:supreme-totality-witness-bridge-v1`

Cutover deployment: `9wabr0`  
Response-mapping repair deployment: `a8qq43`

The deployed API path was exercised after the cutover and returned HTTP `200` through the witness bridge with `_scqos_witness` transition, PERMIT-receipt and observation-receipt identities attached to the returned envelope.

## Direct-bypass closure

The previous public Lambda Function URL for `supreme-totality-ingress-v1` was changed from unauthenticated access to `AWS_IAM` authentication.

The following direct/public invocation permissions were removed from the backend:

- `AllowSupremeWebsiteTwinV1`;
- `TotalityPublicFunctionUrl`;
- `TotalityPublicInvoke`.

The public website application was checked and uses API Gateway `/chat`; it does not depend on the legacy raw Lambda Function URL. Therefore the public website path does not bypass the new witness boundary.

## Adversarial challenge results

### Exact replay

Control transition:

`CONTROL-REPLAY-5f17261fa4a94225a9edc3919a8a77c3`

First qualification:

- result: `PERMIT`;
- witness sequence: `4`;
- permit receipt hash: `64c722e8fe4ecb214e0316984cf840853a2d6a1279213afa9c9b1f6121bf99c9`.

Exact replay of that transition against the consumed sequence:

- result: `HOLD`;
- reason: `MONOTONIC_OR_REPLAY_CONFLICT`;
- underlying transaction result: `TransactionCanceledException`.

### Wrong root

A qualification request carrying a false root hash produced:

- result: `REJECT`;
- reason: `CURRENT_ROOT_OR_POLICY_MISMATCH`.

### Self-succession

An attempt to make the witness install its own successor policy produced:

- result: `REJECT`;
- reason: `ROOT_ONLY_OPERATION`.

### Durable observation

The control transition was explicitly marked as a non-backend-execution test and still carried a separate observation record:

- status: `CONTROL_TEST_NOT_EXECUTED`;
- observation receipt hash: `2ee5f8a70995df7585995fbc02bd4e91f540c1e716847b6c9875b53eeddc72d3`.

This preserves the distinction between a permitted control transition and a claimed physical/software consequence.

## IAM boundary challenge

IAM simulation confirmed the witness execution role is allowed to read the root table but is implicitly denied write access to it. The production bridge is denied DynamoDB and KMS access and is limited to invoking the witness and bound backend plus logging.

Therefore neither the bridge nor the witness can silently rewrite the authority root that qualifies their own execution.

## Current production behavior and explicit boundary

The new outer authority witness is operational and the production `/chat` path is cut over to it.

During the cutover tests, the pre-existing inner `supreme-totality-ingress-v1` application returned its own semantic state as `HOLD` with `GOVERNOR_UNAVAILABLE`. That inner application-level HOLD was preserved rather than promoted to success. The outer witness still successfully proved the transition lifecycle: qualify → execute → observe → durable receipt → release.

This document therefore does **not** claim that every downstream governor or application dependency is healthy. It claims the narrower, executed fact: the real SCQOS authority witness now sits on the production public execution path, the direct public backend bypass was closed, replay/root/self-succession challenges fail closed, and each released production transition is bound to current rooted authority, current policy, the exact backend artifact and a durable observation.

## Closure

The operational authority chain is now:

`independent root state → current policy → current witness observation → monotonic PERMIT consumption → exact backend execution → durable consequence observation → response release`

No prior approval is inherited automatically. No backend response is treated as governed success merely because code ran. No current-policy change is available to the witness itself. A changed root, policy, artifact, sequence or transition identity requires requalification.

**Result: SCQOS Authority Witness Production Cutover — EXECUTED.**
