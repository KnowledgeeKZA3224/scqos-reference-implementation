# Pinned outside context

The lab does not let moving upstream repositories silently change the meaning of a result. `pins.json` freezes the exact commits used for the first execution.

The initial comparison pins:

- OWASP / GenAI Security Project Agent Control Standard repository.
- `probityai/agent-evidence-vectors`, including the ACS-Core negative-conformance corpus.
- the SCQOS reference implementation commit used by the live ProofGate lineage.

The lab also runs the current AGT-backed ACS reference Guardian through the same laboratory probes. Those probes are **not represented as an official ACS certification score**. They are a differential observation: same harness, same classes of request, different Guardian. The raw result is preserved so reviewers can inspect where behavior diverged.
