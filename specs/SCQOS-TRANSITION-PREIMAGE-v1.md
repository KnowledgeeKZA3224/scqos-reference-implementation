# SCQOS Transition Preimage v1

**Status:** FROZEN  
**Identifier:** `SCQOS-TRANSITION-PREIMAGE-v1`  
**Hash:** SHA-256  
**Encoding:** UTF-8

## Purpose

This contract defines a transition identity from the transition's own content. It does not depend on wall-clock time, sequence counters, nonces, receipt history, or which participating system computed it. Independent systems that bind the same transition content MUST derive the same digest.

## Exact field set and order

The hashed preimage contains exactly these seven fields, in this exact order:

1. `version`
2. `artifact_identity`
3. `evidence_identity`
4. `authority_identity`
5. `purpose`
6. `pre_state`
7. `consequence`

`version` MUST equal `SCQOS-TRANSITION-PREIMAGE-v1`.

Each remaining field MUST be exactly 64 lowercase hexadecimal characters representing a SHA-256 identity already derived by the participating system from its native evidence.

No additional field is permitted inside the hashed preimage.

## Canonical byte layout

For each field in the order above, append exactly:

```text
<field-name>=<field-value>\n
```

The final line also ends in one LF byte (`0x0a`). There are no spaces, no CR bytes, no JSON encoding, and no optional fields.

The transition identity is:

```text
transition_id = SHA256(canonical_preimage_bytes).hexdigest()
```

## Explicit exclusions

The following MUST NOT appear in the hashed preimage:

- timestamps or wall-clock values;
- random nonces;
- monotonic sequence numbers;
- prior receipt hashes;
- transport/request IDs;
- signatures;
- optional reconstruction metadata.

Those values may exist outside the identity for replay protection, ordering, observation, or cryptographic attestation, but changing one MUST NOT change the content-derived transition identity.

## Binding semantics

- `artifact_identity` identifies the exact artifact/content being allowed to act.
- `evidence_identity` identifies the evidence proposition being relied upon.
- `authority_identity` identifies the current rooted authority/grant binding.
- `purpose` identifies the allowed purpose.
- `pre_state` identifies the state against which the transition is qualified.
- `consequence` identifies the consequence being authorized.
- `version` fixes the interpretation of all fields above.

A verifier MUST fail closed when the field set, field order, version, encoding, identity width, authority/grant state, purpose, lineage, artifact identity, or derived digest is inconsistent with current authority.

## Canonical test vector

```text
version=SCQOS-TRANSITION-PREIMAGE-v1
artifact_identity=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
evidence_identity=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
authority_identity=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
purpose=dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
pre_state=eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
consequence=ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
```

Expected SHA-256 digest:

```text
8220d6835327217e402d481e4adfafec32ace165e697eec6c37d92619e36b064
```

Any conforming independent implementation MUST produce that exact digest before participating in a live shared-transition proof.

## Production SCQOS binding

The live SCQOS authority witness and production witness bridge in `us-east-1` implement this contract. The transition identity is content-derived; nonce and monotonic sequence remain outside the hashed preimage and are used only as qualification/replay controls.
