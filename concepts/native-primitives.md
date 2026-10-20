---
type: Concept
category: concept
title: "Native Primitives"
description: "How Go functions become clojure.core (and other) vars: the //lg:native annotation surface, the runtime-free lgprimgen registrar generator, contribute vs own mode, the direct-call registry, and the reapply lifecycle that keeps natives in place."
tags: [runtime, go, interop, compiler, stdlib]
resource: "https://github.com/nooga/let-go/blob/main/internal/primgen/generate.go"
sources:
  - "repo: nooga/let-go internal/primgen/*.go, cmd/lgprimgen, cmd/hoist-natives, pkg/rt/{native_prims,native_prims_lifecycle,native_direct,native_direct_install,installers}.go, pkg/rt/corefns, Makefile @ 0911118, 2026-09-05"
  - "pr: nooga/let-go#639 (hoist 222 primitives), #640 (per-package registrar surface), #654 (in-process go/format), #613 (direct-call natives), 2026-09-05"
  - "lg -e transcripts on lg 1.12.3-0.20260904132133 (0911118), 2026-09-05; the transcripts are no longer cited in the body, which is checked against b82588292b"
  - "pr: nooga/let-go#862 (int64 scalar params on Subs/Nth/Deref) @ a044ead1, 2026-09-16"
  - "repo: nooga/let-go internal/primgen/*.go, cmd/lgprimgen/main.go, cmd/hoist-natives/main.go, pkg/rt/{native_prims,native_prims_lifecycle,native_direct,native_direct_install,installers,lang,coreload,zz_run_installers}.go, pkg/rt/zz_primitives_generated.go, pkg/rt/corefns/{corefns.go,zz_primitives_generated.go}, pkg/rt/core/ir/lower_go.lg, pkg/rt/core/ir/passes/pipeline.lg, scripts/generate.lg, scripts/check-generated.sh, Makefile, test/native-bridge-parity.lg @ b82588292b, 2026-10-20"
created: "2026-09-05"
updated: "2026-10-20"
status: stable
---

# Native Primitives

Most of `clojure.core` is Go. A native primitive is a plain Go function that the runtime binds to a var, and since #639 and #640 the binding is declared by an annotation on the function rather than by a hand-written `ns.Def` call. The annotations feed a generator that emits a committed registrar per package. The registrar registers the functions at init, and a small lifecycle keeps the native implementation in place when a namespace's Lisp source loads on top of it. The same registry tells the [Go backend](compile-paths.md) which calls it may emit as direct Go calls.

## The annotation surface

A primitive is any top-level Go function whose doc comment contains `//lg:native`. Methods, and functions without a doc comment, are not scanned. Files named `*_test.go`, files named `zz_*`, and files under a build constraint are skipped (`internal/primgen/generate.go`).

```go
// Subs returns a substring from index start to the end.
// Mirrors clojure.core/subs with 2 arguments — `(subs s start)`.
//
//lg:native
//lg:name subs
func Subs(s string, start int64) (string, error) { ... }
```

| Directive | Meaning |
|---|---|
| `//lg:native` | this function is a primitive |
| `//lg:name <n>` | the let-go name; defaults to the Go identifier kebab-cased (`UpperCase` becomes `upper-case`) |
| `//lg:ns <ns>` | the target namespace; defaults to `clojure.core` |
| `//lg:private` | parsed into `primSpec.Private`; the emitter (`prims_emit.go`) does not read it, so it has no effect on registration at `b82588292b` |
| `//lg:bind` | package-level marker selecting own mode for the whole package (below) |

The scanner reads parameter and result types from the Go signature, so a primitive can take `string` and `int64` and return `(string, error)`; the generated adapter does the boxing and the argument-count check. A fixed-arity mismatch returns `wrong number of args (N), expected K`; a variadic function with too few arguments returns `wrong number of args (N), expected at least K`; the multi-arity dispatch fallback returns `wrong number of args (N)` (`internal/primgen/prims_emit.go` lines 211, 283, 448). Signature rules:

