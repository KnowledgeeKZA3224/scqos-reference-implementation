// SPDX-License-Identifier: GPL-2.0
// SCQOS BPF-LSM v2 loader: load, attach, pin maps, keep links alive.
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <bpf/libbpf.h>

#define OBJ_PATH "/opt/scqos-v2/scqos_exec_gate.bpf.o"
#define PIN_ROOT "/sys/fs/bpf/scqos-v2"

static volatile sig_atomic_t stop_requested;

static void on_signal(int signo)
{
    (void)signo;
    stop_requested = 1;
}

static int ensure_pin_root(void)
{
    if (mkdir(PIN_ROOT, 0755) == 0 || errno == EEXIST)
        return 0;
    perror("mkdir " PIN_ROOT);
    return -1;
}

static void unlink_stale_pins(void)
{
    unlink(PIN_ROOT "/governed");
    unlink(PIN_ROOT "/exec_grants");
    unlink(PIN_ROOT "/events");
}

int main(void)
{
    struct bpf_object *obj = NULL;
    struct bpf_program *prog;
    struct bpf_map *map;
    struct bpf_link *links[16] = {0};
    size_t link_count = 0;
    int rc = 1;

    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    if (ensure_pin_root())
        return 2;
    unlink_stale_pins();

    obj = bpf_object__open_file(OBJ_PATH, NULL);
    if (!obj) {
        fprintf(stderr, "SCQOS: cannot open %s\n", OBJ_PATH);
        return 3;
    }

    if (bpf_object__load(obj)) {
        fprintf(stderr, "SCQOS: BPF object load failed\n");
        goto out;
    }

    bpf_object__for_each_map(map, obj) {
        char path[512];
        snprintf(path, sizeof(path), "%s/%s",
                 PIN_ROOT, bpf_map__name(map));
        if (bpf_map__pin(map, path) && errno != EEXIST) {
            fprintf(stderr, "SCQOS: map pin failed %s: %s\n",
                    path, strerror(errno));
            goto out;
        }
    }

    bpf_object__for_each_program(prog, obj) {
        if (link_count >= 16) {
            fprintf(stderr, "SCQOS: too many programs\n");
            goto out;
        }
        links[link_count] = bpf_program__attach_lsm(prog);
        if (libbpf_get_error(links[link_count])) {
            fprintf(stderr, "SCQOS: attach failed for %s\n",
                    bpf_program__name(prog));
            links[link_count] = NULL;
            goto out;
        }
        link_count++;
    }

    printf("SCQOS_KERNEL_V2_ACTIVE programs=%zu\n", link_count);
    fflush(stdout);
    rc = 0;

    while (!stop_requested)
        pause();

out:
    for (size_t i = 0; i < link_count; i++)
        bpf_link__destroy(links[i]);
    bpf_object__close(obj);
    return rc;
}
