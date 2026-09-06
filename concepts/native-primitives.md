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
  - "lg -e transcripts on lg 1.12.3-0.20260904132133 (0911118), 2026-09-05"
created: "2026-09-05"
updated: "2026-09-05"
status: stable
---

# Native Primitives

Most of `clojure.core` is Go. A native primitive is a plain Go function that the runtime binds to a var, and since #639 and #640 the binding is declared by an annotation on the function rather than by a hand-written `ns.Def` call. The annotations feed a generator that emits a committed registrar per package, the registrar registers the functions at init, and a small lifecycle keeps the native implementation in place when a namespace's Lisp source loads on top of it. The same registry tells the [Go backend](compile-paths.md) which calls it may emit as direct Go calls.

## The annotation surface

A primitive is any exported Go function carrying `//lg:native` in its doc comment:

```go
// Subs returns a substring from index start to the end.
// Mirrors clojure.core/subs with 2 arguments — `(subs s start)`.
//
//lg:native
//lg:name subs
func Subs(s string, start int) (string, error) { ... }
```

| Directive | Meaning |
|---|---|
| `//lg:native` | this function is a primitive |
| `//lg:name <n>` | the let-go name; defaults to the Go identifier kebab-cased (`UpperCase` becomes `upper-case`) |
| `//lg:ns <ns>` | the target namespace; defaults to `clojure.core` |
| `//lg:private` | parsed into `primSpec.Private` but not read by the emitter, so it has no effect on registration at `0911118` |
| `//lg:bind` | package-level marker selecting own mode for the whole package (below) |

The scanner reads parameter and result types from the Go signature, so a primitive can take `string` and `int` and return `(string, error)`; the generated adapter does the boxing and the argument-count check. A variadic `...vm.Value` signature registers with arity `-1`.

## The generator

`go run ./cmd/lgprimgen -primitives <dir> -go-pkg <import> -primitives-out <file>` scans one package and writes its `zz_primitives_generated.go`. Two things about it are deliberate:

