# Neverland GPS — Totality Architecture

## Source-layer end state

A child carries their own safety intelligence. The wearable does not need Wi-Fi to think, locate itself, evaluate danger, guide the child, preserve evidence, or continue attempting rescue communication.

## Closed circuit

```text
GENESIS
  child + guardian + device identity + signed safety capsule
      |
OBSERVE
  GNSS + IMU + button + tamper + battery + local clock
      |
SCQOS
  Time x Continuity x Alignment x Genesis x Boundary x Reference x Causality x Consciousness
      |
DECIDE
  PERMIT / HOLD / REJECT
      |
LOCAL CONSEQUENCE
  child guidance / safe-state change / receipt
      |
OPTIONAL OUTWARD PATH
  direct radio -> LTE-M/NB-IoT -> NTN satellite
      |
RECOVERY
  authorized reunion closes incident
      |
WITNESS + LEARN
  receipts -> cloud validators -> new signed release
      |
NEW GENESIS
```

## Device plane

### Safety brain
Always-on low-power controller. Owns GNSS freshness, emergency button, motion/tamper signals, battery reserve, safety-state machine, direct-radio scheduling, and watchdog behavior.

### Intelligence brain
Runs local speech recognition, compact local AI, offline map/reference retrieval, and child-facing dialogue. It never possesses unilateral authority to release location or invent an unverified destination.

### Storage
Encrypted local identity, guardian keys, safety plan, approved safe places, map packs, model/runtime version, causal event journal, and queued receipts.

### Communications
No Wi-Fi dependency. Outward communication is independent and opportunistic: direct sub-GHz/DECT-style guardian radio, terrestrial IoT cellular, and NTN satellite where hardware/service support exists. If all links fail, the local guardian continues.

## Supreme Computation enforcement

- **Time:** freshness and bounded age of GNSS, maps, credentials, and safety state.
- **Continuity:** route/state lineage and incident history.
- **Alignment:** proposed action must match the guardian-approved safety policy.
- **Genesis:** authentic child-device-guardian identity and signed software origin.
- **Boundary:** location and commands may cross only authorized boundaries.
- **Reference:** guidance uses verified local destinations/maps/rules.
- **Causality:** every escalation has explicit causal evidence.
- **Consciousness:** child/guardian intent is represented in the transition.

A model output is evidence. It is not permission.

## Cloud plane

The existing Supreme Computation environment becomes the factory/witness plane:

1. Supreme Mind + Shadow Clones generate bounded scenarios and attacks.
2. Anabelle/GrassRootsAI and model-validation services independently challenge candidate behavior.
3. Codex/Transformers-derived tooling builds, distills, tests, and analyzes candidate software/models.
4. ProofGate evaluates release transitions.
5. Linux Coherence Gate protects governed execution on capable Linux-based prototypes.
6. Gekyume's pre-movement governance pattern becomes pre-release governance for child location/data.
7. Supreme Apex coordinates intent-to-proof operations.
8. Biological Loop patterns bind physical sensor evidence to software state.
9. Hybrid Proof / Braket / IBM-Qiskit remain independent experimental witness paths, never safety-critical dependencies.
10. KMS/S3/DynamoDB/SQS/Aurora/Cognito/API Gateway/ECS provide signing, evidence, receipts, queues, continuity, identity and controlled cloud services.
11. SCQOS webhook/admission patterns prevent unproven backend releases.
12. Supreme Mail/site/commercial systems support guardian onboarding, support, incident communication and commercialization, not core safety execution.

## Fail-closed rules

- Unknown action -> REJECT.
- Tampered governed state -> REJECT.
- Stale position used for guidance/release -> HOLD.
- Unverified destination -> HOLD.
- Unauthorized location recipient -> REJECT.
- No outward link -> HOLD transmission while Guardian State remains active locally.
- Wi-Fi unavailable -> no state downgrade; core capabilities remain available.

## Physical end-state gates

Software completion is not hardware completion. Production requires verified PCB/SoC selection, GNSS/radio antenna performance, battery reserve, waterproofing, safe attachment/breakaway design, thermal limits, secure boot/provisioning, FCC/carrier/satellite certification as applicable, privacy/COPPA review, abuse/stalker-resistance testing, guardian recovery procedures, and child-centered field validation.

The production definition of done is not “the demo works.” It is: the child-side safety loop continues through total network loss, every consequential transition is governed and receipted, unauthorized tracking fails closed, and recovery behavior survives realistic field failure modes.
