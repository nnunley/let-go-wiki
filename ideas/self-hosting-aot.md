---
type: Idea
category: idea
title: "Self-hosting AOT"
description: "Roadmap for let-go compiling itself ahead-of-time to native Go: using the IR pipeline and Go AOT backend to bootstrap a self-hosted runtime."
tags: [compiler, go, bytecode]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/go-aot-backend.md"
sources: ["docs/design/go-aot-backend.md", "docs/master-plan.md"]
created: "2026-07-02"
updated: "2026-07-02"
status: speculative
---

# Self-hosting AOT

**Self-hosting ahead-of-time (AOT) compilation** — let-go compiling itself to native Go — is a strategic goal: eliminating the interpreter's overhead and reducing the runtime to pure Go code. The path is clear: a Go AOT backend compiles bytecode to Go functions; combining that with the [Indexed-RPN IR](../concepts/indexed-rpn-ir.md) and [IR pipeline](../concepts/ir-pipeline.md) enables bootstrapping a self-hosted runtime.

## Vision

1. **Current state**: let-go is an interpreter (`pkg/vm`) that reads bytecode and executes it. Adding a Go backend means compiling bytecode to Go functions instead of executing them.

2. **Bootstrap**: once the Go backend is mature, compile let-go's own runtime (currently written in Go and Clojure in `pkg/rt/core`) to a Go-based version. This eliminates the last dependency on the interpreter loop for core functionality.

3. **Result**: a pure Go runtime with zero interpreter overhead, while maintaining full Clojure semantics and dynamic `eval` capability.

## Architecture: two-tier approach

### Tier 1: Embedding (quick win)
- Compile bytecode to Go *data* (const pools, instruction arrays).
- Register compiled functions as `NativeFn` instances in their `Var`s at `init()`.
- Still uses the interpreter loop for execution.
- **Benefit**: removes image I/O; Go linker can optimize; equivalent to a built-in runtime image.
- **Timeline**: achievable in Phase 7 of the master plan.

### Tier 2: Native lowering (performance)
- Compile let-go functions to actual Go functions that implement the same logic without bytecode.
- Each compiled function has signature `func(env *vm.Env, args []vm.Value) (vm.Value, error)` or smaller fixed-arity wrappers.
- Implement logic via translating bytecode operations to Go control flow and direct runtime calls.
- **Benefit**: massive performance uplift; call overhead eliminated; TCO via loops.
- **Timeline**: follows Tier 1; incremental rollout on hot functions.

## Self-hosting strategy

Once Tier 2 is working for user code, apply it to let-go's own runtime:

1. **Identify hot runtime paths** (e.g., `core/map`, `core/filter`, `core/reduce`, numeric ops).
2. **Compile to Go** using the same backend.
3. **Register compiled functions** as `NativeFn` instances, replacing the old bytecode/interpreter invocations.
4. **Preserve dynamic `eval`** by keeping `Var` indirection: compiled code calls through `Var` pointers, so redefined functions are observed.

**Result**: a runtime that is entirely Go-generated, with no hard-coded Go functions. The bootstrap is complete: let-go's runtime compiled from let-go source.

## Key properties

### Semantics preserved
- Compiled functions use the same `Value` and `Fn` interfaces as the interpreter.
- Interpreted and compiled code interoperate through shared `Var`s.
- Dynamic `eval` continues to compile to bytecode and install into the same `Var`s.
- Var redefinition is observed by compiled code (unless annotated `^:const` or `^:inline` for AOT-only optimization).

### Mixed execution
- Startup: load and execute a stdlib image (or embedding tier) instantly.
- Long-running: hot functions (identified by sampling or heuristics) are compiled to Go on demand or at build time.
- Interop: compiled code calls interpreted functions (e.g., user-defined fns) via `Var`; interpreted code calls compiled builtins normally.

### Build workflow
```bash
# Build let-go with self-hosted AOT runtime
$ lg build --runtime aot --output lg-aot

# Or: compile an app to Go, then build with go build
$ lg build --target go --output myapp/main.go
$ cd myapp && go build -o myapp
```

