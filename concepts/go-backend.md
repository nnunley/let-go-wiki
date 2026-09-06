---
type: Concept
category: concept
title: "Go Backend"
description: "The shipped Go backend as distinct from its design proposal: how ir.lower-go emits Go through the gogen layer, what makes a function direct-callable, the entry frame that turns a program into a standalone native binary, the runtime-only lg-runtime, and the gates and open defects around it."
tags: [compiler, go, runtime, tooling]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg"
sources:
  - "repo: nooga/let-go pkg/rt/core/ir/lower_go.lg, pkg/rt/core/ir/passes/{pipeline,entry_frame}.lg, pkg/rt/gogen/gogen.lg, scripts/lg-compile, cmd/lg-runtime/main.go, examples/aot/README.md, Makefile @ 0911118, 2026-09-05"
  - "doc: nooga/let-go docs/design/go-aot-backend.md (last-verified 2026-06-05) @ 0911118, 2026-09-05"
  - "pr: nooga/let-go#557 (gogen embedded), #613 (direct-call natives), #658 (lg_no_http), #729 (native-entry gate + frame fix), #649 (tail-call fusion); issue #783 (lifted var nil in entry-frame binaries, open), 2026-09-05"
created: "2026-09-05"
updated: "2026-09-05"
status: stable
---

# Go Backend

The design in `docs/design/go-aot-backend.md` proposed two tiers: embed bytecode as Go data, then lower functions to real Go. What shipped is the second tier, on the [IR pipeline](ir-pipeline.md): `ir.lower-go` turns an optimized IR function into Go source that keeps the runtime's `Value` and `Var` model, so lowered code and interpreted code call each other through the same vars and dynamic `eval` keeps working. This page is about that shipped backend; [lg-compile](lg-compile.md) covers the whole-program driver's command line, and [compile paths](compile-paths.md) where the backend sits relative to the other two.

## What the lowering produces

Each lowered `defn` becomes a Go function whose first parameter is the `*vm.ExecContext` and whose remaining parameters and result are either `vm.Value` or a Go type that [type inference](type-inference.md) proved (`int`, `int64`, `float64`, `bool`, `string`). Block-parameter control flow from `structurize` becomes mutable locals with labels and gotos; arithmetic on proven types stays unboxed; self-recursion (`:recur-fn`) lowers to a labelled loop. #649's `TAIL_CALL` fusion is a bytecode-lowerer optimization with no counterpart here. The header of `lower_go.lg` lists the supported ops and the two modes: strict, where an unsupported op or shape throws, and bridge, where an unsupported function falls back at whole-function granularity and stays on bytecode.

