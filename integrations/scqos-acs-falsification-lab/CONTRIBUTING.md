# Contributing

The preferred contribution is a falsifier: a minimal case tied to a specific pinned ACS requirement that demonstrates an incorrect allow, deny, defer, modify, ask, chain, signature, replay or consequence result.

A new probe must include a positive control when a deny-only corpus could otherwise reward an implementation that simply blocks everything. A harness change should include a mutant that the new check is expected to catch.
