---
type: Entity
category: entity
title: "let-go"
description: "A Clojure dialect with a bytecode compiler and stack VM, written in Go."
tags: [clojure, go, vm, wasm]
resource: "https://github.com/nooga/let-go"
sources: ["repo: nooga/let-go README, 2026-07-01", "repo: nooga/let-go README.md docs/guide/clojure-compatibility.md docs/guide/usage.md docs/guide/go-interop.md docs/guide/wasi.md docs/known-divergences.md pkg/vm go.mod @ b82588292b, 2026-10-20"]
created: "2026-07-01"
updated: "2026-10-20"
status: stable
---

# let-go

let-go is a Clojure dialect implemented as a bytecode compiler and stack-based
virtual machine in Go. The README describes it as a single ~13MB binary with
~10ms cold start and no JVM [2]. The README benchmark table (Apple M1 Pro)
reports 11.1ms startup for the VM binary, 10.7ms for the AOT binary, and 15.2MB
idle memory [2].

It passes the [jank-lang Clojure test suite](https://github.com/jank-lang/clojure-test-suite):
5621 of 5621 assertions pass across 232 files through the `:clj` reader lens,
with no known failures, compile skips, panic skips, or runtime skips [3].

It implements most of Clojure: persistent data structures, lazy seqs,
transducers, protocols, records, multimethods, core.async, and BigInt and
BigDecimal [2][3]. Go interop covers functions and structs [4] and channels [2].
The VM executes compiled bytecode on a stack; see the
[stack VM](../concepts/stack-vm.md) page. Specialized arithmetic and comparison
opcodes in `pkg/vm`, such as `OP_ADD` and `OP_LT`, take two operands from the
stack and leave one result, stack effect `[a b] -> [result]` [6]. Other opcodes
take inline int32 operands, such as `OP_LOAD_CONST` (index), `OP_JUMP` (offset),
and `OP_POP_N` (n) [6].

## Output forms

- **Bytecode:** `lg -c app.lgb app.lg` compiles a program to a `.lgb` file.
  `lg-runtime app.lgb` runs it with no reader, compiler, or resolver [9].
- **Standalone binary, bytecode-bundled:** `lg -b myapp -bundle-base lg-runtime app.lg`
  appends the bytecode to a copy of the runtime base [9].
- **Standalone binary, native:** `lg compile app.lg` builds a native executable
  through the Go backend. It needs a Go toolchain on `PATH`. Code that lowers runs
  as Go; code that does not lower stays on the VM [9].
- **WASM web app:** `lg -w site app.lg` writes `index.html`, a self-contained
  page of about 6MB with inlined, gzipped WASM. Programs that use the `term`
  namespace get terminal emulation through xterm.js [9].
- **WASI module:** `GOOS=wasip1 GOARCH=wasm go build` builds a headless WASI
  module. The REPL and terminal code are excluded from that target [5].

## Not implemented

let-go is not a drop-in replacement for JVM Clojure. It does not load JARs [2].
The gaps listed in [3] are:

- STM: `ref`, `dosync`, `alter`, and `commute` are atom-backed aliases, not
  coordinated STM.
- Agents: `agent`, `send`, and `send-off` are synchronous atom-backed aliases.
- Lazy seqs are unchunked.
- `deftype` supports protocol implementations but not JVM host methods. `reify`
  accepts an `Object` override of `toString`; `hashCode` and `equals` are accepted
  and ignored.
- No `clojure.spec`.
- No `subseq` or `rsubseq`. Sorted collections work; range queries do not.

The README also lists behavior that differs from JVM Clojure: a pragmatic numeric
tower, always-blocking channels, real goroutines for `go` blocks, and `re2`
regex rather than Java regex [2]. Intentional differences and temporary
mismatches are recorded in [known divergences](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/known-divergences.md) [8].

## Install

- Homebrew: `brew install nooga/tap/let-go` [2].
- Prebuilt binaries for Linux, macOS, and Plan 9 are on the GitHub Releases page [2].
- From source: `go install github.com/nooga/let-go@latest`. The README states
  Go 1.26+ [2]. The `go.mod` at b82588292b declares `go 1.27` with
  `toolchain go1.27.1` [7].

# Citations

[1] [let-go repository](https://github.com/nooga/let-go)

[2] [README.md at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/README.md)

[3] [docs/guide/clojure-compatibility.md at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/guide/clojure-compatibility.md)

[4] [docs/guide/go-interop.md at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/guide/go-interop.md)

[5] [docs/guide/wasi.md at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/guide/wasi.md)

[6] [pkg/vm/vm.go opcode definitions at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/vm/vm.go)

[7] [go.mod at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/go.mod)

[8] [docs/known-divergences.md at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/known-divergences.md)

[9] [docs/guide/usage.md at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/guide/usage.md)
