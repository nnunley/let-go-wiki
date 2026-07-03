---
type: Concept
category: concept
title: "Execution Context and Threading"
description: "How the ExecContext carries execution state (scopes and dynamic bindings) through the VM, threaded rather than stored in goroutine-local maps."
tags: [vm, runtime, go, bytecode]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/exec-context-threading.md"
sources: ["design: exec-context-threading.md, 2026-06-10"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# Execution Context and Threading

The let-go runtime maintains per-execution state: structured concurrency (cancellation trees), dynamic-variable bindings (like `*out*`, `*err*`, `*ns*`), and the current namespace. Historically, this state was stored in goroutine-ID-keyed maps. This design moves to an **explicitly-threaded `ExecContext`** carried through the call stack, eliminating goroutine-ID lookups and fixing goid reuse hazards.

## The Problem with Goroutine-ID Keying

The original design had two parallel goroutine-ID-keyed stores:

1. **Scope GLS** (`pkg/vm/scope_gls.go`): carries the cancellation tree and `context.Context` for blocking operations.
2. **Dynamic-variable binding store** (`pkg/vm/binding_frames.go`): carries the stack of bindings for `Var.Deref` and binding pushes.

Goroutine IDs have inherent problems:

- **The goid footgun**: When a goroutine exits with a live binding (panic without recover, or a binding meant to outlive it), the frame leaks. Go reuses goids, so a later goroutine on that ID sees the dead one's state, causing silent corruption.
- **Cost**: `goID()` parses a stack trace on every miss—expensive on the fast path.
- **Duplication**: Two parallel maps solve the same problem twice.

Per-goroutine binding isolation is **load-bearing**: `pmap` (parallel map) and lgbgen's concurrent lowering workers each bind registries and type caches via dynamic bindings. Without per-goroutine isolation, parallel workers corrupt each other's registries, causing nondeterministic lowering.

## The Design: One ExecContext, Explicitly Threaded

Replace the two goid-keyed maps with a single `ExecContext` that carries both concerns:

```go
type ExecContext struct {
    scope    *Scope           // structured concurrency + cancellation tree
    bindings *bindingStack    // dynamic-variable stack (not goid-keyed)
}
```

**Threading**: The `ExecContext` lives on the VM eval `Frame` (already threaded through the interpreter loop). Child frames inherit the pointer. When a new dynamic extent occurs (a `binding` form, `with-scope`), it pushes onto the carried stacks. Goroutine spawns capture a snapshot and seed the child frame's `ExecContext`; the child's context dies with the goroutine—no map entry to forget, no goid reuse hazard, no leak.

## How Builtins Access the Context

`Fn.Invoke([]Value)` is context-free. Only ~17 builtins (plus scope ops) need context; hundreds are pure. So the migration is **additive**:

```go
type CtxFn interface { 
    InvokeCtx(ec *ExecContext, args []Value) (Value, error) 
}
```

- The VM calls `InvokeCtx(currentEC, args)` when the function implements `CtxFn`, else falls back to `Invoke(args)`.
- Pure builtins need **zero changes**.

The consolidation already in place (PR #206) groups I/O operations behind three chokepoints: `WriteToOut(ec, s)`, `WriteToErr(ec, s)`, and `resolveIOHandleVar(ec, name)`. This shrinks the dig-in significantly: only the ~5 print builtins need to forward `ec`, not scattered across 17 sites.

## Three Surfaces

| Surface | Mechanism | Artifact? |
|---|---|---|
| Interpreter eval loop | `ec` on the `Frame` | No (VM) |
| Hand-written NativeFns (~17) | `InvokeCtx` convention | No (VM) |
| Lowered gogen_ir functions | `ec` threaded through emitted signatures | **Yes (IR lowering)** |

Lowered code (gogen_ir functions) is native Go. When lowered let-go code reads a dynamic var or calls a context-needing builtin, it too needs `ec`. The lowering must thread `ec` through lowered function signatures: `func f(ec *vm.ExecContext, ...)` emitted by `lower_go.lg`, forwarded at call sites.

## Why It Matters

Explicit threading replaces goroutine-local state with call-stack plumbing. This:

- **Eliminates goid reuse hazards**: No leaked frames, no corruption from ID reuse.
- **Improves performance**: A threaded pointer is cheaper than a `goID()` parse.
- **Enables correctness**: Parallel workers (lowering, pmap) work without global state corruption.
- **Enables determinism**: The type cache for parallel lowering relies on context isolation.

The change is mechanical for most code (pure builtins see no change), and the blast radius is proportional to the actual set of context-dependent operations, not the whole function surface.

# Citations

[1] **pkg/vm/exec_context.go**: Execution-context threading and per-goroutine scope  
https://github.com/nooga/let-go/blob/main/pkg/vm/exec_context.go

[2] **pkg/vm/binding_stack.go**: Dynamic-binding stack storage  
https://github.com/nooga/let-go/blob/main/pkg/vm/binding_stack.go

[3] **pkg/rt/iort.go**: I/O routing through `WriteToOut`, `WriteToErr`  
https://github.com/nooga/let-go/blob/main/pkg/rt/iort.go

[4] **pkg/vm/value.go**: `Fn.Invoke` calling convention  
https://github.com/nooga/let-go/blob/main/pkg/vm/value.go

[5] **PR #206**: Print and error routing through I/O vars  
https://github.com/nooga/let-go/pull/206

---

See also: [Stack VM](stack-vm.md), [IO/Host Decoupling](io-host-decoupling.md), [IR Pipeline](ir-pipeline.md)
