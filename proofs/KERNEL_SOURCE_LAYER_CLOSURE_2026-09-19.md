# Kernel Source-Layer Closure Record — 2026-09-19

## Live observations

Connected host:
- Ubuntu 26.04.1 LTS
- Linux 7.0.0-31-generic
- current command line contains `recovery nomodeset dis_ucode_ldr`
- current active LSM list omits `bpf`
- kernel config contains `CONFIG_BPF_LSM=y` and `CONFIG_DEBUG_INFO_BTF=y`
- normal GRUB defaults already request `bpf`
- Amazon SSM Agent and its worker are running
- `scqos.service`, `scqos-execve.service`, and the legacy
  `scqos-lsm.service` are enabled

## Legacy gap

The legacy LSM loader defines `scqos_decision()` but does not call it before
the BPF programs are attached. Its BPF side uses one global byte for exec,
file-open, capability and socket-connect authorization. The map is initialized
to zero independently of an eight-invariant transition receipt.

A June 1 proof on kernel 7.0.0-22 recorded `bpf` in the active LSM list.
The September 19 recovery boot does not. That means the historical attachment
is continuity evidence, not proof of current enforcement.

## v2 closure

PR #20 introduces:
- exact child PID + executable inode authorization;
- one-shot, expiring BPF map grants;
- live PID/argv/inode/kernel/LSM facts inserted into the universal transition
  proposition before governance;
- `PERMIT && execution_authorized` required before a grant exists;
- kernel `bprm_check_security` as the final pre-exec consequence gate;
- old global loader disabled only after v2 successfully compiles and stages;
- v2 systemd activation conditioned on BTF and an active `bpf` LSM.

The OS is never put behind a machine-wide SCQOS bit. Only explicitly enrolled
processes become fail-closed.

## Alpine boundary

No Alpine installation was found on the connected laptop or in the searched
SCQOS repository tree. The v2 BPF code is CO-RE based and can target Alpine
when that Alpine kernel exposes BPF-LSM and BTF. Alpine is therefore a
separate deployment target, not the identity of the currently connected host.
