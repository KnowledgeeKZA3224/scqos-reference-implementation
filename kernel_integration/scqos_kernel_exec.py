#!/usr/bin/env python3
"""
SCQOS kernel source-layer launcher.

Flow:
1. Validate the exact transition with integration.universal_gateway.
2. Fork a child and stop it before exec.
3. Bind the PERMIT receipt to that child + exact executable inode.
4. Resume the child.
5. BPF-LSM consumes the one-shot grant at bprm_check_security.
"""
from __future__ import annotations

import argparse
import json
import os
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


def _dev_u64(st_dev: int) -> int:
    return int(st_dev)


def _nonce(receipt_hash: str) -> int:
    return int(receipt_hash[:16], 16)


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

    exe = Path(args.command[0]).resolve(strict=True)
    st = exe.stat()
    if not stat.S_ISREG(st.st_mode):
        raise SystemExit("target executable must be a regular file")

    request_data = json.loads(Path(args.request).read_text())
    request = TransitionRequest.model_validate(request_data)
    result = govern_transition(request)

    print(json.dumps({
        "decision": result.decision,
        "execution_authorized": result.execution_authorized,
        "transition_id": result.transition_id,
        "receipt_hash": result.receipt_hash,
        "final_proof": result.final_proof,
    }, sort_keys=True))

    if result.decision != "PERMIT" or not result.execution_authorized:
        return 2 if result.decision == "HOLD" else 3

    if not GOVERNED.exists() or not EXEC_GRANTS.exists():
        raise SystemExit("SCQOS BPF-LSM v2 maps are not pinned")

    pid = os.fork()
    if pid == 0:
        os.kill(os.getpid(), signal.SIGSTOP)
        os.execv(str(exe), [str(exe), *args.command[1:]])
        os._exit(127)

    _, status = os.waitpid(pid, os.WUNTRACED)
    if not os.WIFSTOPPED(status):
        raise RuntimeError("child did not stop before exec")

    governed_key = struct.pack("<I", pid)
    governed_value = struct.pack("<B", 1)

    # Kernel struct alignment: u32 + pad + u64 + u64.
    exec_key = struct.pack("<IIQQ", pid, 0, _dev_u64(st.st_dev), st.st_ino)

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


if __name__ == "__main__":
    raise SystemExit(main())
