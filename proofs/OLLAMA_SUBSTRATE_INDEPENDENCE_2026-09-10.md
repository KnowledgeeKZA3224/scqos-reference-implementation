# Ollama Substrate-Independence Proof — September 10, 2026

## What was tested

Supreme Computation tested whether the same frozen governance contract could survive a change in the underlying local AI substrate.

Frozen instruction: `Reply with exactly SCQOS_OK and nothing else.`

Two different Ollama model/configuration substrates were executed on the same live host:

- `sc-qwen-1t:latest` — Qwen 2.5 0.5B, model ID `fe8cb989158a`, 1 CPU thread, temperature 0.
- `sc-tiny-4t:latest` — TinyLlama, model ID `b785f23e1e46`, 4 CPU threads, temperature 0.

Both independently returned `SCQOS_OK`.

## What that proves

For this tested pair, model identity and execution configuration changed while the frozen contract result remained the same. That is an observed substrate-independence result for this bounded experiment.

It does **not** claim that every model, accelerator, operating system or hardware platform has been tested.

## Governance closure

- Decision: `PERMIT`
- Invariants: `8/8 PASS`
- Receipt ID: `ollama-substrate-50f38cb634fc4fb0a039cb80`
- Versioned S3 bucket: `scqos-governance-evidence-us-east-1`
- S3 manifest version: `xMXoIV8wvhT1gqqZRYBQNHP7J0xZJaOY`
- Signing authority: AWS KMS `alias/scqos-decision-authority`
- Key type: `ML-DSA-65`
- Algorithm: `ML_DSA_SHAKE_256`
- Manifest SHA-256: `af2dd6fac2b541e5edeab0458953d60b22a399f1cdfe89810ded19e7208e9e16`

## Plain-English meaning

The model is not the law. The hardware configuration is not the law. The governing contract can remain continuous while the intelligence substrate underneath it changes.

**Nothing Executes Until It Proves Itself.**
