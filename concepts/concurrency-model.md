---
type: Concept
category: concept
title: Concurrency & Dynamic Binding Model
description: Goroutine-local dynamic bindings and scoped async supervision for concurrent namespace and binding isolation.
tags: [runtime, lisp, vm]
resource: https://github.com/nooga/let-go/blob/main/pkg/vm/exec_context.go
sources:
  - design: docs/design/exec-context-threading.md (local, 2026-06-13; supersedes earlier goroutine-ID keying)
  - spec: docs/superpowers/specs/2026-06-05-concurrent-namespaces-and-dynamic-bindings-design.md (local, 2026-06-05)
  - spec: docs/superpowers/specs/2026-05-30-scoped-async-supervision-design.md (local, 2026-05-30)
created: "2026-07-02"
updated: "2026-07-02"
status: active
---

## Overview

let-go runs Lisp code on real Go goroutines (`future`, `pmap`, async go-blocks, channel pipes). The **concurrency & dynamic binding model** ensures three guarantees:

1. **Per-namespace thread-safety:** each `Namespace` carries an internal `sync.RWMutex`, preventing data races on concurrent `def`/`require`/resolve across goroutines.
2. **Goroutine-local dynamic bindings:** dynamic vars (like `*ns*`, `*out*`, user-defined) are thread-local, not process-global — so `(binding [*ns* ...] ...)` on one goroutine is invisible to others. Every execution carries an `ExecContext` with its own binding stack; goroutine boundaries propagate it explicitly.
3. **Scoped async supervision:** a `with-scope` resource block spawns child goroutines that inherit the parent's bindings and scope, and can be cancelled independently via a structured concurrency tree.

Together, these resolve two critical concurrency defects (F-1: namespace races, F-4: global `*ns*` mutation) and enable safe, deterministic cleanup of concurrent work.

## Namespace Thread-Safety (Part A)

### The Problem

The `Namespace` type holds four unprotected maps (`registry`, `refers`, `aliases`, `excludes`) that are mutated by `Def`, `LookupOrAdd`, `Refer`, `Alias`, and read by `Lookup`. Under concurrent `pmap`/`future` spawns from different namespaces, reads and writes race without synchronization, causing map corruption or panics.

### The Solution

Each `Namespace` carries an unexported `sync.RWMutex`. The governing invariant is: **never hold one namespace's lock while acquiring another's.** This prevents deadlock because:

- `Lookup` reads other namespaces' registries (for refers/aliases) but *composes* individual read operations without holding a lock across them.
- Accessors (`localVar`, `referFor`, `aliasFor`, `isExcluded`) each acquire their namespace's `RLock`, return copies/pointers, and release.
- Writers (`Def`, `DefStub`, `Refer`, `Alias`, `ImportVar`) each acquire their own `Lock`, modify one map, and release — fast, fits bulk-load.

No lock is held across a multi-namespace hop, so readers see a consistent chain of snapshots; no cycle forms.

### Trade-offs

- **Write-heavy bulk-load fits:** `Lock` is cheap (single map op), not a copy-on-write clone.
- **Hot path (compiled code):** doesn't call `Lookup` — compiled bytecode holds direct `*Var` references, so the runtime rarely consults namespaces.
- **Deadlock-free by design:** only multi-namespace interaction is read-only (following refers/aliases) and never holds a lock across the next acquisition.

## Goroutine-Local Dynamic Bindings (Part B)

### The Problem

The old model was a process-global `Var.bindings` stack guarded by a global `bindingsMu`. A `(binding [*ns* ...] ...)` on goroutine A was *visible to goroutine B*, violating Clojure's thread-local semantics. Also, `NewCompiler` and resolver code mutated the *root* of `*ns*`, clobbering every goroutine's current namespace — F-4.

### The New Model: ExecContext-Threaded Binding Stacks

Instead of goroutine-ID keying (the earlier design), the implementation threads an **`ExecContext`** through every execution: the VM's `Frame`, every builtin call, and every goroutine spawn. The `ExecContext` owns both the dynamic-var binding stack *and* the structured-concurrency scope.

