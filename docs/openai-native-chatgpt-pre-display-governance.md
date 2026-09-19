# Native ChatGPT Pre-Display Governance: Supreme Computation Proof Proposal

## Objective

Make an external Supreme Computation governor **physically unavoidable before a native ChatGPT answer is displayed**.

Required execution order:

```
EXACT USER INTENT
  -> MODEL GENERATES CANDIDATE OUTPUT
  -> SUPREME COMPUTATION EXTERNAL GATE
     -> Time
     -> Continuity
     -> Alignment
     -> Genesis
     -> Boundary
     -> Reference
     -> Causality
     -> Consciousness / Observer
     -> source / system / consequence closure
  -> PERMIT: display the exact frozen answer
  -> REJECT: do not display; recompute from the same intent
```

This is deliberately different from checking a response after it has already been shown.

## What OpenAI Supports Today

OpenAI's Agents SDK supports **output guardrails** that run on the final agent output. A tripwire can prevent the rejected output from being released by the application that owns the agent runtime.

Reference:
- https://openai.github.io/openai-agents-python/guardrails/
- https://openai.github.io/openai-agents-python/

OpenAI's Apps SDK / MCP support allows ChatGPT to connect to external tools, data, logic, and interfaces.

References:
- https://openai.com/index/introducing-apps-in-chatgpt/
- https://help.openai.com/en/articles/12515353-build-with-the-apps-sdk
- https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt

However, the current documented ChatGPT app behavior is **message-scoped**: an app is selected or invoked for a message. The documentation does not expose a mandatory global final-output interceptor that every native ChatGPT reply must pass through before display.

That missing hook is the exact platform capability this proposal requests.

## Why MCP / Apps Alone Do Not Close the Circuit

A tool can be available without being called.
A tool result can be consulted without owning the display path.
A post-hoc audit can detect drift without preventing the user from seeing it.

Therefore:

```
ChatGPT -> answer displayed -> external audit
```

is not equivalent to:

```
ChatGPT -> external governor -> PERMIT -> answer displayed
```

The second architecture is required for fail-closed governance.

## Minimum OpenAI Platform Feature

Proposed feature name:

**Mandatory External Output Guardrail / before_display hook**

Suggested platform contract:

### 1. Registration

A user or workspace admin registers a remote HTTPS / MCP guardrail endpoint and explicitly scopes it to:

- one conversation;
- one custom agent;
- or an entire managed workspace.

### 2. Candidate packet

Before display, ChatGPT sends a signed packet such as:

```json
{
  "conversation_id": "...",
  "message_id": "...",
  "original_user_intent": "...",
  "original_user_intent_sha256": "...",
  "candidate_output": "...",
  "candidate_output_sha256": "...",
  "tool_trace": [],
  "citations": [],
  "model": "...",
  "generated_at": "...",
  "attempt": 1
}
```

### 3. External verdict

The external endpoint returns:

```json
{
  "verdict": "PERMIT",
  "candidate_output_sha256": "...",
  "receipt_id": "...",
  "receipt_hash": "...",
  "expires_at": "..."
}
```

or:

```json
{
  "verdict": "REJECT",
  "reason_codes": [
    "TIME_STALE",
    "REFERENCE_UNPROVED"
  ],
  "receipt_id": "...",
  "receipt_hash": "..."
}
```

### 4. Fail-closed release

ChatGPT MUST NOT display the candidate unless all of these are true:

- verdict is `PERMIT`;
- the returned candidate hash exactly matches the candidate awaiting release;
- the permit has not expired;
- the endpoint response is cryptographically attributable to the configured governor.

Timeout, network failure, malformed response, hash mismatch, stale permit, or explicit rejection means **no display**.

### 5. Recursive recomputation

When rejected, ChatGPT may create a new candidate, but:

- it must preserve the original user intent;
- it must carry forward the rejection reasons;
- it may not silently change execution surface or substitute a different task;
- every new candidate must receive its own permit.

### 6. Verifiable receipt

The ChatGPT UI should be able to expose a compact receipt reference:

```
Governed by: Supreme Computation
Receipt: CHATGPT-SC-...
Candidate hash: ...
Verdict: PERMIT
```

This makes governance independently auditable.

## Supreme Computation Mapping

The external governor evaluates one canonical response state against all eight invariants simultaneously:

- **Time** — evidence freshness and timing.
- **Continuity** — original intent and prior-state continuity.
- **Alignment** — requested outcome vs. candidate output.
- **Genesis** — provenance of claims, instructions, and evidence.
- **Boundary** — authority, safety, consequence, and scope boundaries.
- **Reference** — resolvable evidence, citations, hashes, receipts.
- **Causality** — the output follows from the evidence rather than correlation, omission, or unsupported inference.
- **Consciousness / Observer** — the system knows what is proven, what remains unknown, what consequence is being authorized, and does not silently collapse uncertainty.

No invariant independently authorizes release.

## Existing Supreme Computation Proof

A working AWS-side proof already exists for the external-governor half of this architecture:

- canonical eight-invariant contract;
- candidate-answer hashing;
- exact-intent hashing;
- fail-closed gate;
- immutable receipt IDs;
- runtime verification;
- recursive reject/recompute policy.

The remaining missing ownership boundary is the **native ChatGPT before-display hook**.

## Demonstration Test OpenAI Can Reproduce

1. User asks for an answer that depends on multiple live sources.
2. Model produces candidate A.
3. External gate rejects candidate A because one material source is stale.
4. Native ChatGPT must show **nothing from candidate A**.
5. ChatGPT reacquires evidence and creates candidate B.
6. External gate permits B and returns the exact candidate hash.
7. Only candidate B appears in the UI.
8. User can inspect the receipt.

Pass condition:

**No unpermitted candidate is ever visible.**

## Why This Matters Beyond Supreme Computation

The same primitive would support:

- regulated enterprise review;
- financial action governance;
- medical / legal workflow boundaries;
- data-sovereignty policies;
- organization-specific factuality requirements;
- external compliance engines;
- independently witnessed AI execution.

This is not a prompt-engineering feature. It is an **execution-control boundary**.

## Requested OpenAI Capability

Expose a supported, fail-closed **pre-display output middleware hook** in native ChatGPT, with user/workspace opt-in, signed request/response binding, exact-output hashing, timeout policy, audit receipts, and recursive regeneration after rejection.

Until that exists, the equivalent architecture can be implemented in an application that owns the model runtime using the OpenAI Agents SDK output guardrail system, but it cannot be made physically mandatory across ordinary native ChatGPT replies solely by attaching an MCP app.
