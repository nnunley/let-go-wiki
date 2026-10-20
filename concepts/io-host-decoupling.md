---
type: Concept
category: concept
title: "Runtime I/O and Host Decoupling"
description: "How the runtime routes I/O through dynamic-var seams that each host binds, so one runtime runs natively, in WASM, and under Go embedders."
tags: [runtime, wasm, go, interop]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/runtime-io-host-decoupling.md"
sources:
  - "design: runtime-io-host-decoupling.md, 2026-06-18"
  - "repo: nooga/let-go docs/design/runtime-io-host-decoupling.md, pkg/rt (iort.go, keysource.go, keysource_queued.go, keysource_js_wasm.go, hostwriter_js_wasm.go, hostemitter_js_wasm.go, term.go, term_plan9.go, lang.go, wasm/rendermain.go, wasm/lg-host-core.js), pkg/api/api.go, pkg/cli/cli.go, pkg/vm, docs/design/glplat-backend-contract.md @ b82588292b, 2026-10-20"
created: "2026-07-02"
updated: "2026-10-20"
status: stable
---

# Runtime I/O and Host Decoupling

The let-go runtime originally hardcoded I/O to platform-specific sinks: `os.Stdout` on native, `fs.writeSync` shims in WASM. This coupling required each host to maintain its own shims. The design decouples I/O by exposing **seams**: small, typed boundaries where each host binds the concrete stream.

## The Problem: Parallel I/O Paths

There were four distinct paths for "write a string from `.lg` code":

- **native `lg`** → `os.Stdout` → terminal
- **`lg -w` bundle** → `os.Stdout` → `fs.writeSync` shim → `LetGoHost._output` → the page
- **WASM track** (`pkg/api`-based) → `os.Stdout` → `wasm_exec.js` default → DevTools console
- **`lg -b` native** (third-party CLIs) → `os.Stdout` → terminal

Each host inserted itself at a different layer and maintained its own shim. The solution: make the runtime consult dynamic variables for I/O instead of hardcoding sinks.

## The Model: One Contract, Multiple Bindings

The runtime already had the abstraction partially in place: `*in*`, `*out*`, `*err*` are dynamic variables holding an `IOHandle`, which wraps an `io.Writer` and/or `io.Reader` (`pkg/rt/iort.go`). The design finishes it:

- **native** → the handle wraps `os.Stdout` / `os.Stdin` (`pkg/rt/iort.go`)
- **embedder** (Go via `pkg/api`) → constructor options push per-`Run` bindings: `WithStdout` and `WithStderr` for `*out*` / `*err*`, `WithEmit`, and `WithKeySource` (`pkg/api/api.go`). The `WithStdout` doc comment states that the binding stack is process-global, so concurrent `Run` calls on different instances can interleave their pushes and pops.
- **WASM** → the generated bundle main (`pkg/rt/wasm/rendermain.go`) installs `HostWriter` on `*out*` and `*err*` through `rt.InstallHostOutputRoots(rt.NewWriterHandle(...))`. `*test-out*` follows `*out*` in that same call only if the test namespace is already loaded (`pkg/rt/iort.go`, `testOutVar != nil`); the bundle does not bind it directly. It also installs `HostEmitter` on `*emit*` by `SetRoot`. `HostKeySource` is bound on `*keys*` by `pkg/rt/term_wasm.go` (line 45), not by the bundle main. The bundle main drives bytecode directly and does not go through `pkg/api`, so `WithStdout` is not used there.

Two rules keep the boundary honest:

1. **Host-bound capabilities live in `pkg/rt`, never `pkg/vm`**: The guest names the capability (`println`, `read-key`, `emit`); the host supplies the backend. No `pkg/vm` file imports `syscall/js` at `b82588292b`. `pkg/vm` still writes diagnostics directly to `os.Stderr` in some paths (see Open Items).
2. **The seam is as thin as the operation allows**: Output is a byte stream (`io.Writer`). Input is a small capability set: `KeySource` has `ReadKey` and `KeyPending` only, and terminal size stays a separate term op (`pkg/rt/keysource.go`).

## I/O Seams Shipped