- A first parameter of type `*vm.ExecContext` is not counted in the Lisp arity; it sets `NeedsEC`.
- A result list whose last result is an unnamed `error` sets `NeedsError`; the first result is the value.
- A variadic `...vm.Value` signature registers with arity `-1`, and the fixed parameters remain in `ParamSpecs`.
- Several `//lg:native` functions that share a namespace and `//lg:name` form a multi-arity group. Each fixed arity is registered under a key `name@N`, and a variadic member is registered under `name@variadic` (`internal/primgen/prims_emit.go` lines 790-800). `Subs` and `Subs3` appear as `subs@2` and `subs@3` (`pkg/rt/zz_primitives_generated.go`).

Scalar integer parameters are declared `int64` rather than host-width `int`. The [Go backend](go-backend.md) maps a let-go `:int` to `int64` (`go-type-spec` in `pkg/rt/core/ir/lower_go.lg`), and #862 changed `Subs` (both arities), `Nth` (both arities) and `Deref` with a timeout to `int64` so that a lowered caller matches the signature. The coercion table in `lower_go.lg` accepts both `int` and `int64` parameter types; which path a lowered call to an `int`-declared primitive takes at run time has not been checked against a run for this pin.

## The generator

`go run ./cmd/lgprimgen -primitives <dir> -go-pkg <import> -primitives-out <file>` scans one package and writes its `zz_primitives_generated.go`. The flags default to `pkg/rt`, `github.com/nooga/let-go/pkg/rt` and `pkg/rt/zz_primitives_generated.go`. `cmd/lgprimgen/main.go` is a wrapper around `primgen.Generate`; the scanner is `prims_scan.go`, the emitter is `prims_emit.go`, and the driver with the in-process formatter is `generate.go`. Two things about it are deliberate:

