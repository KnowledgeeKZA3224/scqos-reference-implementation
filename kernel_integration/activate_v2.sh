#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SRC="$REPO_ROOT/kernel_integration"
DEST=/opt/scqos-v2
UNIT=/etc/systemd/system/scqos-kernel-v2.service
OLD_UNIT=scqos-lsm.service
NEW_UNIT=scqos-kernel-v2.service

if [ "$(id -u)" -ne 0 ]; then
  echo "SCQOS_HOLD reason=root_required" >&2
  exit 10
fi

case "$(uname -m)" in
  x86_64|amd64) BPF_ARCH=x86 ;;
  aarch64|arm64) BPF_ARCH=arm64 ;;
  s390x) BPF_ARCH=s390 ;;
  ppc64le|ppc64) BPF_ARCH=powerpc ;;
  riscv64) BPF_ARCH=riscv ;;
  *)
    echo "SCQOS_HOLD reason=unsupported_arch arch=$(uname -m)" >&2
    exit 13
    ;;
esac

for tool in clang bpftool cc systemctl grep install; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "SCQOS_HOLD reason=missing_tool tool=$tool" >&2
    exit 11
  fi
done

if [ ! -r /sys/kernel/btf/vmlinux ]; then
  echo "SCQOS_HOLD reason=kernel_btf_unavailable" >&2
  exit 12
fi

if ! grep -qs ' /sys/fs/bpf bpf ' /proc/mounts; then
  echo "SCQOS_HOLD reason=bpffs_not_mounted" >&2
  exit 14
fi

mkdir -p "$DEST"

# Compile everything before changing service ownership of the consequence path.
bpftool btf dump file /sys/kernel/btf/vmlinux format c > "$DEST/vmlinux.h"

clang -O2 -g -target bpf "-D__TARGET_ARCH_$BPF_ARCH"   -I"$DEST"   -c "$SRC/scqos_exec_gate.bpf.c"   -o "$DEST/scqos_exec_gate.bpf.o"

cc -O2 "$SRC/scqos_exec_gate_loader.c"   -o "$DEST/scqos_exec_gate_loader"   -lbpf -lelf -lz

install -m 0755 "$SRC/scqos_kernel_exec.py"   /usr/local/sbin/scqos-kernel-exec
install -m 0644 "$SRC/scqos-kernel-v2.service" "$UNIT"

systemctl daemon-reload

# The old global-bit loader is superseded only after v2 compiled and staged.
if systemctl list-unit-files "$OLD_UNIT" >/dev/null 2>&1; then
  systemctl disable --now "$OLD_UNIT" || true
fi

systemctl enable "$NEW_UNIT"

if grep -qw bpf /sys/kernel/security/lsm; then
  systemctl restart "$NEW_UNIT"
  systemctl is-active --quiet "$NEW_UNIT"
  test -e /sys/fs/bpf/scqos-v2/governed
  test -e /sys/fs/bpf/scqos-v2/exec_grants
  echo "SCQOS_KERNEL_V2_ACTIVE"
  exit 0
fi

echo "SCQOS_KERNEL_V2_STAGED active_lsm=$(cat /sys/kernel/security/lsm)"
echo "SCQOS_HOLD reason=bpf_lsm_not_active_normal_boot_required"
exit 20
