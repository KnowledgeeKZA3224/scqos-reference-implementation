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
