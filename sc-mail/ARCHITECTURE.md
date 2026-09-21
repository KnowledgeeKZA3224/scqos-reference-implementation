# Supreme Mail v1 — Total Architecture

```
Outlook
  └─ Supreme Mail task pane
      └─ SC Core (8 invariants, one state)
          ├─ contact normalization / dedupe
          ├─ durable suppression
          ├─ campaign intent + authorization
          ├─ quota + pacing boundary
          ├─ retry/reconciliation
          └─ receipts
              └─ Transport Adapter
                  ├─ Microsoft 365 / Graph  [v1]
                  ├─ Amazon SES             [future scale]
                  └─ Generic provider       [portable]
```

## User experience
Mark sees Outlook vocabulary only: Contacts, Audience, Subject, Message, Preview, Send, Scheduled, Sent, Do Not Email.

## Outlook transport boundary
Supreme Mail never schedules more than 9,950 SC-managed recipients inside the configured rolling 24-hour Outlook window. This is deliberately below the 10,000-recipient Exchange Online hard limit. Internal pacing is configured below the 30-message/minute hard limit.

## Execution semantics
The Send button expresses intent. SC compiles an executable batch. A contact is eligible only if the full eight-invariant state passes. Solvable transport problems are retried/reconciled; permanent recipient failures are isolated and added to durable state without aborting unrelated recipients.

## Hosted mode
AWS serverless:
- API Gateway: Outlook task-pane/API endpoint
- Lambda API: UI, preflight, unsubscribe
- SQS + DLQ: consequence queue
- Lambda worker: Microsoft transport
- DynamoDB PITR: campaign receipts/suppression
- Secrets Manager: Microsoft authorization + unsubscribe signing
- CloudWatch: native logs/metrics

## Portable mode
Same SC core + provider interface. Local state uses SQLite. An installer can run a local loopback service and the Outlook task pane against it; no Supreme Computation cloud dependency is required.

## Authentication
Hosted sending remains locked until Mark authorizes the Microsoft 365 tenant. Use an Entra app registration with only the mail authority needed by this product and restrict application access to the intended sender mailbox. Local Outlook mode uses Microsoft-supported nested app authentication where available.

## Non-goals
Supreme Mail does not attempt to evade spam systems, falsify consent/origin, or hide abusive traffic. Account protection comes from proving legitimate origin, authorization, authentication, suppression, pacing and current provider boundaries before each consequence.
