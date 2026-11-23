---
type: Project
category: project
title: "lgcr"
description: "A small Linux container runtime written in let-go, built on the syscall namespace."
tags: [runtime, go, interop, tooling]
resource: "https://github.com/nooga/lgcr"
sources: ["repo: nooga/lgcr README, 2026-07-02", "repo: nooga/let-go README.md pkg/rt/syscall_linux.go pkg/rt/syscall_other.go @ b82588292b, 2026-10-20"]
created: "2026-07-02"
updated: "2026-10-20"
status: active
---

# lgcr

lgcr is a daemonless Linux container runtime written in [let-go](../entities/let-go.md), providing Docker-like command-line functionality in a codebase of approximately 3,000 lines. On Linux it bundles into a single executable; on macOS it acts as a native forwarder into a Lima VM, eliminating the need for wrapper scripts. The let-go README lists lgcr among its examples as "a daemonless container runtime, built on the `syscall` namespace" [2].

# Using let-go

lgcr uses [let-go](../entities/let-go.md)'s built-in `syscall` namespace for systems-level work [2].

- **Built-in syscall namespace, not generated interop** — let-go implements the `syscall` namespace by hand in `pkg/rt/syscall_linux.go` [3]. The namespace defines namespace creation (`clone`, `unshare`), mounts and root changes (`mount`, `umount`, `pivot-root`, `chroot`), file operations, `setuid`/`setgid`, `capset`, `prctl`, and process control (`spawn`, `exec`, `kill`, `waitpid`) [3]. It is separate from the `lginterop`-generated Go bindings described in the Go interop guide [5]. The let-go README says lgcr is built on this namespace [2].
- **Seccomp default filter** — `syscall/seccomp-default` installs the default seccomp filter, which the source comment describes as "lgcr's built-in default seccomp filter" [3]. The filter's syscall list includes `mount`, `pivot_root`, `unshare`, `setns`, `bpf`, `ptrace`, and `init_module` [3].
- **AppArmor stack transition** — `syscall/apparmor-stack-onexec` schedules an AppArmor profile stack transition at the next exec boundary [3].
- **Linux-only namespace** — on non-Linux builds let-go installs `syscall` with stubs. `syscall/getpid`, `getuid`, `getgid`, the file helpers, and the `CLONE_*`, `MS_*`, and `SIG*` constants work. Every other function listed in that file, including `clone`, `unshare`, `mount`, `chroot`, `exec`, `kill`, `signal-notify`, and `waitpid`, returns the error `syscall/<name> is only supported on Linux` [4].
- **Compact implementation** — the lgcr README gives the size as approximately 3,000 lines of let-go code [1].
- **Single-executable deployment** — let-go compiles programs to standalone binaries [2]. lgcr bundles into a single executable on Linux [1].
- **Cross-platform build** — the same codebase builds for Linux, where it runs natively, and for macOS, where it runs as a forwarding client into Lima [1]. On macOS, the stubbed operations (`clone`, `unshare`, `mount`, `pivot-root`, `chroot`, `mkdir`, `chdir`, `exec`, `spawn`, `kill`, `waitpid`, `setuid`, `setgid`, `capset`, `prctl`, and others) return the error `syscall/<name> is only supported on Linux` [4]. The file helpers (`read-file`, `write-file`, `mkdir-p`, `rm-rf`, `rm`, `symlink`, `chmod`) are registered as working functions [4].

# Idioms

- **OCI registry integration** — lgcr pulls from Docker Hub and v2-compatible registries, implementing image authentication and partial blob resume without external libraries [1].
- **Container lifecycle with init process** — lgcr manages PID 1 init process handling and signal forwarding [1]. let-go's `syscall` namespace defines the primitives for this: `signal-notify` delivers received signals onto a channel, `kill` sends a signal to a pid, and `waitpid` returns the pid, exit status, and terminating signal of a child [3]. This page cites no lgcr source showing which of these calls lgcr makes.

# Citations

[1] [lgcr repository](https://github.com/nooga/lgcr), README, as cited in `sources` (2026-07-02)

[2] [let-go README.md at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/README.md)

[3] [let-go pkg/rt/syscall_linux.go at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/syscall_linux.go)

[4] [let-go pkg/rt/syscall_other.go at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/syscall_other.go)

[5] [let-go docs/guide/go-interop.md at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/guide/go-interop.md)
