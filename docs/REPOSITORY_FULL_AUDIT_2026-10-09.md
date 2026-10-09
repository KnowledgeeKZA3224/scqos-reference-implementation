# Repository-wide technical audit and coverage map — October 9, 2026

**Audit scope:** the complete tracked file index in the public `main` snapshot `b46afb75ce7e72a3caf381e4422322589f60ca41`, plus separate review of ongoing [draft Forge PR #26](https://github.com/KnowledgeeKZA3224/scqos-reference-implementation/pull/26) at `442ebb33ac1b988463e01a4998740a0227048bce`. **The draft PR's new files are *not* among the baseline 599 main files.** This was a machine-readable inventory, per-file structural scan and selected source/documentation review. Not a full threat-model audit, penetration test, mathematical proof of every path, or blanket certification.

## Complete baseline content census

- **599 tracked paths.** From their bytes: 583 UTF-8 files, 13 binary-like files, three not UTF-8; binary classification was heuristic (NUL detection).
- **113/113 tracked Python files parsed** with Python 3.14 AST. **192/192 tracked `.json` files parsed**. This establishes syntactic consistency of the checked-out tracked files, not algorithmic correctness.
- File types: JSON (192), Python (113), Markdown (86), TXT (62), shell (22), YAML/YML (17), SHA-256 lists (13), HTML (11), plus images, PDFs, signatures, certificates and archives.
- Largest top-level file groups by number of files: `evidence` (121), `integrations` (79), `verification` (59), `proofs` (37), `sc-mail` (28), `supreme_mind` (22), `crypto_holy_grail` (19), `gekyume` (18), `sc-physical-quantum-evidence` (18), `docs` (17), `website` (14), `shadow_clone` (13), `multicloud` (12), `commercial` (11), `licensing-closure` (11).
- The **complete exact baseline filename/size/content-digest listing** (all 599 entries) is in [audits/REPOSITORY_FILE_MANIFEST_2026-10-09.tsv](audits/REPOSITORY_FILE_MANIFEST_2026-10-09.tsv). A hash is an identity checksum, not independent validation of the underlying claim.

## Implementation families actually present

| Folder / module | What the tracked sources represent | Live-state caution |
| --- | --- | --- |
| `integration/`, root SC runtime scripts, `spec/`, `specs/` | Universal transition law, state preimages, gates, canonicalization, governance logic | Different historical code generations coexist; no assumption every module shares the same canonical protocol |
| `kernel_integration/` | Linux eBPF/LSM loader, source-level execution controls, service/activation scripts | Local kernel environment and deployment version require separate verification; don't infer enforcement on Windows/macOS |
| `proofgate_ai/` and `.github/actions/proofgate` | Public CLI/client and reusable GitHub Action for adversarial pre-execution evaluation | A ProofGate decision is not an external executor's actual side effect |
| `gekyume/`, `crypto_holy_grail/` | Payment-policy code, universal gate, crypto/XRPL/quantum-facing experiments | Not proof of regulated bank transfer or live $B transaction |
| `supreme_mind/`, `shadow_clone/` | Digital faculty manifests, AI worker protocols, governance and memory modeling | Digital roles are not humans; bounded proposals are not independent settled actions |
| `sc-mail/` | Outlook/Microsoft/desktop/cloud email workflow implementation | OAuth/consent and send authorization need live Microsoft verification |
| `azure/`, `multicloud/` | Historical AWS-to-Azure continuity contract and witness code | Azure continuity proof dated Sept 23; current Azure account availability not rechecked |
| `integrations/scqos-acs-falsification-lab/`, `verification/acs-falsification-lab/` | OWASP ACS falsification and conformance evidence, with related CI workflows | Historical tests prove exact cases run, not universal external-provider behavior |
| `projects/neverland-gps/` | Offline child-safety wearable software and architecture | Prototype/software evidence != manufactured wearable |
| `sports_analysis/`, `sc-physical-quantum-evidence/` | Bounded sports evaluation, structured quantum and physical observation artifacts | Results are scoped to recorded experiments and sources |
| `website/` | Public business, educational and proof pages | Tracked web files do not demonstrate every URL is currently serving them |
| `evidence/`, `proofs/`, `sc-evidence/`, `challenge/` | Receipts, signatures, artifact hashes, adversarial challenge and historical source-bound proofs | Historical receipts remain dated; separate verification of signer, witness, cause and effect needed |
| `commercial/`, `licensing-closure/` | Offer structure and commercial boundaries | Licensing docs are not executed customer contracts |
| `.github/workflows/`, `tests/`, `tools/` | CI gates, integration tests, audit utilities, secret-syntax safeguards | Root `unittest` discovery presently requires additional dependencies, including `fastapi` |

## Changes visible in repository history

- **August 2026:** governance/quantum evidence, canonicalization fixtures, signed public proof families and master indices were already present or developed.
- **Sept 7–13:** Public ProofGate client/Action, Shadow Clone/Codex challenge, cloud maps, Supreme Apex proof and documentary continuity.
- **Sept 15–19:** GEKYUME universal policy layer, transition binding/source identity, kernel v2 source/ABI validation and evidence; source and test workflow hardening; earlier accidental secret was removed from live tree on Sept 19. **Past Git history may retain blobs; removal from HEAD does not revoke the compromised credential.**
- **Sept 20–25:** SC Mail -> Supreme Mail; AWS restriction and Azure fallback documentation; Azure runtime, AWS/Azure witness bridge and Microsoft consent/handoff iteration. Do not confuse CLI tests with final customer OAuth approval.
- **Oct 3:** OWASP ACS falsification lab documentation and CI are the latest baseline `main` history.
- **Oct 9:** Draft PR #26 supplies the new GEKYUME/SCQOS/Forge adapter; independently observed tests and GitHub CI; public current-state update in this separate docs-only change.

## Explicit findings and limitations

1. **Current-state drift:** the root README twice calls the AWS account suspended *as of Sept 23*. This was valid as a dated report then, but misleading without the Oct 9 reachable AWS correction now placed at the top of the README.
2. **Canonical contract drift:** original PR #26 client uses an older `/webhook` tenant/signature convention, whereas Oscar reports `/v1/evidence/ingest` + app/signature/nonce. The PR now also contains a *proposed* V2 staging contract; the receiver has not been verified to accept it.
3. **Integration security boundary:** untrusted raw-IP/self-signed-TLS path was not used. On Oct 9 the hostname did not resolve on the HP terminal and TCP/443 to supplied public IP timed out; no TLS or ledger evidence resulted.
4. **Test environment:** the complete baseline test suite failed to *load some test modules* due to `ModuleNotFoundError: fastapi` on the HP environment. No inference that the affected code's assertions failed. CI results must be checked separately; this docs update does not install dependencies or change production.
5. **Versioning clarity:** external Linux coherence gate, Core, hybrid and webhook repositories need dedicated code/version audits before asserting a complete multi-repo release.
6. **Security hygiene:** repository has certificates/key-named evidence files and past sensitive-removal history. A limited file-extension/DER parser scan did **not** validate a comprehensive secret-free history or current keys. Do not commit or reprint private keys, tokens, EIN, personal data, customer payloads or actual live secrets.
7. **Ownership/attribution:** public README credits collaborator-owned Anabelle/GrassRootsAI separately; preserve that and legal/privacy boundaries.
8. **Naming/structure debt:** tracked root has a few shell-looking filenames and historical audit backups; inventory recorded, but no cleanup/deletion performed in this audit to avoid accidental loss of evidentiary history.

## Integrity checks on this update

Changes in this documentation branch intentionally add public Markdown and a baseline file catalog, plus a dated README correction. No business production deployment, queue draining, IAM/role grant, banking action, live webhook transmission, destructive refactor, archived-evidence rewrite or force push is authorized by this update. Before merging: verify links, perform `git diff --check`, run the repo's independent GitHub CI, and check the resulting commit status. Further technical hardening belongs to reviewed implementation PRs, not to a documentary inventory.

**Read next:** [current verified state](CURRENT_VERIFIED_STATE_2026-10-09.md), [registration and ecosystem](ORGANIZATION_AND_ECOSYSTEM_2026-10-09.md), [chronology and evidence register](EVIDENCE_REGISTER_2026-10-09.md).
