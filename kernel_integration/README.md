# SCQOS Kernel Source Layer v2

This directory replaces the old global `scqos_mode` bit with a scoped,
one-shot kernel authorization bound to the exact process and executable.

## Why v2 exists

The previous loader defined an SCQOS decision function but never invoked it
before attaching the BPF-LSM programs. It also used one global bit for exec,
file-open, capabilities and network connects. That made the kernel path
independent from the actual eight-invariant transition receipt and made a
machine-wide lockout possible.

v2 changes the consequence boundary:

```
transition request
  -> Time
  -> Continuity
  -> Alignment
  -> Genesis
  -> Boundary
  -> Reference
  -> Causality
  -> Consciousness
  -> Coherence
  -> PERMIT receipt
  -> exact PID + executable inode one-shot grant
  -> bprm_check_security
  -> execute or EACCES
  -> kernel audit event
```

The operating system is not globally governed. Only a process explicitly
enrolled by `scqos_kernel_exec.py` is fail-closed.

## Files

- `scqos_exec_gate.bpf.c` — BPF-LSM exec gate.
- `scqos_exec_gate_loader.c` — loads/attaches the program and pins maps.
- `scqos_kernel_exec.py` — forks/stops the exact child, injects its live
  PID/argv/inode/kernel/LSM facts into the universal transition contract,
  requires `PERMIT`, installs the one-shot kernel grant, then resumes it.
- `scqos-kernel-v2.service` — activates only when kernel BTF exists and the
  live LSM list actually contains `bpf`.
- `activate_v2.sh` — compiles/stages v2 first, then retires the unsafe legacy
  global-bit service and enables v2.

## Kernel prerequisites

The host kernel must expose:
- `CONFIG_BPF=y`
- `CONFIG_BPF_SYSCALL=y`
- `CONFIG_BPF_LSM=y`
- `CONFIG_DEBUG_INFO_BTF=y`

The active LSM list must include `bpf`.

The connected laptop currently has all compile-time prerequisites, but its
September 19, 2026 recovery boot omitted `bpf` from the active LSM list.
The normal GRUB configuration already requests it.

## Build

Generate CO-RE type definitions from the running kernel:

```bash
mkdir -p /opt/scqos-v2
bpftool btf dump file /sys/kernel/btf/vmlinux format c > /opt/scqos-v2/vmlinux.h
clang -O2 -g -target bpf -D__TARGET_ARCH_x86 \
  -I/opt/scqos-v2 -c scqos_exec_gate.bpf.c \
  -o /opt/scqos-v2/scqos_exec_gate.bpf.o
cc -O2 scqos_exec_gate_loader.c -o /opt/scqos-v2/scqos_exec_gate_loader \
  -lbpf -lelf -lz
```

The repository CI repeats those compilation checks and verifies that v2 does
not reintroduce the legacy `scqos_mode` global switch.

## Runtime contract

A command is not authorized by the presence of the loader alone.
The exact transition must return `PERMIT` and
`execution_authorized=true` from
`integration.universal_gateway.govern_transition`.

Before that governance call, the launcher binds the proposition to:
- exact stopped child PID;
- resolved executable path;
- exact argv;
- executable device/inode;
- running kernel release;
- active LSM chain.

Example invocation after activation:

```bash
sudo python3 kernel_integration/scqos_kernel_exec.py \
  --request transition.json -- /usr/bin/id
```

The grant expires after 5 seconds by default and is consumed on the first
matching exec. A stale, missing, wrong-PID, or wrong-inode grant returns
`-EACCES` before execution.

## Ubuntu and Alpine

The BPF object is CO-RE based. It is not tied to Ubuntu userspace. Alpine can
use the same source when its running Linux kernel has BPF-LSM and BTF enabled,
`bpf` is present in the active LSM list, and libbpf/bpftool/clang are
available. The connected laptop itself is Ubuntu 26.04.1, so Alpine is a
separate deployment target rather than the identity of the current host.
