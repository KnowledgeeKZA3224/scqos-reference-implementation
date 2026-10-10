# SC / The Forge: AWS↔Slack continuity bridge

**Status:** Implementation ready for review and deployment; not a live integration until Slack App approval, AWS credential provisioning, SAM deploy, and witnessed end-to-end tests. ChatGPT's Slack authorization and AWS authorization are **two separate delegated connections**. Neither provides a reusable Slack token to Lambda.

## 1080° execution and evidence boundaries

- **Time:** Slack Events signature timestamp within 300 seconds; UTC receipts and event IDs.
- **Continuity:** Append-only per-event S3 objects; idempotent conditional write on Slack event ID. Slack free-plan retention no longer determines the archive of *new events captured after activation*.
- **Alignment:** Only explicitly allowlisted workspace/channel IDs and `SC-` alarm names are accepted.
- **Genesis:** Original signed Slack event stored, not paraphrased by an AI model.
- **Boundary:** Private S3 bucket, scoped Lambda IAM grants, signatures, SNS source check. Do not import DMs, private channels, employee data, or candidate records without the appropriate approval and retention policy.
- **Reference:** SHA-256 of original event or delivery receipt, immutable event-derived key, correlation ID.
- **Causality:** Slack's successful HTTP response and separate AWS storage receipt are distinct outcomes; no invented delivery proof.
- **Consciousness/Coherence:** Fail-closed on missing credentials, signature mismatch, incorrect workspace/channel, malformed event, or SNS source. No autonomous operational commands are accepted from Slack.

## Current defaults

- Slack workspace: `The Forge` (workspace ID supplied at deployment)
- Inbound archive source: approved *private* `#supreme-founders` (channel ID supplied at deployment), subject to executive approval for institutional retention.
- Notifications: a dedicated **private** cloud-signal channel, to avoid spilling AWS internals into `#all-the-forge`.
- Existing AWS archive bucket should be independently verified before deploying. Do not create a new public bucket or change existing retention policies without approval.

## Required authorization (cannot be inferred from ChatGPT connection)

1. Create or authorize a Slack App in **The Forge** with `chat:write`, `channels:history` (only if channel archival approved), and `groups:history` (only for explicitly approved private channels). Event Subscriptions need `message.groups` for private channels, or `message.channels` for public ones; invite the bot to the selected channels. Do not request blanket DM access.
2. Store Slack **signing secret** and **bot token** separately in AWS Secrets Manager, with access limited to the respective Lambda roles. Never paste token values into Slack, chat, logs, or GitHub.
3. Confirm the current encrypted/private archive S3 bucket, appropriate S3 Object Lock/versioning/retention options, data residency, consent, access control and deletion handling. In this code, `IfNoneMatch=*` prevents overwriting the same key; it does **not** stop a privileged principal deleting objects. Use Object Lock if legally and operationally appropriate.
4. Review/change `ArchiveChannelIds` and `NotificationChannelId`, then `sam build` and `sam deploy --guided --capabilities CAPABILITY_IAM` from a trusted terminal with authorized AWS credentials. Deploy to an AWS region where the bucket exists or use qualified cross-region configuration.
5. Configure the Slack App Event Subscriptions Request URL from `SlackEventUrl`, complete Slack's signature challenge verification, and subscribe the app to selected channel events.
6. Point selected CloudWatch Alarm actions to the CloudFormation `AlarmTopicArn`. Use alarm name prefix `SC-` to pass the allowlist. Confirm only approved alert messages are forwarded.

## Test conditions before declaring LIVE

- Valid Slack signed event → `COMMITTED`, one immutable S3 envelope with correct `sha256` metadata.
- Same signed event → `ALREADY_COMMITTED` and no duplicate object.
- Invalid signature, stale timestamp, non-allowlisted channel → reject or hold without S3 writes.
- A genuine test CloudWatch `SC-` Alarm → Slack message with its returned timestamp and AWS receipt object.
- Non-allowlisted SNS topic or alarm → fail closed; no Slack delivery.
- Verify no private messages or credentials appear in public GitHub repositories or Slack channels.
- Confirm alerts, dead-letter/retry policy, log retention, cost thresholds and deployment rollback before running unattended.

## Critical retention distinction

This design saves messages **from the moment Slack Events are enabled**, not historic messages that Slack has already removed or no longer exposes. A one-time historical import is a separate, permission-scoped operation subject to Slack access, API/export limits, and data policy. Saving in AWS does not automatically replenish Slack's own search interface.

## Rollback

Disable Event Subscriptions in Slack, remove CloudWatch Alarm SNS actions, then delete the stack using CloudFormation. Do not delete archive objects until authorized retention and legal holds are checked. Revoke Slack bot credentials if compromised.

**Delivery semantics:** A forwarded SNS alarm can post twice if Slack acknowledges a message but the Lambda crashes before writing its receipt; this is an at-least-once notification path. Operators must deduplicate by the displayed alarm state and confirm the receipt, and never use Slack notifications as the source of truth for automated execution.
