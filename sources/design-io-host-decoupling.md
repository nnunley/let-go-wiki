---
type: Source
category: source
title: "Design: Decoupling Runtime I/O from the Host"
description: "Design for decoupling runtime I/O from concrete host implementations across native, Go embedder, and WebAssembly platforms."
tags: [runtime, wasm, go, interop]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/runtime-io-host-decoupling.md"
sources: ["repo: nooga/let-go docs/design/runtime-io-host-decoupling.md, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
last-verified: "2026-06-18"
human-verified: "2026-06-18"
status: active
---

## What this is

A design document from the let-go project articulating the architecture for separating I/O operations (output, input, event emit) from the concrete runtime host. It covers the problem (runtime reaching directly for `os.Stdout`, `syscall/js`, and host-specific shims), the solution (I/O seams as dynamic bindings over thin interfaces), and the shipping status across three platforms: native binary, Go embedder (`pkg/api`), and WebAssembly. Status is active; the design rationale stands as shipped PRs (#206, #207, #223, #231, #241, #244) landed the implementation.

## Key takeaways

- **The core abstraction:** The runtime exposes *I/O seams*—dynamic variables (`*out*`, `*err*`, `*in*`) holding abstract handles over `io.Writer`, `io.Reader`, and capability interfaces. The host binds the concrete destination/source at construction; guest code names the capability (`println`, `read-key`, `emit`), and the host supplies the backend.

- **One contract, three bindings:** Native CLI wraps `os.Stdout` / `os.Stdin`; Go embedder via `pkg/api` pushes per-`Run` bindings (e.g. `WithStdout`); WASM uses adapter bridges (`HostWriter`, `HostReader`) forwarding to the JS host. All three reach the same seam.

- **Design principle:** "Host-bound capabilities live in `pkg/rt`, never `pkg/vm`." The VM core remains free of host assumptions (no `syscall/js`, no file-descriptor interception). The seam is as thin as the operation allows—output is a plain byte stream; input needs a slightly richer set (keystroke reading, pending-key check, terminal size, raw mode) because cross-platform semantics diverge.

- **Status:** Shipped. All three streams now route through host-bound seams, eliminating the shim layer. The browser bundle no longer intercepts file descriptors. Client-owned shells launch via `-w-shell none` (#245), wiring peer capabilities through the same seam pattern.

- **Open work:** Peer capabilities (graphics via sixel/canvas, audio, controller input) extend the model into #255. The cross-platform wake protocol for unblocking WASM reads without a real keystroke remains unresolved.

## Derived pages

- [io-host-decoupling](../concepts/io-host-decoupling.md)

# Citations

- `resource`: https://github.com/nooga/let-go/blob/main/docs/design/runtime-io-host-decoupling.md
