# Mark Microsoft 365 boundary

Supreme Mail uses a multitenant Entra app authenticated by Azure user-assigned managed identity through workload identity federation. No client secret is stored.

The Entra app has **no tenant-wide Microsoft Graph Mail.Send application permission**. Exchange Online Application RBAC is the only mail-send authority. The staged PowerShell script creates the customer-tenant service principal, scopes it to `Marks@numbersetcandetc.com`, assigns `Application Mail.Send`, and proves the mailbox is in scope with `Test-ServicePrincipalAuthorization`.

The Azure runtime stays `HOLD` until a `MICROSOFT_AUTH/RBAC_PROVEN` state record is written after the Exchange proof is independently verified. No client contact or email send is authorized by readiness preparation.
