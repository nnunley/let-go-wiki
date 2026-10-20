---
type: Concept
category: concept
title: Concurrency & Dynamic Binding Model
description: Goroutine-local dynamic bindings and scoped async supervision for concurrent namespace and binding isolation.
tags: [runtime, lisp, vm]
resource: https://github.com/nooga/let-go/blob/main/pkg/vm/exec_context.go
sources:
  - "design: docs/design/exec-context-threading.md (nooga/let-go @ b82588292b, 2026-10-19; design note, last-verified 2026-06-10 in its frontmatter; supersedes earlier goroutine-ID keying)"
  - spec: docs/superpowers/specs/2026-06-05-concurrent-namespaces-and-dynamic-bindings-design.md (local, 2026-06-05; not in the upstream tree at b82588292b)
  - spec: docs/superpowers/specs/2026-05-30-scoped-async-supervision-design.md (local, 2026-05-30; not in the upstream tree at b82588292b)
  - repo: nooga/let-go pkg/vm/exec_context.go, pkg/vm/binding_stack.go, pkg/vm/root_bindings.go, pkg/vm/var.go, pkg/vm/native_func.go, pkg/vm/vm.go @ b82588292b, 2026-10-19
  - repo: nooga/let-go pkg/vm/scope.go, pkg/vm/cancelled.go, pkg/vm/exception_class.go @ b82588292b, 2026-10-19
  - repo: nooga/let-go pkg/vm/namespace.go @ b82588292b, 2026-10-19
  - repo: nooga/let-go pkg/rt/lang.go (go*, scope-open, scope-cancelled?, sleep, <!, >!, scope-close!, bound-fn*) @ b82588292b, 2026-10-19
  - repo: nooga/let-go pkg/rt/async.go (alts!) @ b82588292b, 2026-10-19
  - repo: nooga/let-go pkg/rt/exceptions.go (catch-matches?, Cancelled) @ b82588292b, 2026-10-19
  - repo: nooga/let-go pkg/rt/golower_runtime.go (EC helpers) @ b82588292b, 2026-10-19
  - repo: nooga/let-go pkg/rt/core/core.lg (binding, with-scope, *scope-drain-timeout-ms*) @ b82588292b, 2026-10-19
  - repo: nooga/let-go pkg/compiler/compiler.go (NewCompiler, SetCurrentNS) @ b82588292b, 2026-10-19
  - repo: nooga/let-go Makefile (test, bench-ratchet) @ b82588292b, 2026-10-19
  - "guide: nooga/let-go docs/guide/structured-concurrency.md @ b82588292b, 2026-10-19 (last-verified 2026-09-19 in its frontmatter; its cancellation examples predate #924 and were not re-run)"
  - "commit: nooga/let-go 4b9b1588e (#924; issue #920), cancellation surfaced as the Cancelled condition"
created: "2026-07-02"
updated: "2026-10-19"
status: active
---

## Overview

let-go runs Lisp code on real Go goroutines (`future`, `pmap`, async go-blocks, channel pipes). The **concurrency & dynamic binding model** ensures three guarantees:

1. **Per-namespace thread-safety:** each `Namespace` carries an internal `sync.RWMutex`, preventing data races on concurrent `def`/`require`/resolve across goroutines.
2. **Goroutine-local dynamic bindings:** dynamic vars (like `*ns*`, `*out*`, user-defined) are isolated per execution, not process-global. Every execution runs under an `ExecContext`. A child context owns its own binding stack. A spawned goroutine gets a child `ExecContext` seeded from a snapshot of its parent's bindings, so a `(binding [*ns* ...] ...)` on one goroutine is not seen by goroutines that do not inherit it. The root context has no stack of its own: root bindings are kept per Var (`v.rootBind`), and host-level `Var.Deref` reads them through `derefRoot`.
3. **Scoped async supervision:** a `with-scope` resource block opens a child scope. `go` blocks and futures spawned inside it run under that scope and can be cancelled independently through a structured concurrency tree. Cancellation is observable: blocking operations raise a `Cancelled` condition.

Part A addresses F-1 (namespace races). Part B addresses F-4 (global `*ns*` mutation) for dynamic bindings. The compiler's own `*ns*` root assignment is not yet moved onto the execution context at this commit; see Part B.

## Namespace Thread-Safety (Part A)

### The Problem

The `Namespace` type holds four unprotected maps (`registry`, `refers`, `aliases`, `excludes`) that are mutated by `Def`, `LookupOrAdd`, `Refer`, `Alias`, and read by `Lookup`. Under concurrent `pmap`/`future` spawns from different namespaces, reads and writes race without synchronization, causing map corruption or panics.