- **Storage:** each `ExecContext` carries a `bindingStack` (an immutable, persistent stack of (var, value) pairs). The stack is owned by the context; no internal lock needed for single-writer access.
- **Hot path (eval loop):** `OP_LOAD_VAR` / `OP_SET_VAR` call `f.ec.deref(v)` where `f` is the `Frame` and `ec` is its `ExecContext`. The deref path: checks `isDynamic.Load()` (an atomic), and if true, walks the binding stack in `ec.bindings`. If no active binding, returns the var's root value. No goroutine-ID lookup, no map indirection.
- **Entry points:** the interpreter loop always has a frame with an `ec`; hand-written builtins receive `ec` via the `InvokeCtx` interface (a small set of context-aware natives); lowered `.lg` functions receive `ec` as a threaded parameter.
- **Context inheritance:** when a frame calls another frame within the same goroutine, the child frame inherits the parent's `ec` pointer. Binding operations (push/pop) mutate the same stack; only goroutine spawn creates a fresh context.

### Conveyance (Scope.Go and Spawn Integration)

When a parent goroutine spawns a child (via `Scope.Go`, the single integration point), the child is handed an `ExecContext` seeded from a snapshot of the parent's:

```
snap := parent.ec.BindingSnapshot()    // parent reads its OWN context (no race)
go func() {
    childEC := NewExecContextFrom(snap) // child gets a fresh context with parent's bindings snapshot
    fn(childEC)                         // run the thunk with explicit context
}()
```

- The parent reads its own context, so there's no race.
- The child receives a fresh `ExecContext` with the parent's bindings snapshotted in — no goroutine-ID parse on spawn.
- Each goroutine's `ExecContext` is stack-local to it (returned to GC when the goroutine exits); no global registry to leak.

### Resolution of F-4

- `NewCompiler` and resolver no longer call `rt.CurrentNS.SetRoot(...)` (global mutation).
- They set the **goroutine-local** `*ns*` binding instead (via `binding [*ns* ...]` macro).
- The constructor side effect is now goroutine-scoped, so it doesn't clobber other goroutines.
- The global root of `*ns*` remains the bootstrap default; conveyance snapshots the parent's binding for scoped spawns.

### Performance

- **Hot path carries no goroutine-ID cost.** The eval loop's `OP_LOAD_VAR`/`OP_SET_VAR` call `f.ec.deref()` which is: `isDynamic.Load()` (atomic), then if true, a binding stack walk. Non-dynamic vars or a nil binding skip to root in the atomic check.
- **No global registry.** Each `ExecContext` is stack-local; the root context is process-global but binding operations on it are serialized by the goroutine that drives the frame.
- **Portability:** no `runtime.Stack` parsing in the hot path. Threading `ec` through the `Frame` is the core idea, and it generalizes to WASM and other runtimes.

## Scoped Async Supervision (Part C)

### The Problem

The VM has a goroutine supervision tree (`Scope`), but blocking async ops (`<!`, `>!`, `alts!`, `sleep`) consult the *global root* context, and all spawns go into the root. Cancelling a sub-scope has no effect on goroutines parked inside it.

### The Solution: with-scope Resource Block

A `with-scope` is a structured-concurrency resource block. Its lifecycle:

```clojure
(with-scope [s]
  (go (println "got" (<! ch))))   ; s is the child scope; parked under s
;; exit: cancel s → parked (<! ch) unblocks; goroutine exits
```

- **Open:** `(scope-open)` creates a child scope of the current scope and installs it on the running `ExecContext` for the dynamic extent.
- **Body:** goroutines spawned inside (via `go*` or `future*`) and blocking ops inside them all read the current scope from the `ExecContext`.
- **Close (finally):** `(scope-close! s timeout-ms)` cancels the scope's context (cascading to the subtree), awaits the goroutines up to `timeout-ms`, logs a warning if stragglers remain, and restores the prior scope. **Bounded teardown:** no hang.

### Explicit Scope Threading (Part of ExecContext)

