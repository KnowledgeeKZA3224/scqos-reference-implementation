# GEKYUME

GEKYUME is a payment-agnostic pre-execution governance layer. It does not replace payment rails or move funds itself. It decides whether a proposed payment has proven enough to be allowed to enter its underlying rail, then can reconcile what actually settled against what was authorized.

## Universal payment boundary

A caller submits a payment in its native domain. GEKYUME normalizes it into one transaction shape, binds the intended recipient to the exact execution destination, checks authority, amount, asset, rail, time, and optional evidence requirements, and returns `PERMIT`, `HOLD`, or `REJECT` with a durable receipt.

The current universal adapter recognizes ACH, FedNow, RTP, wire/Fedwire, SWIFT, ISO 20022, card, blockchain, Ethereum/EVM, Bitcoin, XRPL, Solana, stablecoin, wallet-to-wallet, AI-agent, bank transfer, and generic/custom payment inputs. Unknown/custom rails can enter through `GENERIC` while retaining the same source/destination/amount/asset/authority/binding contract.

## Blockchain recipient binding

For blockchain payments, the transaction destination is compared with the exact destination authorized before execution. Network, chain, asset, token contract, and recipient identity can also be bound. A destination mutation produces `REJECT` before the transaction is allowed to enter the signing/broadcast rail.

This extends the repository's existing `crypto_holy_grail` pre-signing proof into GEKYUME's universal payment surface.

## AWS deployment

Production control-plane resources are in `us-east-1`:

- Lambda: `gekyume-universal-gate-v1`
- DynamoDB receipts: `gekyume-universal-receipts-v1`
- API: `gekyume-financial-execution-api-v1`
- Routes: `GET /health`, `POST /evaluate`, `POST /execute`, `POST /reconcile`
- API authorization: AWS IAM

`POST /execute` remains as a compatibility alias for pre-execution evaluation. GEKYUME itself does not settle funds.

## Acceptance

The live AWS acceptance run passed synthetic tests for ACH, FedNow, RTP, wire, SWIFT, ISO 20022, card, AI-agent, generic, blockchain recipient binding, wrong-recipient rejection, and post-settlement reconciliation. The machine-readable acceptance record is in `gekyume/evidence/universal_payment_acceptance_2026-09-15.json`.