### The Solution

Each `Namespace` carries an unexported `sync.RWMutex` (`mu`, pkg/vm/namespace.go) that guards its maps: `registry`, `refers`, `aliases`, `excludes`, and `unmapped`. The governing invariant is written in the struct comment: **never hold one namespace's lock while acquiring another's.** This prevents deadlock because:

- `Lookup` reads other namespaces' registries (for refers/aliases) but *composes* individual read operations without holding a lock across them.
- Accessors (`localVar`, `referFor`, `aliasFor`, `isExcluded`) each acquire their namespace's `RLock`, return copies/pointers, and release.
- Writers (`Def`, `DefStub`, `Refer`, `Alias`, `ImportVar`) each acquire their own `Lock`, modify one map, and release — fast, fits bulk-load. `Refer` with `:all` snapshots the target's public vars before it takes its own lock, so it never holds two namespace locks at once.

No lock is held across a multi-namespace hop, so readers see a consistent chain of snapshots; no cycle forms.

### Trade-offs

- **Write-heavy bulk-load fits:** `Lock` is cheap (single map op), not a copy-on-write clone.
- **Hot path (compiled code):** doesn't call `Lookup` — compiled bytecode holds direct `*Var` references, so the runtime rarely consults namespaces.
- **Deadlock-free by design:** only multi-namespace interaction is read-only (following refers/aliases) and never holds a lock across the next acquisition.

## Goroutine-Local Dynamic Bindings (Part B)

### The Problem

The old model was a process-global `Var.bindings` stack guarded by a global `bindingsMu`. A `(binding [*ns* ...] ...)` on goroutine A was *visible to goroutine B*, violating Clojure's thread-local semantics. Also, `NewCompiler` and resolver code mutated the *root* of `*ns*`, clobbering every goroutine's current namespace — F-4.

### The New Model: ExecContext-Threaded Binding Stacks

Instead of goroutine-ID keying (the earlier design), the implementation threads an **`ExecContext`** through every execution: the VM's `Frame`, every builtin call, and every goroutine spawn. The `ExecContext` owns both the dynamic-var binding stack *and* the structured-concurrency scope (pkg/vm/exec_context.go). It holds a `bindings *bindingStack` and a `scope *Scope`; a nil scope means the root `Goroutines` scope.

- **Storage:** `bindingStack` (pkg/vm/binding_stack.go) is a persistent chain of immutable (var, value) frames behind an atomic head. Writers (`push`, `pop`, `setCurrent`, `installSnapshot`) serialize on a mutex and atomically swap the head, so a reader walks the chain without locking. Frames are never mutated after publication.
- **Root context:** `RootExecContext` is the process default. It has no binding stack of its own. `pushBinding`, `popBinding`, `hasBinding`, and `setBinding` route root operations to `rootPush`, `rootPop`, `rootHasBinding`, and `rootSetCurrent` (pkg/vm/exec_context.go). Root bindings are a per-Var chain (`v.rootBind`, serialized on `v.mu`; pkg/vm/root_bindings.go). Reads go through `rootDerefHead` and `derefRoot` (pkg/vm/var.go). A mutex-guarded registry (pkg/vm/root_bindings.go) records which Vars have a live root binding, written only on bind and unbind transitions, so a snapshot can enumerate them.
- **Hot path (eval loop):** `OP_LOAD_VAR` calls `f.ec.deref(v)` (pkg/vm/vm.go). For a child context, `deref` checks `isDynamic` (an atomic) and, if set, walks that context's own stack; otherwise it returns `v.Root()`. For the root context, `deref` calls `v.derefRoot()` (pkg/vm/var.go). There is no goroutine-ID lookup and no map indirection.
- **`set!`:** `OP_SET_VAR` calls `f.ec.setBinding(v, val)`. When the context has no active binding for the var, the opcode falls back to `v.SetRoot(val)`. This is a deliberate leniency: Clojure would throw here (pkg/vm/vm.go, `OP_SET_VAR`).
- **Entry points:** `ExecContext.Invoke` dispatches on the callee's type (closures, `Func`, `MultiArityFn`, and so on) and passes the context down. Context-aware natives are built with `NewCtxNativeFn(name, func(ec *ExecContext, args []Value))` (pkg/vm/native_func.go). Lowered code receives the context through helpers such as `CachedVarFnEC` and `InvokeValueEC` (pkg/rt/golower_runtime.go).
- **Context inheritance:** when a frame calls another bytecode function in the same goroutine, the child frame shares the parent's `ec` (`newFrameForBytecodeCall`, pkg/vm/vm.go). Binding operations push and pop on the same stack. Only a goroutine spawn creates a new context.