- **It imports nothing that boots the runtime.** `internal/primgen` scans with `go/ast`, builds the output by string concatenation, and formats it in process with `go/format` (#654). The registrar it emits is what lets the next runtime boot, so a generator that booted the current runtime would depend on the artifact it is about to produce. That matters mid-migration: with closures moved out of `installLangNS` but the registrar not yet regenerated, the runtime cannot start, and the generator is what makes it consistent again.
- **The output is committed and checked.** `make generate` runs `scripts/generate.lg`, which regenerates `pkg/rt/zz_primitives_generated.go` and `pkg/rt/corefns/zz_primitives_generated.go` when they are stale. `make check-generated` runs `scripts/check-generated.sh`, which covers both registrars and `core_compiled.lgb` (see [runtime image](runtime-image.md)).

## Two modes

The registrar's job depends on where the package sits.

- **Own mode** (`//lg:bind` present in a scanned file; `pkg/rt` itself, marked in `pkg/rt/lg_bind_marker.go`): the registrar emits an adapter per lg-name (a dispatch adapter for a multi-arity name), `Def`s each adapter into its namespace, and registers the direct-call metadata. At `b82588292b`, `pkg/rt`'s registrar has 249 entries: 248 in `clojure.core` and 1 in `clojure.string` (`upper-case`). It registers through `RegisterInstaller` (`pkg/rt/installers.go`). `pkg/rt/zz_run_installers.go` calls `runInstallers()` from an `init` that runs after the package's other `init` functions, so the registrar runs after the other installers have been queued.
- **Contribute mode** (no marker; `pkg/rt/corefns`): the registrar only calls `rt.RegisterNativeModule` with the metadata, from its own `init`. The vars already exist, defined by `core.lg` or by `pkg/rt`; what the package contributes is a typed Go entry point the Go backend can call directly. `corefns` migrated off a hand-written `NativeModule` this way in #640. Its generated file has six entries (`seq`, `first`, `second`, `next`, `rest`, `count`), all in `clojure.core`.

Own-mode registration for an external package (`rt.BindGeneratedPrimitive`) is exported. Its only caller in the repository at `b82588292b` is a test (`pkg/rt/native_prims_lifecycle_test.go`).

## The direct-call registry

Every registration lands in a registry keyed by namespace and name. `RegisterNativeModule` (`pkg/rt/native_direct.go`) records each module's `Fns` under its namespace; a second registration of the same key replaces the earlier entry. Besides `pkg/rt`'s own registrar, two other modules write to `clojure.core` in the registry: the hand-written `registerBuiltinsModule` in `pkg/rt/lang.go` (`GoPkg` `pkg/rt/builtins`), and the contribute-mode `corefns` module, which registers when its package is linked.

Lisp reads the registry through three functions installed in the `rt` namespace (`pkg/rt/native_direct_install.go`):

- `rt/native-modules` returns a map from namespace name to a vector of module maps, each with `:go-pkg`, `:ns`, and `:fns`.
- `rt/native-direct` takes a namespace string and a name string and returns a descriptor map or `nil`. The descriptor has `:go-ident`, `:arity`, `:variadic?`, `:param-specs`, `:result-spec`, `:needs-error?`, and `:needs-ec?`, and `:lg-name` only when the registrar supplied a non-empty LgName (`pkg/rt/native_direct_install.go` lines 110-112; generated entries always set it).
- `rt/native-prims-intact?` returns `NativePrimsIntact()` (see the reapply lifecycle below).

For `"clojure.core" "count"`, the registrar entry is `{GoIdent: "CoreCount", LgName: "count", Arity: -1, Variadic: true, ParamSpecs: []string{}, ResultSpec: "vm.Value", NeedsError: true}`, so the descriptor has `:go-ident "CoreCount"`, `:arity -1`, `:variadic? true`, `:param-specs []`, and `:needs-error? true`.

`ir.passes.pipeline/lower-ns-to-go-result` (`pkg/rt/core/ir/passes/pipeline.lg`) builds the native half of `ir.lower-go/*lowered-registry*` from `(rt/native-modules)` through `native-registry` (`lower_go.lg`). A call to a registered primitive then lowers to `pkg.GoIdent(args)` instead of a var lookup and a boxed invoke. A variadic native is expanded into fixed-arity entries for up to eight rest arguments beyond its fixed parameters; a call with more arguments stays on the trampoline. #613 direct-linked the hot `clojure.core` surface this way and reported about 3.5% less time and 5.6% fewer allocations on the IR-compile benchmark (figures from the PR; not re-run for this pin).

The var-dispatch boundary stays overridable. Native call sites are gated on `rt.NativePrimsIntact()` (`test/native-bridge-parity.lg` states this), so a guarded native root that has been overridden routes calls to the var trampoline. A user `defn` marked `^:dynamic` or `^:redef` is never recorded in the sibling registry, so callers reach it through its var (`lower_go.lg`). `*direct-calls-disabled?*` (`lower_go.lg`) makes `lookup-direct-candidate` return `nil`, so every call falls back to the cached-var trampoline (see [compile paths](compile-paths.md)).

## The reapply lifecycle

Each generated `Def` goes through `defGeneratedPrimitive` (`pkg/rt/native_prims_lifecycle.go`). It sets the adapter as the var's root and marks it with `GuardRoot`, and it records the adapter in `genPrimBindings`, keyed by canonical namespace and var name.

A namespace whose Lisp source loads after runtime init, such as `clojure.string` on its first `require`, re-runs its `defn`s, and a bootstrap `(defn upper-case ...)` would overwrite the native adapter with a closure. `reapplyGeneratedPrimitives` restores each recorded adapter in place through `setPrimitiveRoot`, which sets the root of the existing `Var` rather than calling `Def` when the name is already interned, so code already compiled against that `Var` stays linked to it. When the name is not yet interned, `setPrimitiveRoot` falls back to `Namespace.Def` (`pkg/rt/native_prims_lifecycle.go` lines 128-133). The namespace loader in `pkg/rt/lang.go` calls it when a load succeeds, and `pkg/rt/coreload.go` calls `ReapplyGeneratedPrimitives` after each hybrid chunk. Explicit user redefinition still wins, because it happens after the load, and the reapply fires only on the load itself.

`rt/native-prims-intact?` returns `NativePrimsIntact()`, which is true while `vm.GuardedRootsIntact()` holds. `test/native-bridge-parity.lg` asserts that it is `true` in the steady state, `false` inside a `with-redefs` of `reduce`, and `true` again after the `with-redefs` unwinds.

Diagnostics:

- `LG_REGPRIM_DEBUG` logs every generated registration as `[REGPRIM] <ns>/<name> requested-ns= canonical= landed-canonical=<bool>`. Grep for `landed-canonical=false`.
- `LG_GUARD_DEBUG` prints `[GUARD] deviated: [...]` with the names of the guarded vars whose roots no longer hold the native whenever the guard check fails.
- `AuditGeneratedPrimitives` returns one line per recorded primitive that is not bound in its canonical namespace.
- `ShadowedHandRegistrations` lists `<requested-ns>/<name>` pairs where a generated registration took a var that another registration had already interned.

## How the hoist was done

`cmd/hoist-natives` is the codemod that lifted the inline closures out of `pkg/rt/lang.go` into named `//lg:native` functions. Its default run is a dry run that prints a classification report and the proposed function for each safe site. `-apply` performs the rewrite. For each registration site it checks, in this order, and skips the site on the first match:

1. No `ns.Def("<name>", <var>)` site gives the var a name. Reported as "skipped: no ns.Def(\"name\", var) found (registered differently / internal)" (`cmd/hoist-natives/main.go` line 889).
2. The var is registered under more than one name. Reported as "registered under multiple lg-names".
3. The lg-name is fetched with `.Lookup("<name>")` anywhere in the package. Reported with the multiple-names group.
4. A pre-existing `//lg:native` declaration in another file already owns the lg-name. Reported as a duplicate.
5. A stdlib `.lg` file under `pkg/rt/core` redefines the name. Reported as "redefined in .lg".
6. The closure captures an enclosing local, found by free-variable analysis. Package-level names and parameters are not captures. Reported as a capture.

After these checks, a safe variable that is still referenced by surviving code (a second registration, a helper, or a skipped closure) is demoted and not hoisted. The report lists the surviving-reference skips separately.

Of 292 closures, 222 were classified safe and hoisted (#639); the rest still register the old way. Norman's review of #686 named the hand-registered methods that shadowed generated ones as a gap in that migration, tracked under #531 (consolidating the native-behaviour mechanisms).

The three wins the codemod's header gives (`cmd/hoist-natives/main.go` lines 4-12): stack traces read `rt.corePlus` instead of `installCore.func42`; registration becomes declarative, with the `ns.Def` call dropped and the registration emitted from the `//lg:native` and `//lg:name` annotations; and it is the #411 "Fn-adapter" done as a codemod. The header does not mention typed parameters. The link to direct calls is this page's reading: a named function with a Go signature can be narrowed toward typed parameters over time, which is what makes it direct-callable.

## Citations

**Resource:** [internal/primgen/generate.go](https://github.com/nooga/let-go/blob/main/internal/primgen/generate.go): the package entry point (`Generate`), the in-process `go/format` step, and the header on why the generator is runtime-free and what the p0/p1 bootstrap argument means  
**Related:**
- [internal/primgen/prims_scan.go](https://github.com/nooga/let-go/blob/main/internal/primgen/prims_scan.go): directive parsing (`lg:native`, `lg:private`, `lg:ns`, `lg:name`), signature parsing, and the `//lg:bind` marker
- [internal/primgen/prims_emit.go](https://github.com/nooga/let-go/blob/main/internal/primgen/prims_emit.go): adapter, multi-arity dispatch, and registrar emission; own vs contribute mode
- [cmd/lgprimgen/main.go](https://github.com/nooga/let-go/blob/main/cmd/lgprimgen/main.go): why the generator imports nothing that boots the runtime
- [cmd/hoist-natives/main.go](https://github.com/nooga/let-go/blob/main/cmd/hoist-natives/main.go): the codemod, its classification order, and its safety analysis
- [pkg/rt/native_prims.go](https://github.com/nooga/let-go/blob/main/pkg/rt/native_prims.go): annotated primitives (`Name`, `UpperCase`, `Subs`/`Subs3`, `Nth`/`Nth3`, `Deref`/`Deref3`, and others)
- [pkg/rt/corefns/corefns.go](https://github.com/nooga/let-go/blob/main/pkg/rt/corefns/corefns.go): the contribute-mode package; its registrar is generated from these annotated sources into `pkg/rt/corefns/zz_primitives_generated.go` (`pkg/rt`'s registrar comes from its own directory, not from this file; `scripts/generate.lg` lines 170-177)
- [cmd/lgprimgen/main.go](https://github.com/nooga/let-go/blob/main/cmd/lgprimgen/main.go): the generator that writes `pkg/rt/zz_primitives_generated.go`, the own-mode registrar for `pkg/rt`
- [pkg/rt/native_prims_lifecycle.go](https://github.com/nooga/let-go/blob/main/pkg/rt/native_prims_lifecycle.go): binding, reapply after on-demand load, `NativePrimsIntact`, `LG_REGPRIM_DEBUG`, `LG_GUARD_DEBUG`, `AuditGeneratedPrimitives`
- [pkg/rt/native_direct.go](https://github.com/nooga/let-go/blob/main/pkg/rt/native_direct.go): `NativeModule`, `NativeDirectFn` (including `NeedsEC`), `RegisterNativeModule` (latest registration wins), `LookupNativeDirect`
- [pkg/rt/native_direct_install.go](https://github.com/nooga/let-go/blob/main/pkg/rt/native_direct_install.go): `rt/native-modules`, `rt/native-direct`, `rt/native-prims-intact?`
- [pkg/rt/installers.go](https://github.com/nooga/let-go/blob/main/pkg/rt/installers.go): the installer queue; [pkg/rt/zz_run_installers.go](https://github.com/nooga/let-go/blob/main/pkg/rt/zz_run_installers.go) runs it
- [pkg/rt/lang.go](https://github.com/nooga/let-go/blob/main/pkg/rt/lang.go): the namespace loader that calls the reapply, and the hand-written `registerBuiltinsModule`
- [pkg/rt/coreload.go](https://github.com/nooga/let-go/blob/main/pkg/rt/coreload.go): `ReapplyGeneratedPrimitives` after each hybrid chunk
- [pkg/rt/core/ir/lower_go.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg): `native-registry`, `go-type-spec`, `*direct-calls-disabled?*`
- [pkg/rt/core/ir/passes/pipeline.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/pipeline.lg): seeding the lowered registry from `(rt/native-modules)`
- [test/native-bridge-parity.lg](https://github.com/nooga/let-go/blob/main/test/native-bridge-parity.lg): the `redefinition-guard` assertions on `rt/native-prims-intact?`
- [scripts/generate.lg](https://github.com/nooga/let-go/blob/main/scripts/generate.lg) and [scripts/check-generated.sh](https://github.com/nooga/let-go/blob/main/scripts/check-generated.sh): the regeneration and check steps
- [Makefile](https://github.com/nooga/let-go/blob/main/Makefile): the `generate` and `check-generated` targets
- PRs: [#639](https://github.com/nooga/let-go/pull/639) hoist, [#640](https://github.com/nooga/let-go/pull/640) per-package surface, [#654](https://github.com/nooga/let-go/pull/654) in-process formatting, [#613](https://github.com/nooga/let-go/pull/613) direct-call natives, [#862](https://github.com/nooga/let-go/pull/862) int64 scalar parameters

See also: [Go Interop](go-interop.md), [lginterop](lginterop.md), [Value Representation](value-representation.md), [let-go](../entities/let-go.md)
