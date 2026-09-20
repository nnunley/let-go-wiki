---
type: Reference
category: reference
title: "Clojure Compatibility"
description: "Where let-go IS and ISN'T compatible with Clojure JVM: known limitations, feature parity, and behavioral differences."
tags: [clojure, lisp, runtime]
resource: "https://github.com/nooga/let-go/blob/main/docs/guide/clojure-compatibility.md"
sources: ["docs/guide/clojure-compatibility.md", "docs/clojure-compat-roadmap.md", "repo: nooga/let-go docs/known-divergences.md, test/map_order_test.lg @ ebd9a7bd, 2026-09-09", "pr: nooga/let-go#770 (data readers), #762 (reify Object), #758 (invokable symbols), #840 (Math/* JVM semantics), #841 (canonical dot form), #901 (Thread/currentThread, %n), #843 (split), #854 (edn reads data), #839 (*unchecked-math*), #787 (StringBuilder), #820 (json string keys), #855 (line-seq errors), #711 (clojure.data), #668 (clojure.repl), #863 (clojure.test) all merged for v1.13.0, 2026-09-20", "lg -e transcripts on lg 1.13.0 (369e2a69): every behaviour in the JVM-interop and numerics sections re-probed, plus require of every core namespace short and clojure.* name, 2026-09-20"]
created: "2026-07-02"
updated: "2026-09-20"
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
| `clojure.edn` | `read`, `read-string`; reads data rather than code since #854 |
| `clojure.pprint` | `pprint`, `cl-format` |
| `clojure.test` | `deftest`, `is`, `testing`, `are`, fixtures; #863 replaced the partial namespace with the report, assert, fixture and runner contract |
| `clojure.data` | `diff` (structural projection, #711) |
| `clojure.repl` | `doc` and friends, with a Var-metadata bundle round trip (#668) |
| `async` | Channels, `go`/`go-loop`, `alts!`, `mult`/`pub`, `pipe`/`merge`/`split` (real goroutines, not IOC). Required as `[async ...]`; `clojure.core.async` does not resolve |
| `io` | Polymorphic readers/writers, `slurp`/`spit`, lazy line-seq, encoding, URLs, `with-open`, `resource` |
| `http` | Ring-style server and client, streaming responses |
| `json` | `read-json`, `write-json` (float-preserving, record-aware); since #820 a string map key is written as text, so `{"key" "value"}` emits `{"key":"value"}` rather than the double-quoted EDN reading |
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
| **`*default-data-reader-fn*`** | `*data-readers*` landed in #770 and is honoured by `read-string`, `load-string` and ordinary compilation; there is still no catch-all, so a tag with no entry returns its form unchanged rather than erroring |
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