### Conveyance (go* and Scope Integration)

A spawn creates a child context with `ec.Child()` and runs the block in the caller's scope with `ec.Scope().Go(...)` (`go*`, pkg/rt/lang.go):

```go
childEc := ec.Child()            // fresh stack seeded from a snapshot of ec's bindings; scope copied from ec
ec.Scope().Go(func(ctx context.Context) {
    v, err := childEc.Invoke(at, nil)
    // ...
})
```

- `Child()` installs a snapshot of the parent's bindings on a new, private stack and copies the parent's scope. A nil or root receiver seeds from the root snapshot.
- `Scope.Go(fn func(ctx context.Context))` takes no `ExecContext`. It does liveness accounting and runs `fn` with the scope's current context. The child's binding and scope state travel in the `childEc` that the caller captured.
- Each child context is owned by its goroutine and is garbage-collected when the goroutine exits. There is no global registry to leak.
- `future*` follows the same pattern (pkg/rt/lang.go).

`NewExecContextFrom(snap)` remains as a general constructor for a context that starts from exactly one snapshot. The spawn path does not use it.

### bound-fn*

`bound-fn*` (pkg/rt/lang.go) captures the caller's bindings at creation. Each call runs in `callEc.Child()`, with the captured bindings pushed on top. A var that was not captured keeps tracking the caller's live binding, rather than falling back to root. The child also carries the invoking execution's scope.

### Resolution of F-4

- **Bindings:** `binding`, `bound-fn*`, and spawns resolve dynamic vars through the `ExecContext`. A binding made after a spawn is not seen by that child, and a child's own bindings are not seen by its parent.
- **Compiler and `*ns*` root:** this half is not in place at b82588292b. `NewCompiler` still calls `rt.CurrentNS.SetRoot(ns)` (pkg/compiler/compiler.go:86), and `Context.SetCurrentNS` does the same (pkg/compiler/compiler.go:197). `rt.CurrentNS.Deref()`, used by `Context.CurrentNS()`, resolves through the process-root context. A goroutine with no `*ns*` binding of its own therefore sees the root that a compiler constructed on another goroutine has just changed. F-4 is open for the compiler path at this commit.

### Performance

- **Hot path carries no goroutine-ID cost.** The eval loop's `OP_LOAD_VAR` calls `f.ec.deref()`, which is an atomic `isDynamic` check and, when set, a walk of the context's binding chain. A var with no active binding falls through to its root.
- **No goroutine-ID registry.** Each child `ExecContext` is stack-local. The root context's bindings are recorded in a single mutex-guarded registry (pkg/vm/root_bindings.go), which is touched only on binding transitions and never on the deref path.
- **Portability:** no `runtime.Stack` parsing in the hot path. Threading `ec` through the `Frame` is the core idea, and it generalizes to WASM and other runtimes.

## Scoped Async Supervision (Part C)

### The Problem

The VM has a goroutine supervision tree (`Scope`), but blocking async ops (`<!`, `>!`, `alts!`, `sleep`) consult the *global root* context, and all spawns go into the root. Cancelling a sub-scope has no effect on goroutines parked inside it.

### The Solution: with-scope Resource Block

A `with-scope` is a structured-concurrency resource block. The `with-scope` macro (pkg/rt/core/core.lg, line 2825) expands to `scope-open`, a `try`, and a `finally` that calls `scope-close!` with `*scope-drain-timeout-ms*` (a dynamic var, default `5000`). Its lifecycle:

```clojure
(with-scope [s]
  (go (println "got" (<! ch))))   ; s is the child scope; parked under s
;; exit: cancel s → parked (<! ch) unblocks and raises Cancelled; goroutine exits
```

- **Open:** `(scope-open)` (pkg/rt/lang.go) calls `vm.OpenChildEC(ec)`. That creates a child of the current execution's scope and installs it on the running `ExecContext` for the dynamic extent.
- **Body:** goroutines spawned inside (via `go*` or `future*`) and blocking ops inside them all read the current scope from the `ExecContext`.
- **Close (finally):** `(scope-close! s timeout-ms)` calls `vm.CloseScoped` (pkg/vm/scope.go). That cancels the scope's context (cascading to the subtree), awaits the goroutines up to `timeout-ms`, writes `warning: with-scope drain timed out; N goroutine(s) still live` to stderr if stragglers remain, restores the prior scope, and unparents the child. **Bounded teardown:** no hang. Stragglers are left running.

### Cancellation Is a Condition

When a scope is cancelled, a blocking native does not return `nil` silently. It raises the scope-cancellation condition through its error slot:

