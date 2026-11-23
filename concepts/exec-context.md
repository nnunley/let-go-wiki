---
type: Concept
category: concept
title: "Execution Context and Threading"
description: "How the ExecContext carries execution state (scopes and dynamic bindings) through the VM, threaded rather than stored in goroutine-local maps."
tags: [vm, runtime, go, bytecode]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/exec-context-threading.md"
sources: ["design: exec-context-threading.md, 2026-06-10", "repo: nooga/let-go pkg/vm pkg/rt pkg/rt/core/ir cmd/lgbgen docs/design/exec-context-threading.md @ b82588292b, 2026-10-20"]
created: "2026-07-02"
updated: "2026-10-20"
status: active
---

# Execution Context and Threading

The let-go runtime maintains per-execution state: structured concurrency (the scope tree that cancellation walks), dynamic-variable bindings (like `*out*`, `*err*`, `*ns*`), and the current namespace. Before commit `439b6036e` (2026-06-13) this state was looked up through goroutine-ID-keyed maps. At `b82588292b` it is carried by a single `ExecContext` that is passed explicitly: on the interpreter `Frame`, into context-aware native functions, and as the first parameter of lowered Go functions.

## The Problem with Goroutine-ID Keying

The original design had two parallel goroutine-ID-keyed stores (design note: [docs/design/exec-context-threading.md](https://github.com/nooga/let-go/blob/b82588292b/docs/design/exec-context-threading.md) §1):

1. **Scope GLS** (`pkg/vm/scope_gls.go`, `scopeByGID`): carried the cancellation tree and `context.Context` for blocking operations. Neither the file nor the `scopeByGID` symbol exists at `b82588292b`.
2. **Dynamic-variable binding store** (`pkg/vm/binding_frames.go`, `goroutineLocalBindingStore`): carried the stack of bindings for `Var.Deref` and binding pushes. Neither exists at `b82588292b`.

Goroutine IDs had these problems:

- **Goroutine-ID reuse**: when a goroutine exits with a live binding (panic without recover, or a binding meant to outlive it), the frame stays in the map. Go reuses goroutine IDs, so a later goroutine with the same ID reads the dead one's bindings.
- **Cost**: `goID()` parsed a stack trace on every miss, which put it on the fast path.
- **Duplication**: two parallel maps solved the same problem.

Per-goroutine binding isolation is required by `future`, which `pmap` is built on: `pmap` maps each element to a `future` (`pkg/rt/core/core.lg`, the `pmap` definition), and each `future*` runs under its own child context (`pkg/rt/lang.go`, `future*`). The design note also cites `lgbgen`'s concurrent lowering workers as a dependent. At `b82588292b` `cmd/lgbgen/main.go` starts no worker goroutines; its only goroutine is a signal handler. Parallel lowering is not part of this commit.

## The Design: One ExecContext, Explicitly Threaded

The implemented struct (`pkg/vm/exec_context.go`):

```go
type ExecContext struct {
    bindings *bindingStack // dynamic-var stack (not goid-keyed)
    scope    *Scope        // structured concurrency; nil means the root Goroutines scope
}
```

**Frames**: the eval `Frame` carries the context in its `ec` field (`pkg/vm/vm.go`, `Frame` struct). Bytecode calls create the child frame with the caller's `f.ec` (`pkg/vm/vm.go`, the `newFrameForBytecodeCall(target, f.ec)` call sites), so child frames inherit the pointer. A `binding` form pushes onto the carried stack.

**Scopes**: `with-scope` opens a child scope on the same context with `vm.OpenChildEC`, and the close step restores the previous scope (`pkg/vm/exec_context.go`, `OpenChildEC`; `pkg/rt/lang.go`, `scope-open`).

**Spawns**: `go` and `future*` call `ec.Child()`. `Child()` creates a new binding stack seeded from a snapshot of the parent's bindings and copies the parent's scope pointer (`pkg/vm/exec_context.go`, `Child`; `pkg/rt/lang.go`, `go` and `future*`). The child stack is held by the child context, not by a map, so nothing remains after the goroutine exits.

**Root context**: `RootExecContext` is the process default. Its binding stack is the process-global `globalBindingStack`, so code that never creates a context shares the same stack as before (`pkg/vm/exec_context.go`, the `RootExecContext` declaration). The `Var`-level API (`PushBinding`, `PopBinding`, `SnapshotBindings`, `RunWithBindings`) operates on the root context (`pkg/vm/var.go`). The `RunWithBindings` comment calls it the legacy bracketing for spawn sites that have not moved to a child context. At `b82588292b` no non-test caller in `pkg/rt`, `pkg/ir` or `pkg/compiler` uses it.

**Dynamic deref**: the eval loop resolves dynamic vars through the frame's context, `f.ec.deref(v)` (`pkg/vm/vm.go`, the `deref` call sites in the dispatch loop).

**Exception, `pmapv`**: `pmapv` is the one place where workers share a stack. It binds the caller's context with `ec.Bind(fn)` and its workers read the shared stack (`pkg/rt/parallel.go`). Its comment warns that a worker fn which pushes its own dynamic binding would race the shared global stack.

## How Builtins Access the Context

`Fn.Invoke([]Value)` is context-free (`pkg/vm/value.go`, the `Fn` interface). Natives that need the context are registered with a context-aware constructor: `NewCtxNativeFn`, `NewArityNativeFn`, or `NewCheckedCtxNativeFn` (`pkg/vm/native_func.go`). Each stores its function in the `ctxProxy` field. `ExecContext.Invoke` passes the current context to a native that has `ctxProxy` set; a plain `Invoke([]Value)` call runs it against the root context (`pkg/vm/native_func.go`, `NewCheckedCtxNativeFn`; `pkg/vm/exec_context.go`, `Invoke`). Builtins that do not use the context keep their existing constructor and need no change.

The design note proposes a `CtxFn` interface with an `InvokeCtx` method. `b82588292b` does not define it. The `ctxProxy` path above is what exists.

The I/O routing helpers take the context: `WriteToOut(ec, s)`, `WriteToErr(ec, s)`, and `resolveIOHandleVar(ec, name)` (`pkg/rt/iort.go`). PR #206 (commit `d6d0128f2`) introduced these helpers without the `ec` parameter (`WriteToOut(s)`, `WriteToErr(s)`, `resolveIOHandleVar(varName)`), and routed `print`, `pr`, `prn`, and `println` through `*out*` and error sites through `*err*` ([PR #206](https://github.com/nooga/let-go/pull/206)). The `ec` parameter was added by commit `439b6036e` (PR #210, `feat(vm,ir): ExecContext threading`) ([commit 439b6036e](https://github.com/nooga/let-go/commit/439b6036e)). The print builtins pass their context to `WriteToOut` (`pkg/rt/lang.go`, the `print` family). The terminal builtins in `pkg/rt/term.go` do the same. Some callers pass `nil`, which resolves to the root context (`pkg/rt/pods.go`, `pkg/rt/http.go`).

`ExecContext.Bind(fn)` returns a function that routes each call through `ec.Invoke`, so a callback given to context-free code (for example `pmapv`) still resolves dynamic vars against the caller's context. At the root context `Bind` returns `fn` unchanged (`pkg/vm/exec_context.go`, `Bind`).

## Three Surfaces

| Surface | Mechanism | Artifact? |
|---|---|---|
| Interpreter eval loop | `ec` field on the `Frame` | No (VM) |
| Hand-written natives | Context-aware constructors (`NewCtxNativeFn`, `NewArityNativeFn`, `NewCheckedCtxNativeFn`); 121 call lines under `pkg/` (109 `NewCtxNativeFn`, 12 `NewArityNativeFn`, 0 `NewCheckedCtxNativeFn`) in 17 non-test files, of which 106 lines (105 + 1) are in 13 files under `pkg/rt`, excluding comments and definitions, at `b82588292b` (`git grep` over `pkg/*.go`, `:!*_test.go`) | No (VM) |
| Lowered gogen_ir functions | `ec` as the first parameter of emitted functions | **Yes (IR lowering)** |

Lowered code (gogen_ir functions) is native Go. Lowering emits each top-level function as `func name(ec *vm.ExecContext, arg0 …)`, and emits each method with `ec` as its first parameter (`pkg/rt/core/ir/lower_go.lg`). A closure struct stores the `ec` it was created under and passes it to its function literal (same file, the closure-struct comment). When lowered let-go code reads a dynamic var or calls a context-needing builtin, it uses that `ec`.

## Why It Matters

Explicit threading replaces goroutine-local state with call-stack plumbing. At `b82588292b`:

- **No goroutine-ID reuse hazard**: no goroutine-ID lookup remains in non-test `pkg/` code. A case-insensitive search for `goid` matches only `GoIdent` descriptor fields. A child context is not stored in a map, so it cannot outlive its goroutine as a map entry.
- **Performance**: the design note expects a threaded pointer to be cheaper than a `goID()` parse (design note §8). No benchmark result is recorded on this page.
- **Parallel workers**: `future`-based `pmap` gives each task a private child context. `pmapv` shares the caller's stack by design, and its comment says it is for read-only-binding workloads.
- **Determinism of parallel lowering**: the design note lists it as a verification step (design note §7, step 8). `b82588292b` has no parallel lowering code, so this page makes no claim about it.

The design note's migration sequence (§7) is implemented in the following places: the `Frame` field, the context-aware natives, lowered signatures, spawn propagation through `Child()`, and scope folding into the context. The deletion of `scopeByGID` is in `439b6036e`, the last commit that changes that symbol. The design note's status is still `active`.

# Citations

[1] **pkg/vm/exec_context.go**: Execution-context threading and per-goroutine scope
https://github.com/nooga/let-go/blob/b82588292b/pkg/vm/exec_context.go

[2] **pkg/vm/binding_stack.go**: Dynamic-binding stack storage
https://github.com/nooga/let-go/blob/b82588292b/pkg/vm/binding_stack.go

[3] **pkg/rt/iort.go**: I/O routing through `WriteToOut`, `WriteToErr`
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/iort.go

[4] **pkg/vm/value.go**: `Fn.Invoke` calling convention
https://github.com/nooga/let-go/blob/b82588292b/pkg/vm/value.go

[5] **PR #206**: Print and error routing through I/O vars
https://github.com/nooga/let-go/pull/206

[6] **pkg/vm/vm.go**: `Frame.ec`, bytecode-call frame inheritance, and dynamic deref
https://github.com/nooga/let-go/blob/b82588292b/pkg/vm/vm.go

[7] **pkg/rt/lang.go**: `go`, `future*`, and `scope-open` spawn and scope sites
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/lang.go

[8] **pkg/rt/parallel.go**: `pmapv` shared-binding behavior and caveat
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/parallel.go

[9] **pkg/vm/native_func.go**: Context-aware native constructors (`NewCtxNativeFn`, `NewArityNativeFn`, `NewCheckedCtxNativeFn`)
https://github.com/nooga/let-go/blob/b82588292b/pkg/vm/native_func.go

[10] **pkg/rt/core/ir/lower_go.lg**: Emission of the `ec` parameter in lowered functions
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/lower_go.lg

[11] **Commit 439b6036e (PR #210)**: `feat(vm,ir): ExecContext threading`, 2026-06-13
https://github.com/nooga/let-go/commit/439b6036e

[12] **Design note**: docs/design/exec-context-threading.md (status `active`)
https://github.com/nooga/let-go/blob/b82588292b/docs/design/exec-context-threading.md

---

See also: [Stack VM](stack-vm.md), [IO/Host Decoupling](io-host-decoupling.md), [IR Pipeline](ir-pipeline.md)