The I/O seams merged between 2026-06-10 and 2026-06-17. The input and emit seams merged on 2026-06-17 (#244, #241). The design doc records the I/O half as done and the peer capabilities (#255) as the remaining work (`docs/design/runtime-io-host-decoupling.md` §4, §6).

| Step | Seam | State |
|---|---|---|
| print → `*out*` | `print`, `pr`, `prn`, `println` consult the dynamic binding, not `os.Stdout`; error sites route through `*err*` | #206 (merged) |
| embedder options | `WithStdout` / `WithStderr` per-`Run` bindings | #207 (merged) |
| ANSI ops → `*out*` | `term/*` ANSI output joins the same path | #223 (merged) |
| WASM host writer | `*out*` / `*err*` bound to `HostWriter`; `fs` output shim retired | #231 (merged) |
| input seam | `term/read-key` / `term/key-pending?` via `KeySource`, bound at `*keys*` | #244 (merged) |
| emit seam | `js/emit` via typed `HostEmitter`, off raw `_lgEmit` lookup | #241 (merged) |
| client-owned shell | `lg -w -w-shell none` emits the core only; the client supplies its own shell | #245 (merged) |

Output, input, and emit now reach the host through one configurable seam per stream, and the browser bundle no longer intercepts file descriptors (`pkg/rt/wasm/rendermain.go`). The input work built on primitives already upstream: a non-blocking peek (`key-pending?`, #118), the native wake-a-blocked-`read-key` mechanism (BEL self-pipe on resize, #165), and the browser-interop surface itself (`js/emit` + `LetGoHost`, #174). `-w-shell` defaults to `xterm`; `none` emits the host-agnostic core (`pkg/cli/cli.go`).

## Design Decisions

Each entry states what the source does at `b82588292b`. Entries marked *proposal* are design-doc proposals that the code does not implement.

**Input shape** (decided in #244): `read-key` / `key-pending?` are capability ops backed by a host-supplied `KeySource`, not a generic `io.Reader`. Each `ReadKey` call returns one key value. On WASM, `HostKeySource.ReadKey` coalesces identical queued repeats: it drains every immediately following slot with the same length and bytes and returns that key once, advancing the read index past all of them (`pkg/rt/keysource_js_wasm.go`, "Tier-1 lazy coalesce"). A held key that queued up repeats therefore arrives as one return, not one per keystroke. Interactive keys are event-shaped (one keystroke = one unit), blocking, and need interruption; `io.Reader` fits them awkwardly. Generic stdin (byte streaming) is a separate, later seam, and `*in*` is still an `IOHandle` over `os.Stdin` (`pkg/rt/iort.go`).

**Blocking + wake**: On native, `term.go` writes a BEL byte to a self-pipe from the SIGWINCH handler, and a `read-key` that reads that byte returns `terminalWakeKey` (`"\x07"`) (`pkg/rt/term.go`). The public `KeySource` interface does not expose a wake method. The seam comment says a platform source may surface a wake as `terminalWakeKey`, and that "wake remains an implementation detail" (`pkg/rt/keysource.go`). The design doc proposed making interruptibility by resize, EOF, or stop an explicit part of the seam (§5.3); the code keeps it as an implementation detail. WASM has no wake protocol: the `keysource.go` comment says "WASM still needs a SAB-level wake protocol." The design doc defers that protocol to a later change (§5.3, §7).

**ANSI plain-vs-color** (*proposal*, §5.4–5.5): The design proposes gating color at emission through an `*ansi?*`-style flag, with the host setting it from a tty check at startup. At `b82588292b`, `*ansi?*` is defined with default `true` (`pkg/rt/lang.go`). The only code that reads it is the core test runner's PASS/FAIL labels (`pkg/rt/core/core.lg`). On Plan 9, `term_plan9.go` sets it to `false`. The ANSI-emitting ops do not check the flag, and no code sets it from a tty check. The design doc notes that the ops "don't fully, yet" honor the flag.

**Terminal seam minimalism** (*proposal*, §5.6): Keep output as an `io.Writer` and input as a small capability set. The design doc treats a ratatui-style rendering layer (buffer and diff) as something to build above the writer seam, outside the runtime. No such layer exists in the runtime.

**Adapters in `pkg/rt`** (design doc §5.7): The JS-aware adapters (`HostWriter`, `HostKeySource`, `HostEmitter`) are in `pkg/rt` as files with `//go:build js && wasm`: `hostwriter_js_wasm.go`, `keysource_js_wasm.go`, `hostemitter_js_wasm.go`. The design doc §5.7 records this placement; `HostWriter` was the first of them to land there (#231). The seam is the `io.Writer` / `io.Reader` boundary. The design doc calls the input adapter `HostReader`; the code type is `HostKeySource`.

## Why It Matters

Decoupling I/O enables:

- **One runtime, multiple hosts**: The design's stated goal is that the runtime "knows nothing about *where* it runs" (design doc, glossary). Native, the WASM bundle, and `pkg/api` embedders bind the same seams.
- **No downstream shims**: The WASM output path no longer uses the `fs.writeSync` interception (#231). Embedders bind a stream through options or the `*out*` root.
- **Composability**: A rendering layer can wrap the writer seam without changing the runtime (design doc §5.6, proposal).
- **Client ownership**: `lg -w -w-shell none` (#245) lets a client supply its own shell and bind `window.LetGoHost`, the motivating case being xsofy (nooga/xsofy#22, quoted in the design doc §1).

The pattern generalizes: peer capabilities (graphics, audio, controller input) follow the same shape of guest-named, host-supplied capability. This is not shipped. Peer capabilities are scoped in nooga/let-go#255, which is open. Graphics has experimental code in tree: `pkg/glplat` landed in #744, merged 2026-09-19. Its host-capability seam (binding the backend at a dynamic var and retiring the package-level registry) is still open per `docs/design/glplat-backend-contract.md`. See [glplat graphics](glplat-graphics.md).

## Open Items

These are open at `b82588292b`, from the design doc §7 and the code:

- **Wake API.** The shape of the wake (a method, a sentinel return, or a context) is open. The native wake is a sentinel byte; WASM has no wake protocol.
- **WASM key transport.** `keysource_js_wasm.go` describes an SPSC ring of 8 slots with 16 bytes per key (`keyCapacity = 8`, `keyMaxLen = 16`). When the ring is full, the producer drops the key. The design doc's §7 describes a single slot; the code is a ring.
- **Generic stdin.** `*in*` as an `io.Reader` for byte streaming is a separate seam that is not implemented.
- **VM diagnostics bypass `*err*`.** Some `pkg/vm` diagnostics write to `os.Stderr` directly (`pkg/vm/errors.go`, `pkg/vm/namespace.go`), because `pkg/vm` cannot import `pkg/rt`. In WASM these land on the browser console and not in the `*err*` stream (design doc §7).
- **Bundle install path.** The WASM bundle installs roots directly, so `WithStdout` does not reach bundle output. Reconciling the two is a later cleanup (design doc §5.1).
- **Peer capabilities.** Audio, graphics, and controller input are open in nooga/let-go#255.

# Citations

[1] **pkg/rt/iort.go**: I/O routing and `IOHandle`  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/iort.go

[2] **pkg/api**: Embedder API with `WithStdout` / `WithStderr` / `WithEmit` / `WithKeySource`  
https://github.com/nooga/let-go/blob/b82588292b/pkg/api/api.go

[3] **PR #206**: Print and error routing through `*out*` / `*err*`  
https://github.com/nooga/let-go/pull/206

[4] **PR #231**: WASM host writer (`HostWriter`)  
https://github.com/nooga/let-go/pull/231

[5] **PR #244**: Input seam (`KeySource`, `HostKeySource`)  
https://github.com/nooga/let-go/pull/244

[6] **PR #241**: Emit seam (`HostEmitter`)  
https://github.com/nooga/let-go/pull/241

[7] **nooga/let-go#255**: Host capabilities: generalizing the I/O decoupling to e.g. audio and graphics (open)  
https://github.com/nooga/let-go/issues/255

[8] **PR #245**: Client-owned shell (`lg -w -w-shell none`)  
https://github.com/nooga/let-go/pull/245

[9] **PR #223**: Route `term/*` ANSI output through `*out*`  
https://github.com/nooga/let-go/pull/223

[10] **PR #207**: `WithStdout` / `WithStderr` embedder options  
https://github.com/nooga/let-go/pull/207

[11] **PR #165**: Wake `read-key` on SIGWINCH via BEL self-pipe  
https://github.com/nooga/let-go/pull/165

[12] **Design doc**: `docs/design/runtime-io-host-decoupling.md` @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/docs/design/runtime-io-host-decoupling.md

[13] **PR #744**: glplat Ebitengine backend, merged 2026-09-19; registry and backend contract in `docs/design/glplat-backend-contract.md`  
https://github.com/nooga/let-go/pull/744

---

See also: [WASM Compilation](wasm-compilation.md), [Execution Context](exec-context.md), [Stack VM](stack-vm.md)
