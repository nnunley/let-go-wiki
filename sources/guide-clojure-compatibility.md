---
type: Source
category: source
title: Guide — Clojure Compatibility
description: Comprehensive reference documenting let-go's Clojure dialect compatibility, including passing test suite results, supported standard namespaces, unimplemented features, and behavioral differences from JVM Clojure.
tags: [clojure, runtime, reference]
resource: "https://github.com/nooga/let-go/blob/main/docs/guide/clojure-compatibility.md"
sources:
  - "repo: nooga/let-go docs/guide/clojure-compatibility.md, 2026-07-03"
  - "repo: nooga/let-go docs/guide/clojure-compatibility.md pkg/rt/core/core.lg pkg/rt/core/walk.lg pkg/rt/core/edn.lg pkg/rt/core/clojure/pprint.lg pkg/rt/core/clojure/repl.lg pkg/rt/core/test.lg pkg/rt/core/async.lg pkg/rt/async.go pkg/rt/ions.go pkg/rt/json.go pkg/rt/system.go pkg/rt/syscall_linux.go pkg/rt/lang.go pkg/rt/host_thread.go pkg/rt/host_jvm_stubs.go pkg/rt/warnings.go pkg/compiler/compiler.go pkg/compiler/reader.go pkg/compiler/tagged_reader.go pkg/compiler/eval.go pkg/cli/gofragments.go pkg/gofragments pkg/vm/regex.go pkg/vm/numbers.go pkg/rt/core/string.lg pkg/rt/core/set.lg pkg/rt/core/pods/edn.lg @ b82588292b, 2026-10-20"
created: "2026-07-03"
updated: "2026-10-20"
status: active
---

# Clojure Compatibility Guide

Guide documenting let-go's relationship to JVM Clojure: a compatible dialect rather than a drop-in replacement. Conformance is measured with jank-lang's test suite. The upstream guide reports 5621/5621 assertions passing across 232 files through the `:clj` reader lens. Then it catalogs supported and missing features, and behavioral divergences.

This page is pinned to let-go upstream `main` at b82588292b (2026-10-20). The upstream guide's own frontmatter says `last-verified: 2026-10-11`. The source citations above name the files checked at that commit. The conformance count is the upstream guide's figure; it was not re-run for this pin.

## Key takeaways

- **Conformance**: the upstream guide reports 5621 assertions passing with the `:clj` reader lens, with no known failures, compile skips, panic skips, or runtime skips
- **Standard namespaces**: `clojure.core`, `clojure.string`, `clojure.set`, `clojure.walk`, `clojure.edn`, `clojure.pprint`, `clojure.repl`, `clojure.test`, and `clojure.core.async` are provided. Additional namespaces (`io`, `http`, `json`, `transit`, `os`, `System`, `syscall`, `pods`) are provided beyond the JVM baseline
- **Key omissions**: coordinated STM (`ref` is an atom, and `dosync` expands to `do`), asynchronous agents (`agent` is an atom, and `send` runs `swap!` synchronously), chunked sequences, Java-style `deftype` host methods, `clojure.spec`, and sorted-collection range queries (`subseq`, `rsubseq`)
- **Behavioral shifts**: numeric tower is pragmatic (int64, float64, BigInt, ratios, BigDecimal); base integer arithmetic throws on overflow; regex uses Go flavor (re2); `go` blocks are real goroutines (not IOC); channel ops always block

## Standard namespaces

| Namespace | Contents | Source |
| --- | --- | --- |
| `clojure.core` | macros, destructuring, lazy seqs, transducers, protocols, records, `deftype`, `reify`, multimethods, hierarchies, atoms, regex, metadata, BigInt, BigDecimal | `pkg/rt/core/core.lg` |
| `clojure.string` | full | `pkg/rt/core/string.lg` |
| `clojure.set` | full | `pkg/rt/core/set.lg` |
| `clojure.walk` | `prewalk`, `postwalk`, `keywordize-keys`, `stringify-keys`, `walk` | `pkg/rt/core/walk.lg` |
| `clojure.edn` | `read-string` (options `:readers`, `:default`, `:eof`), `read-all-string` | `pkg/rt/core/edn.lg`, `pkg/compiler/eval.go` |
| `clojure.pprint` | `pprint`, `cl-format` (aesthetic, radix, iteration, conditional, and justify directives), `print-table` | `pkg/rt/core/clojure/pprint.lg` |
| `clojure.repl` | `dir`, `apropos`, `doc`, `find-doc`, `source` | `pkg/rt/core/clojure/repl.lg` |
| `clojure.test` | `deftest`, `is`, `testing`, `are`, fixtures, `run-tests`, `run-test-var` / `run-test` (single var) | `pkg/rt/core/test.lg` |
| `clojure.core.async` | channels, `go` / `go-loop`, `alts!`, `mult` / `pub`, `pipe` / `merge` / `split`; `go` blocks are goroutines | `pkg/rt/core/async.lg`, `pkg/rt/async.go`; `go-loop` is defined in `pkg/rt/core/core.lg` |
| `io` | polymorphic readers and writers, `slurp` / `spit`, lazy line-seq, encoding, URLs, `with-open`, `resource` (filesystem in dev, embedded in `-b` binaries) | `pkg/rt/ions.go` |
| `http` | Ring-style server and client, streaming responses | upstream guide |
| `json` | `read-json`, `write-json` (float-preserving, record-aware) | `pkg/rt/json.go` |
| `transit` | transit+json codec with rolling cache | upstream guide |
| `os` | process execution, environment and args, filesystem and path operations, host information. See the upstream `docs/guide/os.md` | upstream guide |
| `System` | JVM-shaped: `getProperty`, `getProperties`, `getenv`, `exit`, `currentTimeMillis`, `nanoTime`. Exposes `let-go.version`, `let-go.commit`, `user.home`, `user.dir`, `os.name`, `os.arch` | `pkg/rt/system.go` |
| `syscall` | direct Linux syscalls (mount, unshare, mknod, prctl, capset, seccomp, AppArmor) | `pkg/rt/syscall_linux.go` |
| `pods` | Babashka pods over JSON, EDN, and transit | `pkg/rt/core/pods/edn.lg` |

