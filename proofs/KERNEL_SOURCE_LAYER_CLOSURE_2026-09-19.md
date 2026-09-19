# Kernel Source-Layer Closure Record — 2026-09-19

## Live observations

Connected host:
- Ubuntu 26.04.1 LTS
- Linux 7.0.0-31-generic
- current command line contains `recovery nomodeset dis_ucode_ldr`
- current active LSM list omits `bpf`
- kernel config contains `CONFIG_BPF_LSM=y` and `CONFIG_DEBUG_INFO_BTF=y`
- normal GRUB defaults already request `bpf`
- bpffs is mounted at `/sys/fs/bpf`
- Amazon SSM Agent and its worker are running
- `scqos.service`, `scqos-execve.service`, and the legacy
  `scqos-lsm.service` are enabled on the observed recovery boot

## Legacy gap

The legacy LSM loader defines `scqos_decision()` but does not call it before
the BPF programs are attached. Its BPF side uses one global byte for exec,
file-open, capability and socket-connect authorization. The map is initialized
independently of an eight-invariant transition receipt.

A June 1 proof on kernel 7.0.0-22 recorded `bpf` in the active LSM list.
The September 19 recovery boot does not. That historical attachment is
continuity evidence, not proof of current enforcement.

## Mainline source-layer v2

The v2 source is integrated directly on `main` under
`kernel_integration/`. It replaces the machine-wide bit with an explicitly
enrolled, one-shot execution boundary.

Before a kernel grant exists, the launcher binds these facts into the existing
universal SCQOS transition proposition:
- stopped child PID;
- resolved executable path and exact argv;
- userspace device identity plus kernel `dev_t` encoding;
- inode, size, mtime and ctime;
- SHA-256 of the executable contents;
- running kernel release;
- active LSM chain.

The existing `govern_transition` path must return both `PERMIT` and
`execution_authorized=true`. The executable identity is recomputed after
governance and must still match before any grant is inserted.

The BPF-LSM map grant is then bound to the exact process + executable
device/inode. It expires after a bounded 100–5000 ms window (1000 ms default)
and is consumed on the first matching execution. Missing, stale or mismatched
authorization returns `-EACCES` at `bprm_check_security`.

The operating system is never placed behind a machine-wide SCQOS bit. Only a
process explicitly enrolled by the launcher becomes fail-closed.

## Deployment handoff

`activate_v2.sh` verifies root, architecture, compiler/tooling, kernel BTF and
bpffs, compiles the CO-RE object and loader, stages the new systemd unit, then
retires the legacy global-bit unit only after v2 has compiled successfully.

`scqos-kernel-v2.service` starts only when BTF exists and `bpf` is present
in the live LSM list. On the currently observed recovery boot, activation
therefore remains HOLD rather than falsely claiming kernel enforcement. The
normal GRUB configuration already contains the required `bpf` LSM argument.

## Validation

The mainline GitHub workflow compiles the BPF-LSM object and userspace loader,
syntax-checks the Python launcher and activation script, checks the userspace /
kernel map ABI, verifies kernel device-number encoding, verifies executable
reference hashing, and rejects reintroduction of the legacy global
`scqos_mode` switch in executable source.

## Independent build receipts

GitHub Actions independently compiled and checked the mainline source:
- kernel workflow run `35475904457` — SUCCESS;
- stricter kernel workflow run `35475910972` — SUCCESS.

The stricter run completed dependency/tool resolution, BTF-derived
`vmlinux.h`, BPF-LSM compilation, userspace-loader compilation, launcher and
activation syntax checks, userspace/kernel map ABI checks, kernel device-number
encoding checks, executable-reference hashing checks, and source-layer
invariant assertions.

## Alpine boundary

No Alpine installation was found on the connected laptop or in the searched
SCQOS repository tree. v2 is CO-RE based and architecture-aware; it can target
an Alpine Linux kernel when that kernel exposes BPF-LSM and BTF and has
`bpf` active in the LSM list. Alpine remains a separate deployment target
from the currently connected Ubuntu host.


## Live activation closure

The recovery-boot observations above are now historical. The host was
transitioned through a normal boot and independently re-verified through the
AWS Systems Manager control plane.

Post-boot state:
- boot ID: `4503f3f3-c1a3-4269-a9b8-09b5f58c8e19`;
- kernel: `7.0.0-31-generic`;
- kernel command line uses the normal boot path and includes
  `lsm=lockdown,capability,landlock,yama,apparmor,bpf,ima,evm`;
- active LSM chain includes `bpf`;
- `scqos-kernel-v2.service` is enabled and active;
- legacy `scqos-lsm.service` is inactive;
- pinned `governed` and `exec_grants` maps are present under
  `/sys/fs/bpf/scqos-v2`.

The activation path was hardened after live execution exposed two boundary
issues: the installed launcher initially lost its repository Python runtime,
and immediate post-restart map checks could race service startup. The activator
now binds the installed wrapper to a validated Python runtime, proves
`--help` can traverse that runtime, and waits boundedly for both service
activity and pinned maps before declaring ACTIVE.

## Live consequence receipts

A harmless governed execution of `/usr/bin/true` was evaluated through the
existing eight-invariant `govern_transition` path and then released through
the live BPF-LSM consequence gate.

PERMIT receipt:
- decision: `PERMIT`;
- `execution_authorized=true`;
- transition ID:
  `7b30ecbd6f2234c0b49d03af2896af7b1300d43ebda31238a7fed23d53424c4d`;
- receipt hash:
  `b6df0f1d280b1de640467576d312a580946b975211bbeec6145db084f5dad98c`;
- final proof:
  `96f848132b78df3d4985828ae928a3263e8b9c6b5e8947461140bd458736898e`;
- resolved executable: `/usr/bin/gnutrue`;
- executable SHA-256:
  `913a39cd38f353497086bcf317b12f91f93c23b51869cea763b8340b4f84cfd3`;
- child exit code: `0`.

A separate fail-closed harness enrolled a stopped child in the live
`governed` map without inserting an execution grant. When resumed, the
kernel denied `exec` with `EACCES`; the harness recorded child exit `77`
and `SCQOS_KERNEL_DENY_PROOF_GREEN`. This proves the consequence hook is
enforcing rather than merely logging.

Live execution also exposed that nanosecond timestamps and other opaque kernel
identifiers can exceed the RFC 8785 safe JSON integer domain. Those identity
facts are now canonicalized as decimal strings before governance while the
kernel map path converts the exact device/inode fields back to integers for
the BPF ABI. The same executable identity is recomputed after governance, so
the reference check remains exact.

Local pre-push verification completed with:
- Python compileall: GREEN;
- 25/25 unit tests: GREEN;
- ProofGate frozen adversarial matrix: 6/6 GREEN;
- live BPF-LSM PERMIT path: GREEN;
- live BPF-LSM missing-grant deny path: GREEN.
