# ProofGate AI — Agents for Humans Hackathon 2026

ProofGate AI is a governed AWS Strands agent that checks whether a proposed consequence is allowed to become real before execution.

## Live demo

https://brbdxmelpeaktvdpmjrk34upwq0pymad.lambda-url.us-east-1.on.aws/

Test:
- `?scenario=permit` — all required checks pass.
- `?scenario=hold` — stale evidence causes HOLD.
- `?scenario=reject` — invalid authority causes REJECT.
- `?scenario=reroute` — degraded primary path causes REROUTE to a bounded alternate.

## Architecture

Human goal → Strands Agent → ProofGate governance boundary → PERMIT / HOLD / REJECT / REROUTE → AWS execution → consequence verification → signed durable receipt.

## AWS services

- Strands Agents SDK
- Amazon Bedrock / Amazon Nova Pro
- AWS Lambda
- Amazon DynamoDB
- AWS KMS

## What the demo proves

The same agent is evaluated under four different live conditions. Each decision produces a durable receipt with a SHA-256 identity and AWS KMS signature so the decision can be checked after execution.

## Pre-existing work disclosure

This hackathon project was created during the Agents for Humans contest period and builds on pre-existing Supreme Computation / SCQOS governance research already present in this repository. The new hackathon-facing work is the ProofGate AI Strands/Bedrock agent implementation, four-state demo, AWS execution path, and signed receipt flow.

## Run locally

1. Install Python 3.12+.
2. `pip install -r requirements.txt`
3. Configure AWS credentials with permission for the Bedrock model and the AWS resources referenced by the environment variables.
4. Set `RECEIPT_TABLE`, `KMS_KEY_ID`, and optionally `MODEL_ID`.
5. Invoke `lambda_handler` with a query parameter `scenario` set to `permit`, `hold`, `reject`, or `reroute`.

## License

MIT. See `LICENSE`.
