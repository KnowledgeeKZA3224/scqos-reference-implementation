# OWASP ACS interoperability and falsification lab

SCQOS now has an executable OWASP Agent Control Standard integration/falsification surface. The lab drives ACS-shaped requests through SCQOS, checks valid and invalid execution paths, verifies replay and signature handling, checks real controlled terminal consequences, and attacks the test harness with deliberately broken Guardians.

Verified execution result: 20/20 SCQOS probes passed against the live ProofGate decision substrate; six deliberately broken conditions were detected; the cloud-to-terminal consequence test permitted the authorized write, prevented the wrong-authority write, blocked replay, and preserved the replay target hash. The pinned Microsoft/AGT Guardian package self-test recorded 259 pass / 0 fail.

The complete release is committed locally as `fe6d1aefcbd4c8b066861c661a6c4e9d1fcf26a9` in `scqos-acs-falsification-lab` and includes the Guardian, harness, negative controls, controlled side-effect proof, evidence bundles, CI workflow, architecture and claim boundary.

This is evidence of the pinned executions, not a claim of OWASP or Microsoft certification. The intended public laboratory repository is `KnowledgeeKZA3224/scqos-acs-falsification-lab`.