- `sleep`, `<!`, and `>!` return `vm.NewThrownError(vm.NewCancelled(ctx.Err()))` once their scope's context is done (pkg/rt/lang.go: `sleep` at line 4630; `>!` and `<!` at lines 2780, 2795, and 2815). The `ctx.Err()` cause is kept on the condition.
- `alts!` is the exception in the current source. Its cancel arm returns `nil` (no port chosen) and does not raise `Cancelled` (pkg/rt/async.go, `alts!`).
- `Cancelled` is the class `vm.ClassCancelled`, a leaf under `Throwable` (pkg/vm/exception_class.go). Lisp code cannot construct one: `Cancelled` is defined in the namespace without a constructor (pkg/rt/exceptions.go), and the runtime, through `vm.NewCancelled` (pkg/vm/cancelled.go), is the only source of the value.
- `catch-matches?` (pkg/rt/exceptions.go) does not match it for `Throwable` or `Exception`. A worker loop with `(catch Throwable e ...)` cannot swallow its own termination. Only `(catch Cancelled e ...)`, which names the class explicitly, catches it.
- `go*` absorbs the condition silently. Other errors from a `go` block still route to `*err*` (pkg/rt/lang.go, `go*`).
- `(scope-cancelled?)` (pkg/rt/lang.go) returns `true` once the current scope, or a scope passed as an argument, is cancelled. A loop that exits on a count or a time, and does not sleep or park on a cancellable op, can use it to stop.

### Explicit Scope Threading (Part of ExecContext)

The `ExecContext` carries the scope; when code needs to know its current scope, it reads it from `ec.Scope()` (which normalizes `nil` to the root `Goroutines` scope). When a goroutine spawns a child, it calls `ec.Child()`, which copies the current scope into the child's fresh context.