The `ExecContext` carries the scope; when code needs to know its current scope, it reads it from `ec.Scope()` (which normalizes `nil` to the root `Goroutines` scope). When a goroutine spawns a child, it captures the current scope from its `ExecContext` and hands it to the child's fresh context.

- **No registry lookup.** A goroutine doesn't parse its ID to discover its scope; the `ExecContext` it's executing in already knows it.
- **Two operation paths:** synchronous `with-scope` (same goroutine, same frame, but changing `ec.scope` for the dynamic extent), and asynchronous spawn (child gets a fresh `ExecContext` with the parent's scope copied to it).

### Guarantees

1. **Independence:** goroutines under one sub-scope are cancelled independently; siblings and root keep running.
2. **No orphans:** every scope is owned by exactly one `with-scope` and cleaned up on block exit. No unbounded `children` growth; no leaked context-tree `cancel`.
3. **No hangs:** bounded drain with timeout; stragglers are logged and left running (leak is visible and bounded).

### Rewiring the Ops

| Lisp operation | Change |
|---|---|
| `go*` / `future*` | spawn with `Scope.Go(child_ec)` where `child_ec` carries the parent scope |
| `<!` / `>!` / `alts!` / `sleep` | select on `ec.Context()` (from the `ExecContext`) instead of root context |

The pipeline CSP internals (`async.go`) remain root-wired (no user-facing scope); bulk root drain stays correct.

## Implementation Hook Points

- **ExecContext:** `pkg/vm/exec_context.go` — the unified context carrying bindings + scope; `deref()`, `pushBinding()`, `popBinding()`, threading through spawns.
- **Binding:** `pkg/rt/core/core.lg` — `binding` macro (line ~582), `bound-fn*` macro; operates on the `ExecContext` passed by the eval loop.
- **Scope:**  `pkg/rt/lang.go` — `scope-open` and `scope-close!` native functions; `go*` and `future*` rewired to spawn via `Scope.Go(childEC)`.
- **Frame & eval loop:** `pkg/vm/vm.go` — `Frame.ec *ExecContext` field; `OP_LOAD_VAR` / `OP_SET_VAR` call `f.ec.deref()`.
- **Binding stack:** `pkg/vm/binding_stack.go` — immutable stack data structure, snapshots for conveyance.
- **Scope tree:** `pkg/vm/scope.go` — `Scope`, `Scope.Go()`, `Scope.Context()` for cancellation; wired to `ExecContext.Scope()`.

## Testing Strategy

- **Go race tests:** `-race` flag on namespace concurrent `Def`/`Lookup`, binding isolation (each goroutine sees only its own value), conveyance (child inherits parent, siblings don't leak), and concurrent compile.
- **Lisp conformance:** `pmap`/`future` rebind `*ns*` per worker and assert isolation; `with-scope` / `sleep` / `go*` tests assert cancellation and bounded drain.
- **Performance gate:** `make test-race` target; bench-ratchet regression tests on dynamic-var-heavy benchmarks.

## Citations

- **ExecContext (core impl):** [pkg/vm/exec_context.go](https://github.com/nooga/let-go/blob/main/pkg/vm/exec_context.go) — the unified `ExecContext` struct carrying bindings and scope, threading through execution.
- **Frame & eval loop:** [pkg/vm/vm.go](https://github.com/nooga/let-go/blob/main/pkg/vm/vm.go) (`Frame` struct, `OP_LOAD_VAR` / `OP_SET_VAR` opcodes) — how `ec` is carried through interpretation.
- **Binding macros:** [pkg/rt/core/core.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg) (`binding` macro ~line 582, `bound-fn*`) — the user-facing binding APIs.
- **Design history:** [docs/design/exec-context-threading.md](local, 2026-06-13) — the design decision to replace goroutine-ID keying with explicit `ExecContext` threading. Supersedes the earlier goroutine-local scope registry design.
- **Original specs:** [docs/superpowers/specs/2026-06-05-concurrent-namespaces-and-dynamic-bindings-design.md](local) and [docs/superpowers/specs/2026-05-30-scoped-async-supervision-design.md](local) — the initial design approach using goroutine-ID keying, revised by the exec-context-threading design.
