#!/usr/bin/env python3
"""
SCQOS kernel source-layer launcher.

The exact child PID, executable inode, argv, running kernel and active LSM
chain are inserted into the transition proposition before governance.
Only a PERMIT receipt for those exact facts creates a one-shot BPF-LSM grant.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from integration.universal_gateway import TransitionRequest, govern_transition

PIN_ROOT = Path("/sys/fs/bpf/scqos-v2")
GOVERNED = PIN_ROOT / "governed"
EXEC_GRANTS = PIN_ROOT / "exec_grants"


def _hex_words(blob: bytes) -> list[str]:
    return [f"{b:02x}" for b in blob]


def _bpftool_update(path: Path, key: bytes, value: bytes) -> None:
    subprocess.run(
        [
            "bpftool", "map", "update", "pinned", str(path),
            "key", "hex", *_hex_words(key),
            "value", "hex", *_hex_words(value),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _bpftool_delete(path: Path, key: bytes) -> None:
    subprocess.run(
        [
            "bpftool", "map", "delete", "pinned", str(path),
            "key", "hex", *_hex_words(key),
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _active_lsms() -> str:
    try:
        return Path("/sys/kernel/security/lsm").read_text().strip()
    except OSError:
        return "unavailable"


def _nonce(receipt_hash: str) -> int:
    # Correlation token only. Authorization is the privileged pinned-map entry.
    return int(receipt_hash[:16], 16)


def _kernel_dev(st_dev: int) -> int:
    """Encode userspace dev_t as the kernel's 32-bit MKDEV layout."""
    major = os.major(st_dev)
    minor = os.minor(st_dev)
    if major >= (1 << 12) or minor >= (1 << 20):
        raise ValueError(
            f"device number outside kernel dev_t bounds: major={major} minor={minor}"
        )
    return (major << 20) | minor


def _resolve_executable(value: str) -> Path:
    if "/" in value:
        return Path(value).resolve(strict=True)
    resolved = shutil.which(value)
    if not resolved:
        raise FileNotFoundError(value)
    return Path(resolved).resolve(strict=True)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_identity(path: Path) -> dict[str, str]:
    st = path.stat()
    if not stat.S_ISREG(st.st_mode):
        raise ValueError("target executable must be a regular file")
    return {
        "stat_dev": str(int(st.st_dev)),
        "kernel_dev": str(_kernel_dev(st.st_dev)),
        "device_major": str(os.major(st.st_dev)),
        "device_minor": str(os.minor(st.st_dev)),
        "inode": str(int(st.st_ino)),
        "size": str(int(st.st_size)),
        "mtime_ns": str(int(st.st_mtime_ns)),
        "ctime_ns": str(int(st.st_ctime_ns)),
        "sha256": _sha256_file(path),
    }


def _kill_stopped_child(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", required=True)
    ap.add_argument("--ttl-ms", type=int, default=1000)
    ap.add_argument("command", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    if os.geteuid() != 0:
        raise SystemExit("SCQOS kernel launcher requires root")
    if not args.command:
        raise SystemExit("command required after --request")
    if not 100 <= args.ttl_ms <= 5000:
        raise SystemExit("ttl-ms must be between 100 and 5000")
    if not GOVERNED.exists() or not EXEC_GRANTS.exists():
        raise SystemExit("SCQOS BPF-LSM v2 maps are not pinned")

    exe = _resolve_executable(args.command[0])
    identity = _file_identity(exe)

    request_data = json.loads(Path(args.request).read_text())

    pid = os.fork()
    if pid == 0:
        os.kill(os.getpid(), signal.SIGSTOP)
        os.execv(str(exe), [str(exe), *args.command[1:]])
        os._exit(127)

    _, status = os.waitpid(pid, os.WUNTRACED)
    if not os.WIFSTOPPED(status):
        _kill_stopped_child(pid)
        raise RuntimeError("child did not stop before exec")

    binding = {
        "pid": pid,
        "path": str(exe),
        "argv": [str(exe), *args.command[1:]],
        **identity,
        "kernel_release": platform.release(),
        "active_lsms": _active_lsms(),
    }

    try:
        request_data.setdefault("proposed_transition", {})[
            "kernel_exec"
        ] = binding
        request_data.setdefault("expected_consequence", {})[
            "kernel_exec"
        ] = binding
        request_data.setdefault("current_state", {})[
            "kernel_runtime"
        ] = {
            "kernel_release": binding["kernel_release"],
            "active_lsms": binding["active_lsms"],
        }

        request = TransitionRequest.model_validate(request_data)
        result = govern_transition(request)

        print(json.dumps({
            "decision": result.decision,
            "execution_authorized": result.execution_authorized,
            "transition_id": result.transition_id,
            "receipt_hash": result.receipt_hash,
            "final_proof": result.final_proof,
            "kernel_binding": binding,
        }, sort_keys=True))

        if result.decision != "PERMIT" or not result.execution_authorized:
            _kill_stopped_child(pid)
            return 2 if result.decision == "HOLD" else 3

        # Reference must still be the exact executable that was governed.
        if _file_identity(exe) != identity:
            _kill_stopped_child(pid)
            raise RuntimeError("executable changed after governance")

        governed_key = struct.pack("<I", pid)
        governed_value = struct.pack("<B", 1)

        # Kernel key layout: u32 tgid + u32 pad + u64 dev + u64 ino.
        exec_key = struct.pack(
            "<IIQQ",
            pid,
            0,
            int(identity["kernel_dev"]),
            int(identity["inode"]),
        )

        expires_ns = time.monotonic_ns() + args.ttl_ms * 1_000_000
        grant_value = struct.pack(
            "<QQ",
            expires_ns,
            _nonce(result.receipt_hash),
        )

        _bpftool_update(GOVERNED, governed_key, governed_value)
        _bpftool_update(EXEC_GRANTS, exec_key, grant_value)

        try:
            os.kill(pid, signal.SIGCONT)
            _, child_status = os.waitpid(pid, 0)
            if os.WIFEXITED(child_status):
                return os.WEXITSTATUS(child_status)
            if os.WIFSIGNALED(child_status):
                return 128 + os.WTERMSIG(child_status)
            return 1
        finally:
            _bpftool_delete(GOVERNED, governed_key)
            _bpftool_delete(EXEC_GRANTS, exec_key)

    except BaseException:
        _kill_stopped_child(pid)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
