---
type: Project
category: project
title: "lgcr"
description: "A small Linux container runtime written in let-go, built on the syscall namespace."
tags: [runtime, go, interop, tooling]
resource: "https://github.com/nooga/lgcr"
sources: ["repo: nooga/lgcr README, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# lgcr

lgcr is a daemonless Linux container runtime written in [let-go](../entities/let-go.md), providing Docker-like command-line functionality while maintaining a remarkably compact codebase of approximately 3,000 lines. On Linux it bundles into a single executable; on macOS it acts as a native forwarder into a Lima VM, eliminating the need for wrapper scripts.

# Using let-go

lgcr demonstrates [let-go](../entities/let-go.md)'s capacity to implement systems-level programs with direct syscall access:

- **Direct syscall bindings** — leverages [let-go](../entities/let-go.md)'s Go interop layer to bind Linux syscalls for namespace isolation, capability management, and filesystem operations without extra C code.
- **Compact implementation** — 3,000 lines of let-go code replace thousands of lines in traditional implementations, showing the language's expressiveness for low-level systems work.
- **Single-executable deployment** — compiles to a standalone binary on Linux, simplifying distribution and eliminating runtime dependencies.
- **Cross-platform abstraction** — the same codebase runs natively on Linux and as a forwarding client on macOS via Lima, demonstrating let-go's platform portability.

# Idioms

- **OCI registry integration** — lgcr pulls from Docker Hub and v2-compatible registries, implementing image authentication and partial blob resume without external libraries.
- **Container lifecycle with init process** — manages PID 1 init process handling and signal forwarding, a critical systems-programming pattern that let-go handles cleanly via Go interop.

# Citations

[1] [lgcr repository](https://github.com/nooga/lgcr)
