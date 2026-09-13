# Supreme Apex V1 — Live Deployment — 2026-09-13

Supreme Apex V1 is now deployed in the live AWS account as an additive control surface for SupremeComputation.org. Existing pre-existing website content was preserved.

## Live surfaces

- Public human interface: `http://SupremeComputation.org/apex/`
- Machine discovery: `http://SupremeComputation.org/.well-known/supreme-computation.json`
- OpenAPI: `http://SupremeComputation.org/apex/openapi.json`
- Proof explorer: `http://SupremeComputation.org/proof/apex-v1/`
- API endpoint: `https://63w9gbzyuh.execute-api.us-east-1.amazonaws.com`

## Governed circuit

`intent -> durable case state -> SQS work queue -> worker -> supreme-totality-witness-bridge-v1 -> Supreme Mind / SCQOS -> observed result -> durable receipt -> current case state`

Public intent is forcibly downgraded to `READ_ONLY_AUTONOMY` at ingress regardless of caller-supplied authority fields. The owner route `POST /owner/intent` is protected with API Gateway `AWS_IAM` authorization and produces `OWNER_AUTHORIZED` cases that still pass through the SCQOS witness boundary.

## Live AWS resources

The CloudFormation stack is `supreme-apex-v1` in `us-east-1`. It contains:

- HTTP API with health, public intent, IAM owner intent, case lookup, and receipt lookup routes
- API Lambda and worker Lambda
- DynamoDB case-state table with point-in-time recovery
- DynamoDB receipt table with point-in-time recovery
- SQS work queue and dead-letter queue
- EventBridge hourly bounded reconciliation rule
- API access log group
- least-privilege execution roles

The stack reached `UPDATE_COMPLETE` after deployment and subsequent boundary hardening.

## Executed verification

An end-to-end public test created case `4b32bcb9-519d-4534-bc9d-61a63bd62670`. The request deliberately attempted to supply `OWNER_AUTHORIZED`; ingress stored the case as `READ_ONLY_AUTONOMY`, proving the public route cannot self-promote authority. The case completed with a SCQOS `PERMIT` and durable receipt:

- Receipt ID: `303862ba30765ad2c4fedccb57008be3eaef95f2490691eac8a0c5c5cb174866`
- Witness transition ID: `a3a8596a2738a4166f5fb291552a15df5b6d4764f0bcf9bfcc72cd1c924d0a90`
- Permit receipt hash: `1d44dd9ca151fc90d69285d4c734800f813e79b43e5fc48f10d9349c7bc2a55f`
- Observation receipt hash: `4516ae93ba7ce4ace59df89f9ce564f14a2255ffd623a5913e23bbe3ac61738b`

A deployment-level durable receipt was also written as `SUPREME_APEX_V1_DEPLOYMENT_RECEIPT` after verifying the CloudFormation stack, API routes, IAM owner boundary, enabled hourly reconciler, and published Apex web objects.

## Boundary

This deployment does not replace or weaken existing SCQOS, Supreme Mind, Shadow Clone, Gekyume, business, email, sports, proof, or website infrastructure. It adds a single continuous intent-to-proof control surface around the existing environment.

**Nothing Executes Until It Proves Itself.**
