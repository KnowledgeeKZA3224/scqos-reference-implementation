#!/usr/bin/env python3
"""
SCQOS kernel source-layer launcher.

The exact child PID, executable inode, argv, running kernel and active LSM
chain are inserted into the transition proposition before governance.
Only a PERMIT receipt for those exact facts creates a one-shot BPF-LSM grant.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
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
    ap.add_argument("--ttl-ms", type=int, default=5000)
    ap.add_argument("command", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    if os.geteuid() != 0:
        raise SystemExit("SCQOS kernel launcher requires root")
    if not args.command:
        raise SystemExit("command required after --request")
    if not GOVERNED.exists() or not EXEC_GRANTS.exists():
        raise SystemExit("SCQOS BPF-LSM v2 maps are not pinned")

    exe = Path(args.command[0]).resolve(strict=True)
    st = exe.stat()
    if not stat.S_ISREG(st.st_mode):
        raise SystemExit("target executable must be a regular file")

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
        "device": int(st.st_dev),
        "inode": int(st.st_ino),
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

        governed_key = struct.pack("<I", pid)
        governed_value = struct.pack("<B", 1)

        # Kernel key layout: u32 tgid + u32 pad + u64 dev + u64 ino.
        exec_key = struct.pack(
            "<IIQQ",
            pid,
            0,
            int(st.st_dev),
            int(st.st_ino),
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
