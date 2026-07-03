---
type: Source
category: source
title: Threading an execution context (off goid)
description: Design for eliminating goroutine-ID keying and unifying Scope + dynamic-var bindings into an explicitly-threaded ExecContext.
tags: [runtime, vm, concept, go]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/exec-context-threading.md"
sources: ["repo: nooga/let-go docs/design/exec-context-threading.md, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

# Threading an execution context (off goid)

This design note, marked active as a gating decision for the dynamic-binding refactor, proposes eliminating goroutine-ID keying by unifying two separate ambient context mechanisms into a single **`ExecContext`** that is explicitly threaded through execution rather than looked up by goroutine ID.

The let-go [runtime](../entities/let-go.md) currently maintains two parallel, goroutine-ID-keyed structures: the Scope GLS (carrying structured concurrency and cancellation context) and the dynamic-var binding store. Both resolve "current" by parsing `runtime.Stack` output to extract the goroutine ID, which creates a hazard: goroutine ID reuse can leak dead bindings into later goroutines, maps grow unbounded, and the ambient lookup duplicates mechanism across two codebases. The design gates the [concurrency-model](../concepts/concurrency-model.md) and binding isolation needed for deterministic parallel lowering.

## Key takeaways

- **Problem:** Two parallel goroutine-ID-keyed mechanisms (Scope GLS and dynamic-var binding store) create the goid footgun, redundancy, and performance cost.

- **Goal:** Eliminate goid by introducing a single `ExecContext` struct carrying both Scope and binding stack, explicitly threaded through execution (via the VM [Frame](../concepts/stack-vm.md)) rather than ambient lookup.

- **Design:** ExecContext lives on the interpreter Frame; child frames inherit the pointer; goroutine spawns capture a snapshot; no map entry is left to forget, no goid reuse hazard.

- **NativeFn convention (bounded dig-in):** Only ~17 builtins + Scope ops need context; add an additive `CtxFn` interface (`InvokeCtx(ec, args)`) with fallback to `Invoke(args)` for pure builtins. Three chokepoints—`WriteToOut`, `WriteToErr`, `resolveIOHandleVar`—consolidate IO-family derefs (the bulk of context-dependent sites).

- **Three surfaces:** interpreter eval loop (threading `ec` on Frame, no IR artifact), hand-written NativeFns (~17, additive convention), and lowered gogen_ir functions (threading `ec` through emitted signatures, an IR-lowering artifact).

- **Migration:** Eight-step sequence starting from clean `main@upstream` (incorporating #206's `WriteToOut` routing by construction), introducing `ExecContext`, wiring `CtxFn`, migrating builtins, threading `ec` through lowered-fn signatures, and finally deleting goid-keyed structures.

- **Determinism preserved:** Concurrency isolation for `pmap`, `parallel`, and lgbgen workers is achieved via per-goroutine binding snapshots, keeping deterministic lowering intact without a global stack.

## Derived pages

[exec-context](../concepts/exec-context.md) · [concurrency-model](../concepts/concurrency-model.md)

# Citations