- **No registry lookup.** A goroutine doesn't parse its ID to discover its scope; the `ExecContext` it's executing in already knows it.
- **Two operation paths:** synchronous `with-scope` (same goroutine, same frame, but changing `ec.scope` for the dynamic extent), and asynchronous spawn (child gets a fresh `ExecContext` with the parent's scope copied to it).

### Guarantees

1. **Independence:** goroutines under one sub-scope are cancelled independently; siblings and root keep running.
2. **No orphans:** every scope is owned by exactly one `with-scope` and cleaned up on block exit. No unbounded `children` growth; no leaked context-tree `cancel`.
3. **No hangs:** bounded drain with timeout; stragglers are logged to stderr and left running (leak is visible and bounded).
4. **Cancellation is visible:** a blocking native that is interrupted by its scope raises `Cancelled`, so a caller can distinguish teardown from a legitimate `nil` result. `alts!` is the exception: it returns `nil` on cancel.

### Rewiring the Ops

| Lisp operation | Change |
|---|---|
| `go*` / `future*` | spawn with `ec.Scope().Go(...)` on a child context from `ec.Child()`, which carries the parent scope |
| `<!` / `>!` / `sleep` | select on `ec.Context()` (from the `ExecContext`) instead of root context; raise `Cancelled` on cancel |
| `alts!` | select on `ec.Context()`; return `nil` on cancel (pkg/rt/async.go) |

The pipeline CSP helpers (`pipe`, `map`, `reduce`, `split`, `pub`, `timeout`) still spawn into the root scope regardless of the caller. The user guide lists this as a known gap (docs/guide/structured-concurrency.md, "Known gaps"). Bulk root drain stays correct.

## Implementation Hook Points

- **ExecContext:** `pkg/vm/exec_context.go` — the unified context carrying bindings + scope; `deref()`, `setBinding()`, `pushBinding()`, `popBinding()`, `Child()`, `Invoke()`, `Bind()`.
- **Binding:** `pkg/rt/core/core.lg` — `binding` macro (line 649) and `bound-fn*` macro (line 668); the `bound-fn*` native is in `pkg/rt/lang.go`.
- **Scope:** `pkg/rt/lang.go` — `scope-open`, `scope-cancelled?`, and `scope-close!` native functions; `go*` and `future*` rewired to spawn via `ec.Scope().Go(...)`. `pkg/rt/core/core.lg` — `with-scope` macro (line 2825) and `*scope-drain-timeout-ms*`.
- **Frame & eval loop:** `pkg/vm/vm.go` — `Frame.ec *ExecContext` field; `OP_LOAD_VAR` calls `f.ec.deref()`; `OP_SET_VAR` calls `f.ec.setBinding()`.
- **Binding stack:** `pkg/vm/binding_stack.go` — persistent stack with an atomic head, with snapshots for conveyance; `pkg/vm/root_bindings.go` — root-context binding registry.
- **Scope tree:** `pkg/vm/scope.go` — `Scope`, `Scope.Go()`, `Scope.Context()` for cancellation, `CloseScoped()`, and the drain methods (`Await`, `Shutdown`, `Drain`); `pkg/vm/cancelled.go` — `NewCancelled`, `IsCancelled`.
- **Namespace locks:** `pkg/vm/namespace.go` — `mu sync.RWMutex` and the writer and reader accessors.

## Testing Strategy

- **Go tests:** `pkg/vm/exec_context_isolation_test.go` (child isolation, concurrent isolation, snapshot seeding); `pkg/vm/namespace_race_test.go` (`TestNamespaceConcurrentAccess`); `pkg/vm/scope_test.go` (live and await, drain reinstalls the context, subtree cancel leaves siblings running, parent cancel cascades).
- **Race detector:** there is no `make test-race` target at b82588292b. The `test` target's `GO-TEST-FLAGS` carries only `-timeout` (Makefile), so `-race` is not passed by default. Race runs are a manual `go test -race` on the packages above.
- **Lisp conformance:** `pmap`/`future` rebind `*ns*` per worker and assert isolation; `with-scope` / `sleep` / `go*` tests assert cancellation and bounded drain.
- **Performance gate:** `make bench-ratchet` (Makefile:406-407) depends on `lowered` and runs `go run ./cmd/bench-ratchet check` against the stored baseline. The default gate runs the jank suite under both VM variants (bytecode and gogen_ir-lowered) plus a calibration anchor (Makefile:404-405). Nothing in `cmd/bench-ratchet` at b82588292b references dynamic vars or binding, so this page does not claim the gate targets dynamic-var workloads.

## Citations

- **ExecContext (core impl):** [pkg/vm/exec_context.go](https://github.com/nooga/let-go/blob/main/pkg/vm/exec_context.go) — the unified `ExecContext` struct carrying bindings and scope, threading through execution.
- **Binding stack:** [pkg/vm/binding_stack.go](https://github.com/nooga/let-go/blob/main/pkg/vm/binding_stack.go) — persistent, atomically-headed chain of binding frames; [pkg/vm/root_bindings.go](https://github.com/nooga/let-go/blob/main/pkg/vm/root_bindings.go) — root-context registry.
- **Scope tree and cancellation condition:** [pkg/vm/scope.go](https://github.com/nooga/let-go/blob/main/pkg/vm/scope.go) and `pkg/vm/cancelled.go`; cancellation was surfaced as a condition in [nooga/let-go#924](https://github.com/nooga/let-go/pull/924) (issue [#920](https://github.com/nooga/let-go/issues/920)).
- **Frame & eval loop:** [pkg/vm/vm.go](https://github.com/nooga/let-go/blob/main/pkg/vm/vm.go) (`Frame` struct, `OP_LOAD_VAR` / `OP_SET_VAR` opcodes) — how `ec` is carried through interpretation.
- **Namespace locks:** [pkg/vm/namespace.go](https://github.com/nooga/let-go/blob/main/pkg/vm/namespace.go) — the `mu` field and the lock invariant.
- **Spawns, scope operations and `bound-fn*`:** [pkg/rt/lang.go](https://github.com/nooga/let-go/blob/main/pkg/rt/lang.go) (`go*`, `scope-open`, `scope-cancelled?`, `sleep`, `scope-close!`, `bound-fn*`).
- **Binding macros:** [pkg/rt/core/core.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg) (`binding` macro, line 649; `with-scope` macro, line 2825) — the user-facing binding and scope APIs.
- **Compiler `*ns*` root assignment:** [pkg/compiler/compiler.go](https://github.com/nooga/let-go/blob/main/pkg/compiler/compiler.go) (`NewCompiler`, `SetCurrentNS`) — still sets the root `*ns*`.
- **User guide:** `docs/guide/structured-concurrency.md` — scope lifecycle, drain timeout, and known gaps. Its cancellation examples predate #924 and show a `nil` return that the current source no longer produces for `<!`, `>!`, and `sleep`.
- **Design history:** [docs/design/exec-context-threading.md](https://github.com/nooga/let-go/blob/main/docs/design/exec-context-threading.md) — the design decision to replace goroutine-ID keying with explicit `ExecContext` threading. Supersedes the earlier goroutine-local scope registry design.
- **Original specs:** `docs/superpowers/specs/2026-06-05-concurrent-namespaces-and-dynamic-bindings-design.md` and `docs/superpowers/specs/2026-05-30-scoped-async-supervision-design.md` (local; not in the upstream tree at b82588292b) — the initial design approach using goroutine-ID keying, revised by the exec-context-threading design.
