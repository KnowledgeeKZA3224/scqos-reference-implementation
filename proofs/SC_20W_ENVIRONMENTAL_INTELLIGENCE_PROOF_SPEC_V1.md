# SCQOS 20-Watt Environmental Intelligence Proof — Universal Submission Specification v1

## Purpose

Produce one artifact that a national laboratory, standards body, university, government agency, hardware company or independent laboratory can reproduce without trusting Supreme Computation, its author, or any vendor.

## Exact claim under proof

A complete governed intelligent consequence can be executed at <=20 W average **for the defined functional unit**, with every energy input inside the measurement boundary accounted for. A second qualification may establish what fraction of that power can be continuously supplied by ambient/environmental harvesting.

This avoids two invalid substitutions: (1) claiming 20 W powers the external loads being controlled, and (2) calling ambient harvesting 'energy from nothing.'

## One complete proof apparatus

### A. Functional unit

One fixed end-to-end consequence:

`input -> local inference/reasoning -> SCQOS eight-invariant decision -> allowed action in a sandbox -> consequence confirmation -> signed durable receipt`

The dataset, prompts, model weights, runtime, policy, expected result and receipt schema are content-addressed before execution.

### B. Energy boundary

Measure the complete device boundary, not only CPU/GPU telemetry:
- compute
- memory
- storage
- networking used by the run
- fans/pumps/cooling physically required by the device
- power conversion losses
- any battery discharge
- every ambient harvester input and storage element

For a government-grade claim, use a calibrated power/energy analyzer with a documented uncertainty budget and traceability chain. NIST defines metrological traceability as an unbroken documented calibration chain with each link contributing measurement uncertainty.

Reference: https://www.nist.gov/calibrations/traceability

### C. Environmental-energy boundary

Instrument each available gradient separately but sum them at one DC bus:
- light
- humidity/moisture
- temperature gradient / waste heat
- airflow/vibration where present
- RF where present
- biological/plant-microbial input where present

Every source gets its own voltage/current/time series. Storage begins at a declared state of charge and ends at the same or lower state unless the energy increase is explicitly counted.

### D. Eight invariant release gate

**Time** — synchronized timestamps; fixed run window; energy integrated over the same interval.

**Continuity** — hashes bind model, code, policy, dataset, runtime, meter configuration and calibration certificate to the run.

**Alignment** — the workload must meet a predeclared quality/outcome threshold; low power cannot be bought by silently degrading the task.

**Genesis** — every joule entering the device is attributed to a declared source or the run is HOLD.

**Boundary** — mains, batteries, USB, network PoE, hidden storage and measurement-equipment coupling are either inside the ledger or physically excluded.

**Reference** — measurements are traceable to calibrated instruments and source artifacts are immutable/content-addressed.

**Causality** — source-disable and workload-disable controls show which energy source causes which electrical output and which computation causes which energy use.

**Consciousness / accountability** — independent operator/lab identity signs the same manifest and can reproduce the result from the published package.

## Required executions

1. **Baseline**: current conventional stack, complete functional unit, total joules and outcome score.
2. **SC-gated**: identical functional unit with SCQOS preventing unnecessary transitions; total joules and outcome score.
3. **Efficiency stack**: same functional unit on the lowest-energy available architecture (quantized/sparse/event-driven/in-memory/neuromorphic/analog where accessible).
4. **Ambient-coupled**: same functional unit with environmental harvesters feeding the common energy bus; declare the measured fraction of demand supplied by ambient sources.
5. **Blind negative controls**: disconnect or neutralize each claimed energy source in randomized order. Output must fall by the predicted amount or the corresponding claim is rejected.
6. **Independent reproduction**: a second operator/lab repeats the exact package without private instructions.

## Release conditions

### PERMIT: 20-W intelligence claim
- fixed functional unit passes outcome threshold;
- whole-device average power <=20 W over the declared duration;
- uncertainty interval remains <=20 W at the chosen confidence level;
- all eight invariants pass.

### PERMIT: ambient-autonomy claim
- the energy ledger closes over the declared duration;
- stored-energy state does not secretly decrease, unless that decrease is counted;
- measured environmental inputs supply >=100% of device energy plus conversion/storage losses over the interval;
- source-disable controls behave causally;
- all eight invariants pass.

### HOLD
Any missing calibration, unknown energy input, workload drift, hidden battery contribution, unbounded network compute, unverifiable model change, or missing raw trace.

## Public package

- `manifest.json` — hashes/identities/claim
- `raw_power.csv` — timestamp, volts, amps, watts, cumulative joules
- `ambient_inputs.csv` — source-resolved energy
- `workload.json` — frozen functional unit and pass criteria
- `hardware.json` — full bill of materials/configuration
- `software.lock` — exact versions/hashes
- `calibration/` — instrument certificates + uncertainty budget
- `controls/` — negative-control runs
- `receipt.json` — SCQOS decision + invariant results
- `signature.sig` — cryptographic signature
- `reproduce.sh` — one-command software reproduction
- `README.md` — plain-English result and claim boundary

## Standards crosswalk

- NIST metrological traceability: unbroken calibration chain + uncertainty.
- MLCommons Power: standardized ML benchmark power measurement techniques and formats.
- Green Software Foundation SEI: `energy / functional unit`, including facility/network boundary where relevant.
- ISO/IEC 21031:2024 SCI: published software-impact measurement methodology; useful for downstream carbon reporting.

References:
- https://www.nist.gov/calibrations/traceability
- https://mlcommons.org/working-groups/benchmarks/power/
- https://greensoftware.foundation/standards/sei/
- https://greensoftware.foundation/standards/sci/

## Current SCQOS state

Software-side governance, model-substrate change, durable receipts and cryptographic evidence are already executable in the Supreme Computation environment. The present workstation exposes no usable whole-system power telemetry while on AC power (`BAT0 power_now=0` and no hwmon energy/power counters were exposed during the 2026-09-10 inspection). Therefore a government-grade <=20 W physical claim is **not yet releasable from this machine without an external calibrated power analyzer**. SCQOS marks that physical claim HOLD rather than inventing a wattage.

That HOLD is not a failure of the thesis; it is the exact missing boundary required to turn the thesis into evidence nobody has to trust.

