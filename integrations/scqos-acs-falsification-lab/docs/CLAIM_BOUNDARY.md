# Claim Boundary

This lab is designed to make strong claims difficult to fake, not to make unfalsifiable claims.

A green run means that the exact pinned code, exact pinned ACS revision, exact probes, exact execution environment, and exact evidence named in that run behaved as recorded. It does not mean OWASP, Microsoft, NIST, IETF, GitHub, AWS, or any third party certified Supreme Computation. It does not prove the absence of unknown defects. It does not turn a self-attestation into an independent certification.

The stronger statement this repository supports is narrower and testable: **the SCQOS Guardian accepted ACS-shaped requests, rejected or deferred the named invalid cases, blocked duplicate/replayed execution in the controlled consequence test, produced wire evidence, and the same public harness detected deliberately broken implementations.**

The project is intentionally open to falsification. A valid counterexample is a reproducible case showing that the Guardian violates a pinned ACS requirement or that the harness reports green while reality violates the asserted state.
