# Supreme Computation on Azure — Continuity Runtime

This directory is the AWS→Azure continuity layer for Supreme Computation / SCQOS.

The governing law does not change with the cloud substrate: **Nothing executes until the current transition proves itself.** Time, Continuity, Alignment, Genesis, Boundary, Reference, Causality, and Consciousness / Observer remain the admission boundary.

## Verified live baseline

Verified before the local Azure execution channel disconnected on September 24, 2026:

- Azure subscription enabled
- `rg-supreme-computation-core` in `westus3`
- `vnet-sc-core` with app/data/management subnets
- `nsg-sc-private` with explicit Internet egress deny
- `sc-continuity-lock` CanNotDelete lock
- `id-sc-governance-observer` with Reader-only access
- `sc-totality-enforced`, `sc-eight-invariants-gate`, and `sc-boundary-gate`
- storage account `stscqosc9f1a2b2`
- Blob versioning + 30-day delete retention enabled

## Migration contract

The AWS implementation remains historical evidence. New Azure code must preserve the same consequence semantics rather than mechanically translate vendor APIs.

| AWS plane | Azure continuity target |
|---|---|
| Lambda / Function URL | Azure Functions HTTP, Queue and Timer triggers |
| DynamoDB state / receipts | Azure Table Storage now; Cosmos DB only where query/index needs justify it |
| SQS / DLQ | Azure Storage Queues now; Service Bus for ordered/session workloads |
| S3 versioned evidence | Azure Blob Storage with versioning/retention |
| KMS signing | Azure Key Vault keys + cryptographic sign/verify |
| Secrets Manager | Azure Key Vault secrets |
| EventBridge schedules | Azure Functions Timer triggers / Event Grid |
| API Gateway | Azure Functions HTTP endpoints; API Management only if needed |
| CloudWatch | Azure Monitor / Application Insights |
| Cognito | Microsoft Entra ID / External ID |
| ECS/EKS | Azure Container Apps scale-to-zero; AKS only when Kubernetes is actually required |
| ECR | Azure Container Registry |
| Bedrock / AgentCore | Azure AI / external model adapters behind deterministic SCQOS admission |
| SageMaker | Azure Machine Learning |
| Braket | Azure Quantum or IBM/Qiskit witness lane; never safety-critical |
| CloudFront / S3 web | Azure Static Web Apps or Storage static website |
| SES / mail routing | Microsoft Graph / Azure Communication Services |
| Route 53 | Azure DNS |
| CloudFormation | Bicep/ARM plus this idempotent deployment surface |

## Named application continuity

The migration manifest covers Supreme Mind, Shadow Clone, ProofGate/public challenge, Supreme Apex, Gekyume, Sharingan, Anabelle/GrassRootsAI integration, Supreme Mail, website/business automation, social OAuth/publishing, scheduled growth/follow-up loops, public evidence, and quantum witness paths.

## Files

- `migration-map.json` — source-to-target inventory and current status
- `deploy_totality.sh` — idempotent Azure deployment script
- `runtime/azure_backend.py` — vendor substrate adapter
- `runtime/supreme_mind_azure.py` — 59-faculty governor port
- `function_app.py` — Azure Functions ingress, heartbeat, and admitted-work queue boundary
- `requirements.txt` — Azure runtime dependencies

Anything marked `BLOCKED_EXTERNAL` is not silently promoted to complete. It requires a credential, DNS change, vendor approval/quota, or the later IBM Cloud connection.