### Reader and tagged literals

The reader supports `#uuid` and `#inst` through `default-data-readers`. Custom tagged literals are supported through the dynamic `*data-readers*` map, which holds symbol-to-function entries. `*default-data-reader-fn*` is called for any other tag (`pkg/rt/core/core.lg`, `-read-tagged`; `pkg/compiler/tagged_reader.go`). A tag that no reader handles throws `No reader function for tag <tag>` (`pkg/rt/core/core.lg`; `pkg/compiler/reader.go`).

`lg` also reads raw `#go{...}` fragments. A `*data-readers*` entry for `#go` is installed by importing the Go package `pkg/gofragments`. The build tag `lg_no_gofragments` leaves that entry out (`pkg/cli/gofragments.go`). See the upstream `docs/guide/custom-data-readers.md`.

## Not implemented

- **STM coordination**: there is no transactional coordination. `ref` is bound to `atom` and `ensure` to `deref`. `ref-set` is `(reset! r v)` and `alter` is `(apply swap! r f args)`, and `commute` is bound to `alter`. `dosync` expands to `do` (`pkg/rt/core/core.lg`, lines 2892-2900, the "Clojure compatibility" block near the `future` macro).
- **Asynchronous agents**: `agent` is an atom. `send` and `send-off` run `swap!` synchronously; an action error is recorded in `*agent-errors*` and returned by `agent-error`. `await` returns `nil` and `await-for` returns `true`, without waiting (`pkg/rt/core/core.lg`, lines 2902-2915, the agents block after `dosync`).
- **Chunked sequences**: lazy seqs are unchunked (upstream guide).
- **Java-style `deftype` method bodies and host interfaces**: protocol implementations work. JVM host methods on `deftype` do not (upstream guide). `reify` accepts `Object` overrides of `toString`, `hashCode`, and `equals` only, and any other `Object` method name is a compile-time error (`pkg/rt/core/core.lg`, the `reify` expansion). `toString` is wired into the value's string representation, so `str`, `pr-str`, and `println` use it. `hashCode` and `equals` are accepted and ignored; instance hash and equality stay identity-based.
- **Spec**: there is no `clojure.spec` namespace in the source tree.
- **`subseq` / `rsubseq`**: sorted collections work (`sorted-map`, `sorted-set`, `rseq`; `pkg/rt/core/core.lg`, `pkg/rt/lang.go`). Range queries are not defined.

## Behavioral differences

