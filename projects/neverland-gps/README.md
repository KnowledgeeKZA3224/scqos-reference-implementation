# Neverland GPS

**Mission:** a child-safety wearable whose core protection continues with zero Wi-Fi.

Neverland GPS combines an offline device runtime with Supreme Computation governance. The child-side loop must continue to boot, determine GNSS position, observe sensors, evaluate safety state, communicate locally with the child, produce safety guidance from verified local references, and generate receipts even when Wi-Fi and every outward network are unavailable.

The cloud is the factory, witness, update authority, and evidence plane. It is never life support for the child.

## Non-negotiable invariant

```text
NO_WIFI_REQUIRED == true
```

Loss of cloud, Wi-Fi, cellular, satellite, or direct radio may reduce outward communication, but it must not disable the local safety brain.

## Runtime states

```text
SAFE -> ATTENTION -> GUARDIAN -> RECOVERY
```

Every consequential transition is governed by SCQOS across Time, Continuity, Alignment, Genesis, Boundary, Reference, Causality, and Consciousness.

## Files

- `TOTALITY_ARCHITECTURE.md` — beginning-to-end architecture.
- `SOFTWARE_MAP.json` — how the existing Supreme Computation environment participates.
- `neverland_runtime.py` — deterministic offline reference state machine.
- `test_neverland_runtime.py` — fail-closed proof cases.
- `cloudformation.yaml` — non-PII prototype cloud evidence/control plane.

## Current engineering boundary

This repository can prove the software contract and cloud witness path. A production wearable still requires physical PCB/radio/antenna/battery design, environmental and RF testing, secure manufacturing/provisioning, child-safety validation, privacy/compliance review, and field trials before it can be represented as production-ready.
