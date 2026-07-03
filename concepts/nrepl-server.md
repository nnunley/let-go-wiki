---
type: Concept
category: concept
title: "nREPL Server"
description: "A TCP server exposing let-go's compiler and runtime over the nREPL protocol for editor tooling and interactive development."
tags: [tooling, interop, runtime]
resource: "https://github.com/nooga/let-go/blob/main/pkg/nrepl/server.go"
sources: ["/Users/ndn/development/let-go/docs/superpowers/specs/2026-06-14-incremental-lowering-nrepl-server-design.md", "/Users/ndn/development/let-go/docs/superpowers/specs/2026-06-29-browser-inspector-nrepl-bridge-design.md"]
created: "2026-07-03"
updated: "2026-07-03"
status: speculative
---

# nREPL Server

A network REPL server exposing let-go's compiler and runtime via bencode-framed messages over TCP (127.0.0.1 by default). Enables interactive development in editors, the REPL, and tooling without rebuilding let-go itself.

## Core Implementation

The base server in `pkg/nrepl/server.go` implements the nREPL 1.0 protocol. A client starts it via `lg -n -p <port>` or calls `NewNreplServer(ctx).Start(port)` directly from Go.

The server is **single-threaded at the protocol layer** (bencode frames over TCP, one message at a time per connection) but spawns one goroutine per accepted client connection. Each client connection is isolated via a session ID; multiple clients can connect to the same server instance.

### Session Model

Each nREPL session is a lightweight wrapper around a shared `*compiler.Context`:

```go
type session struct {
  id  string                      // UUID
  ctx *compiler.Context
}
```

Sessions are created on-demand (via the `clone` operation) and destroyed explicitly. All sessions in a server share the same namespace state (the same `*rt.Namespace` objects), so `def`s in one session are visible to all others—matching Clojure's process-global namespace architecture.

### Wire Format

Messages are bencode dictionaries, each sent as a byte sequence:

```
d2:id4:abc123:opevaln/a  → {"id": "abc", "op": "eval", ...}
```

Responses are also bencode dictionaries streamed back to the client. The protocol is synchronous: for each request, the server sends one or more response frames (each a separate bencode message) culminating in a `"done"` status.

## Supported Operations

- **`eval`** — Compile and execute Lisp code. Captures output via dynamic-binding interception of `*out*`, returning stdout frames, value/error results, and a final done frame. Code is evaluated against the session's compiler context, so all top-level forms execute with shared defs.
- **`load-file`** — Evaluate a code string (convenience operation; converted to `eval` internally).
- **`clone`** — Create a new session with a fresh UUID. The new session shares the parent's namespace.
- **`close`** — Destroy a session by ID.
- **`describe`** — Advertise supported operations and version info (let-go 1.0, nREPL 1.0).
- **`completions` / `complete`** — Symbol completion via fuzzy namespace lookup.
- **`info` / `lookup`** — Metadata and binding info for a symbol.
- **`ls-sessions`** — List all active session IDs.
- **`interrupt`** — Placeholder; returns `session-idle` (no cancellation implemented yet).

## Output Capture

The `eval` operation captures stdout by binding `*out*` to a per-eval `bytes.Buffer`, executed on the call stack (not OS-level file descriptor swapping). This avoids cross-platform I/O decoupling issues that plagued earlier implementations.

**Concurrency caveat:** The binding stack is process-global, not per-goroutine. Concurrent evals interleave bindings, so stdout from parallel evals can mix. Suitable for interactive single-client loops; not suitable for a multi-client production server without serialization.

## Future Extensions (Design Phase)

### Incremental Lowering

**Status:** design phase (not yet integrated).

**Design goal:** A `--serve` flag in `cmd/lgbgen` would warm-boot the full IR pipeline (Phase-1 compilation of core) once, then keep the compiler context alive and expose it over nREPL. Clients could then re-lower individual namespaces in seconds (vs. the ~76s cold-start cost). Design spec at `/Users/ndn/development/let-go/docs/superpowers/specs/2026-06-14-incremental-lowering-nrepl-server-design.md`. Experimental prototype exists in a development branch; not yet in main.

### Browser Inspector Bridge

**Status:** design only; not yet integrated into `pkg/nrepl/server.go`.

A JSON variant of nREPL for WASM runtimes, streaming structured responses with per-form compilation artifacts (IR, bytecode, lowered Go). See `/Users/ndn/development/let-go/docs/superpowers/specs/2026-06-29-browser-inspector-nrepl-bridge-design.md`.

---

# Citations

[1] [nREPL Server implementation](https://github.com/nooga/let-go/blob/main/pkg/nrepl/server.go) — bencode protocol, session management, operation dispatch.

[2] Incremental lowering design — local spec `/Users/ndn/development/let-go/docs/superpowers/specs/2026-06-14-incremental-lowering-nrepl-server-design.md`.

[3] Browser Inspector nREPL bridge design — local spec `/Users/ndn/development/let-go/docs/superpowers/specs/2026-06-29-browser-inspector-nrepl-bridge-design.md`.
