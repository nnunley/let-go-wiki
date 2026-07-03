---
type: Reference
category: reference
title: "Clojure Compatibility"
description: "Where let-go IS and ISN'T compatible with Clojure JVM: known limitations, feature parity, and behavioral differences."
tags: [clojure, lisp, runtime]
resource: "https://github.com/nooga/let-go/blob/main/docs/guide/clojure-compatibility.md"
sources: ["docs/guide/clojure-compatibility.md", "docs/clojure-compat-roadmap.md"]
created: "2026-07-02"
updated: "2026-07-02"
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
| `clojure.edn` | `read`, `read-string` |
| `clojure.pprint` | `pprint`, `cl-format` |
| `clojure.test` | `deftest`, `is`, `testing`, `are`, fixtures |
| `clojure.core.async` | Channels, `go`/`go-loop`, `alts!`, `mult`/`pub`, `pipe`/`merge`/`split` (real goroutines, not IOC) |
| `io` | Polymorphic readers/writers, `slurp`/`spit`, lazy line-seq, encoding, URLs, `with-open`, `resource` |
| `http` | Ring-style server and client, streaming responses |
| `json` | `read-json`, `write-json` (float-preserving, record-aware) |
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
| **Custom tagged literals** | Built-in `#uuid` and `#inst` work; unknown tags read as payload; `*data-readers*` / `*default-data-reader-fn*` not implemented |
| **Java-style `deftype`/`reify` method bodies** | Protocol implementations work; JVM host methods do not |
| **`clojure.spec`** | Not ported |
| **`subseq`/`rsubseq`** | Sorted collections work; range queries don't |

## Behavioral differences

### Concurrency and async

- `<!` and `<!!` are identical; same for `>!` and `>!!` (Go channels always block).
- `go` blocks are real goroutines, not IOC state machines (cheaper, can call blocking ops directly).

### Numerics

- Tower includes `int64`, `float64`, `BigInt`, ratios, and `BigDecimal` without JVM's full primitive/class model.
- Base integer `+`/`-`/`*`/`inc`/`dec` throw on overflow; use `+'`/`-'`/`*'`/`inc'`/`dec'` for BigInt-promoting exact math.

### String processing and regex

- Regex is Go flavor (`re2`), not Java regex.
  - Supports most common patterns.
  - Lacks lookaround, backreferences, named capture groups, possessive quantifiers.
  - Linear-time execution; no ReDoS risk (unless using extended regex engine).

### Sequence operations

- `concat*` (used internally by quasiquote) is eager; user-facing `concat` is lazy.

## Reader-level feature detection

let-go supports `:clj` and `:lg` reader conditionals (in addition to `:default`). Libraries can use `#?(:lg ... :clj ...)` to provide let-go-specific code paths.

Babashka-compatible libraries using `:bb` reader branches can be loaded in let-go by matching the `:bb` feature to avoid JVM-internal assumptions.

## Test suite results

let-go's implementation is verified against 232 test files from jank's clojure-test-suite:
- **5621 / 5621 assertions pass** under the `:clj` reader lens.
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
