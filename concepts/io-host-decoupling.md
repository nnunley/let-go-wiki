---
type: Concept
category: concept
title: "Runtime I/O and Host Decoupling"
description: "How the runtime decouples I/O operations from the host platform, enabling the same runtime to run natively, in WASM, and on exotic hosts."
tags: [runtime, wasm, go, interop]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/runtime-io-host-decoupling.md"
sources: ["design: runtime-io-host-decoupling.md, 2026-06-18"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# Runtime I/O and Host Decoupling

The let-go runtime originally hardcoded I/O to platform-specific sinks: `os.Stdout` on native, `fs.writeSync` shims in WASM. This coupling required each host to maintain its own shims. The design decouples I/O by exposing **seams**—small, typed boundaries where each host binds the concrete stream.

## The Problem: Parallel I/O Paths

There were four distinct paths for "write a string from `.lg` code":

- **native `lg`** → `os.Stdout` → terminal
- **`lg -w` bundle** → `os.Stdout` → `fs.writeSync` shim → `LetGoHost._output` → the page
- **WASM track** → `os.Stdout` → `wasm_exec.js` default → DevTools console
- **`lg -b` native** (third-party CLIs) → `os.Stdout` → terminal

Each host inserted itself at a different layer and maintained its own shim. The solution: finish what was half-built—make the runtime consult dynamic variables for I/O instead of hardcoding sinks.

## The Model: One Contract, Multiple Bindings

The runtime already had the right abstraction partially in place: `*in*`, `*out*`, `*err*` are dynamic variables holding an `IOHandle`, which wraps an `io.Writer` and/or `io.Reader`. The design finishes it:

- **native** → the handle wraps `os.Stdout` / `os.Stdin`
- **embedder** (Go via `pkg/api`) → constructor options (`WithStdout`, `WithStderr`) push per-`Run` bindings
- **WASM** → a `HostWriter` / `HostReader` adapter forwards to the JS host

Two rules keep the boundary honest:

1. **Host-bound capabilities live in `pkg/rt`, never `pkg/vm`**: The guest names the capability (`println`, `read-key`, `emit`); the host supplies the backend. The VM core stays host-agnostic.
2. **The seam is as thin as the operation allows**: Output is a byte stream (`io.Writer`); input is a small capability set; no richer interface earns its keep.

## I/O Seams Shipped

The decoupling is complete as of 2026-06-17:

| Step | Seam | State |
|---|---|---|
| print → `*out*` | Print fns consult dynamic binding, not `os.Stdout` | #206 (merged) |
| embedder options | `WithStdout` / `WithStderr` per-`Run` bindings | #207 (merged) |
| ANSI ops → `*out*` | Terminal control ops join the same path | #223 (merged) |
| WASM host writer | `*out*` / `*err*` bound to `HostWriter`; `fs` shim retired | #231 (merged) |
| input seam | `read-key` / `key-pending?` via `KeySource` / `HostReader` | #244 (merged) |
| emit seam | `js/emit` via typed `HostEmitter`, off raw `_lgEmit` | #241 (merged) |

Output, input, and emit now reach the host through one configurable seam per stream. The browser bundle no longer intercepts file descriptors.

## Design Decisions

**Input shape**: `read-key` / `key-pending?` are capability ops backed by a host-supplied `KeySource` (a small interface), not a generic `io.Reader`. Interactive keys are event-shaped (one keystroke = one unit), blocking, and need interruption; `io.Reader` fits them awkwardly. Generic stdin (byte streaming) is a separate, later seam.

**Blocking + wake**: The native runtime interrupts a blocked `read-key` with a self-pipe wake-byte (returns `BEL` on resize). This is explicit in the seam: "a blocked read is interruptible by resize/EOF/stop." Both platforms already solve the interrupt, so codifying it is cheaper than rewriting.

**ANSI plain-vs-color**: Gated at emission (ops consult an `*ansi?*` flag), not stripped downstream. This avoids generating-then-parsing-out escapes. The host can set the flag automatically by checking `isatty` at startup.

**Terminal seam minimalism**: Keep output as an `io.Writer`; input as a small capability set. A rich TUI library like ratatui can sit on top of the writer seam, not replace it.

**Adapters in `pkg/rt`**: Build-tagged JS-aware adapters (`HostWriter`, `HostReader`, emit bridge) stay in `pkg/rt` as thin shims. The seam is the `io.Writer`/`io.Reader` boundary; adapters bridge host-specific code to it.

## Why It Matters

Decoupling I/O enables:

- **One runtime, multiple hosts**: The same bytecode runs natively, in WASM, and on custom hosts without modification.
- **No downstream shims**: Embedders don't maintain `fs.writeSync` patches; the host binds a stream at startup.
- **Composability**: A TUI library, analytics layer, or shell can wrap the writer seam without touching the runtime.
- **Client ownership**: Projects like xsofy can provide their own shells and I/O backends without patches to let-go.

The pattern generalizes: peer capabilities (graphics, audio, input) follow the same shape—guest-named, host-supplied, decoupled.

# Citations

[1] **pkg/rt/iort.go**: I/O routing and `IOHandle`  
https://github.com/nooga/let-go/blob/main/pkg/rt/iort.go

[2] **pkg/api**: Embedder API with `WithStdout` / `WithStderr`  
https://github.com/nooga/let-go/blob/main/pkg/api

[3] **PR #206**: Print and error routing through `*out*` / `*err*`  
https://github.com/nooga/let-go/pull/206

[4] **PR #231**: WASM host writer (`HostWriter`)  
https://github.com/nooga/let-go/pull/231

[5] **PR #244**: Input seam (`KeySource`, `HostReader`)  
https://github.com/nooga/let-go/pull/244

[6] **PR #241**: Emit seam (`HostEmitter`)  
https://github.com/nooga/let-go/pull/241

[7] **nooga/let-go#255**: Peer capabilities (graphics, audio, controller)  
https://github.com/nooga/let-go/issues/255

---

See also: [WASM Compilation](wasm-compilation.md), [Execution Context](exec-context.md), [Stack VM](stack-vm.md)
