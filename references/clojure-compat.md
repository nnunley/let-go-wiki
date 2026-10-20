---
type: Reference
category: reference
title: "Clojure Compatibility"
description: "Where let-go IS and ISN'T compatible with Clojure JVM: known limitations, feature parity, and behavioral differences."
tags: [clojure, lisp, runtime]
resource: "https://github.com/nooga/let-go/blob/main/docs/guide/clojure-compatibility.md"
sources: ["docs/guide/clojure-compatibility.md", "docs/clojure-compat-roadmap.md", "repo: nooga/let-go pkg/rt/core/core.lg (lines 261, 2072-2083, 3089-3102), pkg/compiler/tagged_reader.go, pkg/compiler/eval.go (load-string) @ b82588292b, 2026-10-19", "repo: nooga/let-go pkg/rt/core/edn.lg (lines 53-71), pkg/rt/json.go (lines 24-68) @ b82588292b, 2026-10-19", "repo: nooga/let-go pkg/vm/vm.go (multiArityAt, lines 199-206), pkg/rt/core/ir/lower_go.lg (lines 1182-1214) @ b82588292b, 2026-10-19", "repo: nooga/let-go docs/guide/clojure-compatibility.md, pkg/compiler/reflection_warning_test.go, pkg/compiler/constant_literal_test.go @ b82588292b, 2026-10-19", "pr: nooga/let-go#986 (edn read-string options), #995 (exact JSON integers), #1009 (fn literal sharing, documented), #1014 (fn literal sharing on every compile path), #964 (reflection-warning known targets) merged by b82588292b, 2026-10-19", "repo: nooga/let-go docs/known-divergences.md, test/map_order_test.lg @ ebd9a7bd, 2026-09-09", "pr: nooga/let-go#770 (data readers), #762 (reify Object), #758 (invokable symbols), #840 (Math/* JVM semantics), #841 (canonical dot form), #901 (Thread/currentThread, %n), #843 (split), #854 (edn reads data), #839 (*unchecked-math*), #787 (StringBuilder), #820 (json string keys), #855 (line-seq errors), #711 (clojure.data), #668 (clojure.repl), #863 (clojure.test) all merged for v1.13.0, 2026-09-20", "lg -e transcripts on lg 1.13.0 (369e2a69): every behaviour in the JVM-interop and numerics sections re-probed, plus require of every core namespace short and clojure.* name, 2026-09-20"]
created: "2026-07-02"
updated: "2026-10-19"
status: stable
---

# Clojure Compatibility