- **It imports nothing that boots the runtime.** `internal/primgen` scans with `go/ast`, builds the output by string concatenation, and formats it in process with `go/format` (#654). The registrar it emits is what lets the next runtime boot, so a generator that booted the current runtime would depend on the artifact it is about to produce. That matters mid-migration: with closures moved out of `installLangNS` but the registrar not yet regenerated, the runtime cannot start, and the generator is what makes it consistent again.
- **The output is committed and content-gated.** `make generate` regenerates both registrars (`pkg/rt` and `pkg/rt/corefns`) and `make check-generated` fails when either is out of date, as it does for `core_compiled.lgb` (see [runtime image](runtime-image.md)).

## Two modes

The registrar's job depends on where the package sits.

- **Own mode** (`//lg:bind` present; `pkg/rt` itself): the registrar emits an adapter per primitive, `Def`s each adapter into its namespace, and registers the direct-call metadata. `pkg/rt`'s registrar holds 247 entries as of `0911118` (2026-09-05), registered as two modules, `clojure.core` and `clojure.string`, 222 of them from the #639 hoist, and runs through the runtime's installer queue (`RegisterInstaller`), the same mechanism every `install*NS` in `pkg/rt` uses, so ordering against the rest of core boot is explicit.
- **Contribute mode** (no marker; `pkg/rt/corefns`): the registrar only calls `rt.RegisterNativeModule` with the metadata. The vars already exist, defined by `core.lg` or by `pkg/rt`; what the package contributes is a typed Go entry point the Go backend can call directly. `corefns` migrated off a hand-written `NativeModule` this way in #640, and its generated file is six entries (`seq`, `first`, `second`, `next`, `rest`, `count`) that self-register from `init`.

Own-mode registration for an external package (`rt.BindGeneratedPrimitive`) is exported but not yet wired to a consumer.

## The direct-call registry

Every registration lands in a registry keyed by namespace and name, and it is readable from Lisp:

```
$ lg -e '(rt/native-direct "clojure.core" "count")'
{:variadic? false :needs-error? true :param-specs ["vm.Value"] :go-ident "Count" :result-spec "vm.Value" :arity 1 :needs-ec? false :lg-name "count"}
$ lg -e '(sort (keys (rt/native-modules)))'
("clojure.core" "clojure.string")
```

`ir.passes.pipeline/lower-ns-to-go-result` seeds `ir.lower-go/*lowered-registry*` from `(rt/native-modules)`, so a call to a registered primitive lowers to `pkg.GoIdent(args)` instead of a var lookup and a boxed invoke. #613 direct-linked the hot `clojure.core` surface this way and measured about 3.5% less time and 5.6% fewer allocations on the IR-compile benchmark. The var-dispatch boundary stays overridable: `with-redefs`, `^:dynamic`, and `^:redef` vars are exempt, and `*direct-calls-disabled?*` forces every call back through the trampoline when runtime `alter-var-root` overrides must be observed (see [compile paths](compile-paths.md)).

## The reapply lifecycle

A namespace whose Lisp source loads after runtime init, such as `clojure.string` on its first `require`, re-runs its `defn`s, and a bootstrap `(defn upper-case ...)` would overwrite the native adapter with a closure. Each generated `Def` is therefore recorded, and `reapplyGeneratedPrimitives` re-`Def`s the adapters right after an on-demand load completes. Explicit user redefinition still wins, because it happens after the load and the reapply fires only on the load itself.

```
$ lg -e "(do (require 'clojure.string) [(rt/native-prims-intact?) (clojure.string/upper-case :a)])"
[true ":A"]
```

`rt/native-prims-intact?` answers whether every generated primitive still resolves to its adapter; it is the boot-time and post-`require` gate the hoist PRs used. Two environment variables help when it says `false`: `LG_REGPRIM_DEBUG` logs every generated registration with the namespace it landed in (grep for `landed-canonical=false`), and `LG_GUARD_DEBUG` names a var whose root deviated from the native.

## How the hoist was done

`cmd/hoist-natives` is the codemod that lifted the inline closures out of `lang.go`. It hoists only sites it can prove safe: no capture of an enclosing local (package-level references and parameters are fine) and a discoverable name from an `ns.Def("<name>", <var>)` site. Five categories are reported and left alone: multi-name aliases, duplicate `//lg:native` names, `.Lookup`-by-name registrations, names a stdlib `.lg` file redefines, and closures whose variable is still referenced by surviving code (a second registration, a helper, or a skipped closure). Capturing an enclosing local is the base safety criterion, checked before those five. Its default is a dry run that prints the classification and the proposed function; `-apply` rewrites. Of 292 closures, 222 were classified safe and hoisted (#639); the rest still register the old way, and Norman's review of #686 named the hand-registered methods that shadowed generated ones as a gap in that migration, tracked under #531 (consolidating the native-behaviour mechanisms).

The three wins the codemod was built for: stack traces name `rt.CorePlus` instead of `installLangNS.func42`; registration is declarative; and a named function with a Go signature can narrow toward typed parameters over time, which is what makes it direct-callable.

## Citations

**Resource:** [internal/primgen/generate.go](https://github.com/nooga/let-go/blob/main/internal/primgen/generate.go): the runtime-free scanner and emitter, with the p0/p1 bootstrap argument in its header  
**Related:**
- [internal/primgen/prims_scan.go](https://github.com/nooga/let-go/blob/main/internal/primgen/prims_scan.go): directive parsing (`lg:native`, `lg:private`, `lg:ns`, `lg:name`) and the `//lg:bind` marker
- [cmd/lgprimgen/main.go](https://github.com/nooga/let-go/blob/main/cmd/lgprimgen/main.go): why the generator imports nothing that boots the runtime
- [cmd/hoist-natives/main.go](https://github.com/nooga/let-go/blob/main/cmd/hoist-natives/main.go): the codemod and its safety analysis
- [pkg/rt/native_prims.go](https://github.com/nooga/let-go/blob/main/pkg/rt/native_prims.go): annotated primitives (`Name`, `UpperCase`, `Subs`, and others)
- [pkg/rt/corefns/corefns.go](https://github.com/nooga/let-go/blob/main/pkg/rt/corefns/corefns.go): the contribute-mode package; its registrar and `pkg/rt`'s are generated from these annotated sources into `zz_primitives_generated.go` in each package
- [pkg/rt/native_prims_lifecycle.go](https://github.com/nooga/let-go/blob/main/pkg/rt/native_prims_lifecycle.go): reapply after on-demand load, `LG_REGPRIM_DEBUG`, `LG_GUARD_DEBUG`
- [pkg/rt/native_direct.go](https://github.com/nooga/let-go/blob/main/pkg/rt/native_direct.go): `NativeModule`, `NativeDirectFn` (including `NeedsEC`), `RegisterNativeModule` (latest registration wins), `LookupNativeDirect`
- [pkg/rt/native_direct_install.go](https://github.com/nooga/let-go/blob/main/pkg/rt/native_direct_install.go): `rt/native-modules`, `rt/native-direct`, `rt/native-prims-intact?`
- [pkg/rt/installers.go](https://github.com/nooga/let-go/blob/main/pkg/rt/installers.go): the installer queue
- [Makefile](https://github.com/nooga/let-go/blob/main/Makefile): the `lgprimgen` invocations under `generate` and `check-generated`
- PRs: [#639](https://github.com/nooga/let-go/pull/639) hoist, [#640](https://github.com/nooga/let-go/pull/640) per-package surface, [#654](https://github.com/nooga/let-go/pull/654) in-process formatting, [#613](https://github.com/nooga/let-go/pull/613) direct-call natives

See also: [Go Interop](go-interop.md), [lginterop](lginterop.md), [Value Representation](value-representation.md), [let-go](../entities/let-go.md)
