# Live execution record

The first live execution connected the terminal laboratory to the already-deployed SCQOS ProofGate in AWS.

The sequence was:

1. Terminal generated ACS requests.
2. The SCQOS ACS Guardian verified wire integrity, timestamp freshness, replay state and chain continuity.
3. The Guardian translated the consequential request into an SCQOS transition and called the live AWS ProofGate.
4. A `PERMIT` was mapped to ACS `allow`; a wrong-authority request was mapped to `deny`; missing evidence was mapped to fail-closed `defer`.
5. For the real-consequence test, the terminal wrote a sandbox file only after the live cloud decision returned `allow`.
6. A denied request produced no file.
7. A replayed request returned `REPLAY_DETECTED` and the file digest remained unchanged.

Machine-readable evidence is committed under `evidence/initial/`.
