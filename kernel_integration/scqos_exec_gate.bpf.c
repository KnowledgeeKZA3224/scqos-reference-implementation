// SPDX-License-Identifier: GPL-2.0
// SCQOS kernel source-layer v2: scoped, one-shot exec authorization.
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>

char LICENSE[] SEC("license") = "GPL";

struct governed_key {
    __u32 tgid;
};

struct exec_key {
    __u32 tgid;
    __u32 pad;
    __u64 dev;
    __u64 ino;
};

struct grant_value {
    __u64 expires_ns;
    __u64 decision_nonce;
};

struct audit_event {
    __u64 ts_ns;
    __u64 decision_nonce;
    __u64 dev;
    __u64 ino;
    __u32 tgid;
    __s32 result;
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 4096);
    __type(key, struct governed_key);
    __type(value, __u8);
} governed SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 16384);
    __type(key, struct exec_key);
    __type(value, struct grant_value);
} exec_grants SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 1 << 22);
} events SEC(".maps");

static __always_inline void audit(__u32 tgid, __u64 dev, __u64 ino,
                                  __u64 nonce, int result)
{
    struct audit_event *e = bpf_ringbuf_reserve(&events, sizeof(*e), 0);
    if (!e)
        return;
    e->ts_ns = bpf_ktime_get_ns();
    e->decision_nonce = nonce;
    e->dev = dev;
    e->ino = ino;
    e->tgid = tgid;
    e->result = result;
    bpf_ringbuf_submit(e, 0);
}

SEC("lsm/bprm_check_security")
int BPF_PROG(scqos_exec_gate, struct linux_binprm *bprm, int ret)
{
    if (ret)
        return ret;

    __u32 tgid = (__u32)(bpf_get_current_pid_tgid() >> 32);
    struct governed_key gk = {.tgid = tgid};
    __u8 *is_governed = bpf_map_lookup_elem(&governed, &gk);

    // The operating system remains outside this hook unless explicitly
    // enrolled by the SCQOS launcher. This avoids machine-wide deadlock.
    if (!is_governed || *is_governed != 1)
        return 0;

    struct file *file = BPF_CORE_READ(bprm, file);
    if (!file) {
        audit(tgid, 0, 0, 0, -13);
        return -13;
    }

    struct inode *inode = BPF_CORE_READ(file, f_inode);
    if (!inode) {
        audit(tgid, 0, 0, 0, -13);
        return -13;
    }

    __u64 ino = BPF_CORE_READ(inode, i_ino);
    struct super_block *sb = BPF_CORE_READ(inode, i_sb);
    __u64 dev = sb ? BPF_CORE_READ(sb, s_dev) : 0;

    struct exec_key key = {
        .tgid = tgid,
        .pad = 0,
        .dev = dev,
        .ino = ino,
    };

    struct grant_value *grant = bpf_map_lookup_elem(&exec_grants, &key);
    if (!grant) {
        audit(tgid, dev, ino, 0, -13);
        return -13;
    }

    if (grant->expires_ns < bpf_ktime_get_ns()) {
        __u64 nonce = grant->decision_nonce;
        bpf_map_delete_elem(&exec_grants, &key);
        audit(tgid, dev, ino, nonce, -13);
        return -13;
    }

    __u64 nonce = grant->decision_nonce;
    bpf_map_delete_elem(&exec_grants, &key);
    bpf_map_delete_elem(&governed, &gk);
    audit(tgid, dev, ino, nonce, 0);
    return 0;
}
