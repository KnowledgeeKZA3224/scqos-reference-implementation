# Supreme Mail — Mark v1

Outlook-native business email automation governed by Supreme Computation.

## Frozen end state
- Mark works from Outlook through a right-side **Supreme Mail** pane.
- Normal workflow: import CSV/Excel export → choose audience → write → preview → send.
- SC evaluates Time, Continuity, Alignment, Genesis, Boundary, Reference, Causality and Consciousness as one pre-execution state.
- Outlook/Microsoft 365 is the first transport.
- **9,950 recipients in a rolling 24-hour SC-managed window is a hard transport ceiling, not the product workflow.**
- A separate internal pacing limit stays under Microsoft's message-rate ceiling.
- Unsubscribes, hard bounces, complaints and permanent failures become durable suppression state.
- Temporary transport failures are retried with bounded backoff; a single recipient failure does not abort unrelated recipients.
- Every accepted/rejected/held consequence receives a receipt.
- The transport is pluggable so the same UI/core can later use SES or another provider without changing Mark's workflow.
- Hosted mode runs in Supreme Computation AWS. Portable mode uses the same SC core and provider interface locally.

## Live AWS development stack
Stack: `sc-mail-mark-v1` in `us-east-1`.

Resources are intentionally isolated from unrelated SC workloads.

## Microsoft boundary
The application is deployed with the Microsoft transport **locked** until Mark authorizes his business Microsoft 365 tenant. No password is ever required. Hosted mode expects an Entra app registration restricted to the intended sender mailbox.

## Safety model
SC does not attempt to disguise spam or bypass provider enforcement. The system maximizes successful legitimate delivery by proving list origin, suppression state, recipient validity, authentication state, quota state, campaign intent and authorization before execution, then reconciling transport responses into the next decision.