## Implementation phases (Phase 7 onward)

### Phase 7a: Embedding tier + prototype native lowering
- Compile bytecode to Go data + register in `Var`s.
- Prototype: compile a few small functions (`+`, `inc`, `conj`) to Go by hand.
- Verify: interop with interpreted code; performance gains.
- **Acceptance**: mixed execution works; measurable speedup on call-heavy microbenchmarks.

### Phase 7b: Native lowering at scale
- Codegen for all non-variadic functions (arity 0–3, no closures initially).
- Self-tail recursion elimination (to loops).
- Calls via `Var` indirection (no devirtualization yet).
- Error wrapping with source location.
- **Acceptance**: real programs mixed compiled+interpreted; perf tests pass.

### Phase 7c: Self-hosting bootstrap
- Compile `core/map`, `core/filter`, `core/reduce`, numeric ops to Go.
- Replace bytecode invocations with compiled versions.
- Verify: stdlib tests still pass; startup and throughput improve.
- **Acceptance**: stdlib image optional (embedding tier sufficient); performance targets hit.

### Phase 8 onwards: Optimization and polish
- Closures and variadics.
- Direct-call devirtualization for known-final vars.
- Inline constant/const-vars.
- Source maps and improved error stack traces.

## Relationship to runtime images

- **Runtime images** (Phase 5 of master plan) pre-serialize the stdlib to `.img` format for fast boot.
- **Self-hosting AOT** (Phase 7+) eliminates the interpreter's execution overhead entirely.
- **Together**, they provide: fast startup (image) + fast execution (AOT). Embedding tier provides the former; native lowering tier provides the latter.

## Benefits

1. **Performance**: eliminate interpreter overhead; achieve native-code speed.
2. **Redistribution**: smaller binaries (no bytecode interpreter loop); faster cold-starts.
3. **Transparency**: stack traces and profiling see Go function names directly.
4. **Maintainability**: runtime logic stays in Clojure source; compiler generates the Go code automatically.

## Risks

- **Semantic divergence**: compiled and interpreted paths must stay in sync. Mitigation: single spec; comprehensive property tests; reuse runtime helpers.
- **Compilation complexity**: native lowering is a substantial feature. Mitigation: start with Tier 1 (embedding); prove value before going to Tier 2.
- **Mutual recursion**: self-tail recursion has cheap solution (loops); mutual tail recursion requires trampolines or dynamic indirection. Mitigation: optimize self-recursion first; mutual recursion falls back to `Var` indirection initially.

## Success criteria

- **Mixed execution**: compiled functions call interpreted functions (and vice versa) via shared `Var`s; semantics and errors match.
- **Performance**: call-heavy microbenchmarks show >25% throughput improvement and >50% alloc reduction vs. optimized interpreter.
- **Completeness**: stdlib compiles successfully; all tests pass.

# Citations

[1] **docs/design/go-aot-backend.md**: Go AOT backend design  
https://github.com/nooga/let-go/blob/main/docs/design/go-aot-backend.md

[2] **docs/master-plan.md**: Full master plan, including Phase 7 (Go AOT backend)  
https://github.com/nooga/let-go/blob/main/docs/master-plan.md

[3] **Indexed-RPN IR** (this wiki)  
[../concepts/indexed-rpn-ir.md](../concepts/indexed-rpn-ir.md)

[4] **IR pipeline** (this wiki)  
[../concepts/ir-pipeline.md](../concepts/ir-pipeline.md)

[5] **Bytecode compiler** (this wiki)  
[../concepts/bytecode-compiler.md](../concepts/bytecode-compiler.md)

[6] **let-go** (this wiki)  
[../entities/let-go.md](../entities/let-go.md)

---

See also: [lg-compile](../concepts/lg-compile.md), [bytecode-compiler](../concepts/bytecode-compiler.md), [go-interop](../concepts/go-interop.md)