let-go is a Clojure dialect, not a drop-in JVM Clojure replacement. Most idiomatic Clojure code runs unmodified, but host-interop and concurrency models differ. let-go passes **5621 / 5621 assertions** across 232 test files from the [jank-lang/clojure-test-suite](https://github.com/jank-lang/clojure-test-suite) under the `:clj` reader lens with zero failures.

## Standard namespaces

| Namespace | Status |
|-----------|--------|
| `clojure.core` | Macros, destructuring, lazy sequences, transducers, protocols, records, `deftype`, `reify`, multimethods, hierarchies, atoms, regex, metadata, BigInt, BigDecimal |
| `clojure.string` | Full implementation |
| `clojure.set` | Full implementation |
| `clojure.walk` | `prewalk`, `postwalk`, `keywordize-keys`, `stringify-keys`, `walk` |
| `clojure.edn` | `read-string` and `read-all-string`; reads data rather than code since #854. `read-string` takes `:readers`, `:default` and `:eof` options, and `read-all-string` takes `:readers` and `:default` (#986) |
| `clojure.pprint` | `pprint`, `cl-format` |
| `clojure.test` | `deftest`, `is`, `testing`, `are`, fixtures; #863 replaced the partial namespace with the report, assert, fixture and runner contract |
| `clojure.data` | `diff` (structural projection, #711) |
| `clojure.repl` | `doc` and friends, with a Var-metadata bundle round trip (#668) |
| `async` | Channels, `go`/`go-loop`, `alts!`, `mult`/`pub`, `pipe`/`merge`/`split` (real goroutines, not IOC). Required as `[async ...]`; `clojure.core.async` does not resolve |
| `io` | Polymorphic readers/writers, `slurp`/`spit`, lazy line-seq, encoding, URLs, `with-open`, `resource` |
| `http` | Ring-style server and client, streaming responses |
| `json` | `read-json`, `write-json` (float-preserving, record-aware); integer literals decode exactly, as int64 or BigInt past that, so values above 2^53 are no longer rounded through float64 (#995). Decimal and exponent forms go through float64, and a whole value in int64 range still decodes as an Int, so `1.0` and `2e3` read as `1` and `2000`; other decimal and exponent values read as floats; since #820 a string map key is written as text, so `{"key" "value"}` emits `{"key":"value"}` rather than the double-quoted EDN reading |
| `transit` | transit+json codec with rolling cache |
| `os` | `sh`, `stat`, `ls`, `cwd`, `getenv`/`setenv`, `exit`, `os-name`, `arch`, `user-name`, `hostname` |
| `System` | JVM-shaped API: `getProperty`, `getProperties`, `getenv`, `exit`, `currentTimeMillis`, `nanoTime` |
| `syscall` | Direct Linux syscalls (mount, unshare, mknod, prctl, capset, seccomp, AppArmor) |
| `pods` | [Babashka pods](../concepts/pods.md) over JSON/EDN/transit |

## Not implemented

| Feature | Reason |
|---------|--------|
| **STM coordination** (`ref`/`dosync`) | Atom-backed compatibility aliases; not coordinated STM |
| **Asynchronous agents** (`agent`/`send`/`send-off`) | Synchronous atom-backed compatibility aliases |
| **Chunked sequences** | Lazy seqs are unchunked |
| **Arbitrary JVM host methods on `deftype`/`reify`** | Protocol implementations work, and #762 added the `Object` overrides `toString`, `hashCode` and `equals`; other host methods do not |
| **`clojure.spec`** | Not ported |
| **`subseq`/`rsubseq`** | Sorted collections work; range queries don't |

## Behavioral differences

### Concurrency and async

- `<!` and `<!!` are identical; same for `>!` and `>!!` (Go channels always block).
- `go` blocks are real goroutines, not IOC state machines (cheaper, can call blocking ops directly).

### Numerics

- Tower includes `int64`, `float64`, `BigInt`, ratios, and `BigDecimal` without JVM's full primitive/class model.
- Base integer `+`/`-`/`*`/`inc`/`dec` throw on overflow; use `+'`/`-'`/`*'`/`inc'`/`dec'` for BigInt-promoting exact math, or the `unchecked-*` functions to wrap.
- `*unchecked-math*` is live since #839, and it is a **compile-time** flag as on the JVM: the five operators above are rewritten to their wrapping forms while a form is compiled under the binding, so wrapping a runtime `binding` around already-compiled code changes nothing. On lg 1.13.0, `(binding [*unchecked-math* true] (eval '(* 9223372036854775807 2)))` is `-2`, while the same multiplication compiled outside the binding still throws `integer overflow`.

### String processing and regex

- `clojure.string/split` follows `Pattern.split` since #843: trailing empty fields are dropped, the result is a vector rather than a list, and a limit arity is accepted. `(clojure.string/split "a,b,," #",")` is `["a" "b"]`. `split-lines` was added at the same time.
- Regex is Go flavor (`re2`), not Java regex.
  - Supports most common patterns.
  - Lacks lookaround, backreferences, named capture groups, possessive quantifiers.
  - Linear-time execution; no ReDoS risk (unless using extended regex engine).

### JVM-shaped interop surface

JAR loading is still unsupported (see Interop story below), but a JVM-shaped surface exists for the idioms libraries reach for. Each of these was re-probed on lg 1.13.0:

- `Math/*` and the boxed-type statics are pinned to JVM semantics rather than Go's (#840). `(Math/round -2.5)` is `-2`, where Go's rounding gives `-3`; `(Long/bitCount 7)` is `3` and `Integer/MAX_VALUE` is `2147483647`.
- The canonical `(. obj member ...)` form compiles, not only the `.member` sugar (#841): `(. "abc" toUpperCase)` is `"ABC"`.
- `Thread/currentThread` resolves to the calling scope dressed as a `java.lang.Thread`, so `.isInterrupted` means "was my scope cancelled" (#901). `format` honours `%n`.
- A `StringBuilder` shim exists (#787). Note that `str` on one gives `#<java.lang.StringBuilder>`; call `.toString` to get the contents.
- Symbols are invokable for collection lookup, as keywords already were (#758): `('a {'a 1})` is `1`.

### Sequence operations

- `concat*` (used internally by quasiquote) is eager; user-facing `concat` is lazy.
- `line-seq` surfaces a read error since #855, rather than ending the sequence silently.

### Maps and characters

- Traversal order of map literals and `hash-map` is unspecified by contract. Since #764 (2026-09-07) maps of up to eight entries, `array-map`, and the builders on them (`assoc` chains, `into`, `zipmap`, `merge`, `select-keys`) keep insertion order, and the ninth `assoc` promotes to hash order. An `array-map` constructed with more than eight pairs promotes at construction, unlike Clojure's. Use `sorted-map` for comparator order.
- A character is one Unicode scalar value (a Go rune), not a UTF-16 code unit: `(count "😀")` is 1 where JVM Clojure gives 2, and `(char 65895)` yields U+10167 where the JVM throws. `char` does not yet reject surrogate-range integers. The ledger for these and their shared-suite overrides is [Known Clojure divergences](../sources/docs-known-divergences.md).

### Data readers

- `*data-readers*` (#770) maps tag symbols to functions. A tagged literal `#tag form` is settled in this order. Before the form is read, an embedder's explicit Go registry entry (`TaggedReaderRegistry` in `pkg/compiler/tagged_reader.go`, which `RegisterRaw` fills) and raw readers such as `#go` are checked first. After the form is read, an explicit Go data reader (`RegisterData`) is checked, then the lg policy: a `*data-readers*` entry, then the built-in `#inst` and `#uuid`, then `*default-data-reader-fn*`, which is called with the tag and the form. The default is `nil`. If no handler applies, or the default fn returns `nil`, reading throws `No reader function for tag <tag>`. The policy is `-read-tagged` in `pkg/rt/core/core.lg` (lines 3089-3102), and the reader calls it from `readTaggedLiteral` in `pkg/compiler/reader.go` (about lines 1775-1812). `pkg/compiler/tagged_reader.go` supplies the resolver that looks up `-read-tagged` and invokes it. `read-string`, `load-string` and ordinary compilation all go through it.
- `clojure.edn` does not consult `*data-readers*` or `*default-data-reader-fn*`. Its `:readers` and `:default` options are the only tag hooks (`pkg/rt/core/edn.lg`, lines 53-66, #986).

### Identity of constants and fn literals

- Equal literals written in different places may be one object. Any compile path may share equal constants, so `identical?` on them can be `true` where JVM Clojure gives `false`. Metadata-bearing literals are not shared (`pkg/compiler/constant_literal_test.go`).
- A `fn` that closes over nothing is created once and shared on all three compile paths: the default compiler, `*ir-compile*`, and the lowered Go code. `(defn mk [] (fn [x] x))` returns the same object on every call, so `(identical? (mk) (mk))` is `true`, where JVM Clojure gives `false` (#1009 documents this in `docs/guide/clojure-compatibility.md`; #1014 made all three paths share, in `pkg/vm/vm.go` `multiArityAt` and the lowered-Go literal in `pkg/rt/core/ir/lower_go.lg` lines 1182-1214, @ b82588292b). A `fn` that closes over locals is a new object per evaluation, as on the JVM.

### Reflection warnings

- `*warn-on-reflection*` (`pkg/rt/core/core.lg`, line 261) is dynamic and defaults to `false`. Enabling it never changes execution. "Reflection" here means a missed static dispatch in let-go, not JVM method reflection. The warning fires once per source site (`pkg/compiler/reflection_warning_test.go`).
- A host receiver counts as known when the source names its type: a literal, a fresh constructor call, a `^Tag` hint, or a local whose nearest binding is known. A `let` local is known when its init is a known receiver. A `loop` local counts only through its hint, since `recur` can rebind it (#964).
- A known receiver silences the host warning, but no compile path dispatches host members statically yet. Only the bytecode compiler emits the host warning. A receiver that is another call's result still warns, because let-go does not model method return types (`docs/guide/clojure-compatibility.md`).

## Reader-level feature detection

let-go supports `:clj` and `:lg` reader conditionals (in addition to `:default`). Libraries can use `#?(:lg ... :clj ...)` to provide let-go-specific code paths.

Babashka-compatible libraries using `:bb` reader branches can be loaded in let-go by matching the `:bb` feature to avoid JVM-internal assumptions.

## Test suite results

let-go's implementation is verified against 232 test files from jank's clojure-test-suite:
- **5621 / 5621 assertions pass** under the `:clj` reader lens, as measured for v1.12.x and still the figure `README.md` carries at v1.13.0. It predates #863's `clojure.test` port and is worth re-measuring.
- **Zero failures, skips, or panics**.
- Coverage includes core functions, collection operations, destructuring, lazy sequences, protocols, and multimethods.

## Interop story

JAR loading and dynamic class loading are not supported; instead:

- **Pods** provide access to external libraries via the [Babashka pods protocol](../concepts/pods.md).
- **Go embedding** allows calling Go functions from let-go via `lginterop` and gogen-generated bindings.
- **System calls** (`os`, `syscall` namespaces) provide OS-level interop for shell, file I/O, and Linux syscalls.

# Citations

[1] **docs/guide/clojure-compatibility.md**: Comprehensive compatibility reference  
https://github.com/nooga/let-go/blob/main/docs/guide/clojure-compatibility.md

[2] **docs/clojure-compat-roadmap.md**: Compatibility roadmap and known gaps  
https://github.com/nooga/let-go/blob/main/docs/clojure-compat-roadmap.md

[3] **jank-lang/clojure-test-suite**: Test suite source  
https://github.com/jank-lang/clojure-test-suite

[4] **Pods** (this wiki)  
[../concepts/pods.md](../concepts/pods.md)

[5] **let-go** (this wiki)  
[../entities/let-go.md](../entities/let-go.md)

---

See also: [lginterop](../concepts/lginterop.md), [go-interop](../concepts/go-interop.md), [stack-vm](../concepts/stack-vm.md)