- `concat*` is eager and is used by quasiquote at compile time. User-facing `concat` is lazy (`pkg/rt/core/core.lg`, the `concat*` comment).
- `<!` and `<!!` are identical, and `>!` and `>!!` are identical. Go channels always block (`pkg/rt/async.go`, the blocking aliases).
- `go` blocks are real goroutines, not IOC state machines. They can call blocking operations directly (`pkg/rt/async.go`).
- The numeric tower is pragmatic: `int64`, `float64`, `BigInt`, ratios, and `BigDecimal`. It does not model the JVM primitive and class system.
- Base integer `+`, `-`, and `*` return the error `integer overflow` on int64 overflow instead of wrapping. The checks are in `NumAdd`, `NumSub`, and `NumMul` (`pkg/vm/numbers.go`, lines 78-87, 126-135, 174-183), which the base natives in `pkg/rt/lang.go` (`CorePlus`, `CoreSub`, `CoreMul`) call. `inc` and `dec` are defined as `(+ x 1)` and `(- x 1)` (`pkg/rt/core/core.lg`, lines 218-219), so they overflow through the same path. `+'`, `-'`, and `*'` are native functions in `pkg/rt/lang.go` (`CorePlusP`, `CoreSubP`, `CoreMulP`) that promote to BigInt. `inc'` and `dec'` are defined on top of `+'` and `-'` in `pkg/rt/core/core.lg` (lines 224-225).
- Regex is Go flavor (`re2`), compiled with `regexp.Compile` (`pkg/vm/regex.go`), not Java regex.
- `letfn` uses atoms internally for forward references (`pkg/rt/core/core.lg`, the `letfn` macro).
- `Thread/currentThread` returns the calling scope. `.isInterrupted` reads scope cancellation, and `.interrupt` cancels the scope. Both work inside `with-scope`. At the root scope, `.interrupt` throws rather than cancelling the program's tracked work. `Thread.` cannot be constructed (`pkg/rt/host_thread.go`, `pkg/rt/host_jvm_stubs.go`).
- `format` is Go `fmt` underneath. Java's `%n` is rewritten to `\n` before formatting (`pkg/rt/lang.go`, the `formatNewlines` helper). Surplus arguments are ignored, as in Java's Formatter (`pkg/rt/lang.go`).
- `=` gives the same answer on all three compile paths. `identical?` is promised only for a value compared with itself, and a value stays `identical?` to itself however it travels through `let`, `loop`, `if`, or a fn argument. Whether two equal literals written in different places are one object is unspecified, as in Clojure. A literal map keeps the key order it was written in, so constant sharing never replaces a map with an equal map whose keys are in a different order (upstream guide).
- A `fn` that closes over nothing is created once and shared on all three compile paths (the default compiler, `*ir-compile*`, and lowered Go). `(defn mk [] (fn [x] x))` returns the same object on every call, so `(identical? (mk) (mk))` is `true`. A `fn` that closes over locals is a new object per evaluation (upstream guide).
- Code lowered to native Go (`-tags gogen_ir`) links a call from one lowered fn to another directly. `with-redefs`, `alter-var-root`, or a re-`def` of a lowered fn reaches bytecode callers and anything that calls through the var, but not other lowered fns until they are recompiled. A `^:redef` or `^:dynamic` fn is never linked directly. The default compiler and `*ir-compile*` always call through the var (upstream guide).

## Compiler compatibility vars

**`*warn-on-reflection*`** is dynamic and defaults to `false` (`pkg/rt/core/core.lg`). "Reflection" here means a missed static-dispatch opportunity in let-go, not JVM method reflection. When the var is truthy, compilation or IR/Go lowering warns once per source site for:

- host member dispatch whose target type is not statically known; and
- a known direct or native candidate that cannot be lowered and reaches the generic `InvokeValueEC` trampoline.

Warnings are emitted by `pkg/rt/warnings.go`. Ordinary higher-order IFn calls, protocol dispatch, known host targets, and direct or native-lowered calls do not warn. A host receiver counts as known when the source names its type: a literal, a fresh constructor call, a `^Tag` hint on the receiver form, or a local whose nearest binding is known. A call whose receiver is another call's result still warns, because let-go does not model method return types (upstream guide).

Known limitation (upstream guide): a known receiver silences the host warning, but no compile path dispatches host members statically yet. The bytecode compiler, `*ir-compile*`, and the Go lowering route member calls through the generic `.` builtin. A type hint is neither checked against the runtime value nor used to pick the method. Only the bytecode compiler emits the host warning.

Numeric parameter hints (`^double x`, `^long n`) are separate. The AOT native-Go lowering uses them to run arithmetic on unboxed Go `float64` and `int64`. They have no effect on host-member dispatch or on the plain bytecode path (upstream guide).

**`*unchecked-math*`** is dynamic and settable. At b82588292b the bytecode compiler does act on it. When the var is truthy, `+`, `-`, `*`, `inc`, and `dec` are rewritten to `clojure.core/unchecked-add`, `unchecked-subtract`, `unchecked-multiply`, `unchecked-inc`, and `unchecked-dec` before the call is compiled. The fast-opcode path is skipped while the var is truthy, so the checked opcode is not emitted (`pkg/compiler/compiler.go`, the `*unchecked-math*` rewrite and the `uncheckedArithFor` table). The upstream guide says changing this var "currently has no code-generation effect". That statement does not match the bytecode compiler at this commit. The `*ir-compile*` and Go-lowering paths were not checked for this claim.

## Citations

- nooga/let-go: [Clojure compatibility and differences](https://github.com/nooga/let-go/blob/main/docs/guide/clojure-compatibility.md), pinned to b82588292b
- nooga/let-go source at b82588292b: the files listed in `sources`

## Derived pages

- [clojure-compat](../references/clojure-compat.md)
