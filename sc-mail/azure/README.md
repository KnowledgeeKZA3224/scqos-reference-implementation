# Supreme Mail — Mark — Azure execution plane

Live execution host: https://sc-mail-mark-v2.whitewave-9c5d9f8d.westus3.azurecontainerapps.io

- Azure: API/UI, Table state, Service Bus consequence queue, Key Vault boundary, receipt storage, Graph worker.
- AWS: independent live Supreme Mail baseline plus Supreme Apex read-only witness.
- SC: all eight invariants run before a campaign can enter the consequence queue.
- Microsoft: multitenant Entra app uses workload identity federation with Exchange Online Application RBAC scoped only to Marks@numbersetcandetc.com. No client secret or tenant-wide Mail.Send grant is used; transport stays fail-closed until the mailbox-scoped RBAC proof is observed.
- Evidence: sc-mail/azure/evidence/LIVE_TOTALITY_PROOF.json
- Evidence SHA-256: d0e27173c88ea413156c512bc99d562050728b6f0fad181a201260249a5499c8

Nothing executes until it proves itself.