Source text is not built with string templates. The `gogen` namespace constructs `go/ast` nodes from let-go: a `(gquote (func ...))` form expands at macro time into constructor calls, those evaluate to boxed AST nodes, and `gogen/render` prints them with `go/format.Node`, so every generated file is gofmt-canonical. `gogen` is embedded in shipped binaries as an auxiliary source outside the core lowering universe (#557); see [generated artifacts](generated-artifacts.md) for why it must stay outside.

## Direct calls and the trampoline

The point of the backend is that lowered code can call other lowered code, and native primitives, as plain Go calls. Whether a function qualifies is decided per function:

- **Direct-callable** (`override-coercible?` in `lower_go.lg`): non-variadic, and every parameter and result type is one a call site can coerce soundly. A typed sibling such as `func F(ec, x int) int` is recorded with its actual specs, so a caller with a proven-`int` argument emits `F(ec, intval)` with no boxing; a caller that cannot prove the type falls back to the trampoline for that call.
- **Override-eligible**: the shape that gets an override wrapper registered on the var, so interpreted code calling the var lands on the Go function: uniform `vm.Value` in and out, or `vm.Value` parameters with a primitive return the wrapper can box (`bool`, `int`, `float64`, `string`, `vm.Char`).

Everything else, variadic functions above all, goes through `rt.CachedVarFn` and `ec.Invoke`: a var lookup, a boxed argument slice, and a dynamic dispatch. The per-namespace direct-call registry is seeded from the [native primitive](native-primitives.md) registry and from lowered siblings, and `lower-all-ns-to-go` merges every package's exports into a cross-package registry so a call into another lowered package resolves to `pkg.LG_<name>(ec, ...)` with the matching import.

One escape hatch keeps direct calls honest: `*direct-calls-disabled?*`, bound at lowering time, forces every call through the trampoline so runtime `alter-var-root` overrides are observed. `pkg/vm` also maintains a process-wide deviation counter for guarded native-primitive vars (`GuardedRootsIntact`), but at `0911118` only the `rt/native-prims-intact?` diagnostic reads it; emitted call sites do not consult it (see [namespaces and vars](namespaces-and-vars.md)).

## Two deployments

**The core.** `make generate` lowers the embedded core into `pkg/rt/core_go_lowered/` (gitignored), and a build with `-tags gogen_ir` links it: each lowered package's `init` queues overrides, and the runtime applies them onto the vars after each namespace loads from bytecode. `bench-ratchet` measures both variants, and the [ratchet doc](perf-ratchet.md) is candid that lowered core code still boxes most cross-namespace calls, so it can allocate more than bytecode; direct-call coverage is the lever.

**Programs.** `./lg scripts/lg-compile [--entry-frame] <out-dir> <import-prefix> <file.lg>...` lowers a set of files to one Go package per namespace with direct calls wired between them. With `--entry-frame` it also emits `main.go`, the native-entry frame from `passes/entry_frame.lg`: boot core, publish `*command-line-args*`, decode the program bundle, load its namespaces (draining overrides after each), replay the main chunk once so top-level forms and VM-backed vars exist, then call the lowered entry. The entry is `main` or `-main` with arity `[]`, `[argv]`, or `[& args]`; other shapes fail generation with a source-level diagnostic. The orchestrator (gloat, or a Makefile) owns `go.mod`, `go build`, and placing `program.lgb` beside `main.go`. `examples/aot/native-entry` builds `fib` and `-main` this way and reports about 16 times the VM's speed on `fib(34)`.

## The runtime-only binary

`cmd/lg-runtime` executes precompiled bytecode with no reader, compiler, or resolver linked in; the guarantee is structural, enforced by a test that the package never imports `pkg/compiler` or `pkg/resolver`, so there is no `eval`, `read-string`, or dynamic source `require`. `lg -b myapp -bundle-base lg-runtime app.lg` appends a program to a copy of it for a standalone, compiler-free bundle. It also loads a split debug companion beside the artifact (see [`.lgb` format](lgb-bytecode-format.md)). `-tags lg_no_http` (#658) drops `net/http` and the TLS and x509 packages behind it, which the linker could never prove unused because the HTTP namespace registers from an `init`; on darwin/arm64 that cut `lg-runtime` from 17.6 MB to 12.2 MB.

## Gates and open defects

`make native-entry-gate` (#729) proves that lowered entries execute as generated Go rather than through a silent fallback. Each fixture under `test/native-entry/` carries an exact `.expect` stdout and a structural `.goexpect.json` contract, and a missing sidecar fails rather than skips. Building the gate found a real defect: for a single-file program `lg -c` emits a bundle with an empty namespace table, so the frame's namespace load ran nothing and every namespace-level var stayed undefined, which only worked while every reachable callee lowered to a direct call. The frame now runs the main chunk after loading namespaces, idempotently.

Open at 2026-09-05: #783, a lowered function whose own inline lambda is lambda-lifted (`mapv (fn [f] (f)) fs`) emits `ec.Deref(rt.LookupVar(ns, "fn__lifted0"))`, and in an entry-frame binary that var is nil at first deref, so the binary panics where the VM runs the same program. The reported cause is the same empty-namespace-table path: the lifted var's override is queued but never drained before use. Also #607, an AOT bundle rejected by its own runtime over a capability-mask mismatch, tracked separately.

## Citations

**Resource:** [pkg/rt/core/ir/lower_go.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg): the lowering, strict and bridge modes, `override-coercible?`, the direct-call registry entries  
**Related:**
- [pkg/rt/core/ir/passes/pipeline.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/pipeline.lg): `lower-ns-to-go`, `lower-all-ns-to-go`, the cross-package registry vars
- [pkg/rt/core/ir/passes/entry_frame.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/entry_frame.lg): the native-entry frame
- [pkg/rt/gogen/gogen.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/gogen/gogen.lg): Go AST construction and rendering
- [scripts/lg-compile](https://github.com/nooga/let-go/blob/main/scripts/lg-compile): the whole-program driver
- [cmd/lg-runtime/main.go](https://github.com/nooga/let-go/blob/main/cmd/lg-runtime/main.go): the runtime-only binary
- [examples/aot/README.md](https://github.com/nooga/let-go/blob/main/examples/aot/README.md): the cross-package, native-entry, and YAMLScript examples
- [docs/design/go-aot-backend.md](https://github.com/nooga/let-go/blob/main/docs/design/go-aot-backend.md): the proposal (also summarised in [sources/design-go-aot-backend](../sources/design-go-aot-backend.md))
- PRs and issues: [#557](https://github.com/nooga/let-go/pull/557), [#613](https://github.com/nooga/let-go/pull/613), [#658](https://github.com/nooga/let-go/pull/658), [#729](https://github.com/nooga/let-go/pull/729), [#783](https://github.com/nooga/let-go/issues/783), [#607](https://github.com/nooga/let-go/issues/607)

See also: [Compile Paths](compile-paths.md), [lg-compile](lg-compile.md), [Self-hosting AOT](../ideas/self-hosting-aot.md), [let-go](../entities/let-go.md)
