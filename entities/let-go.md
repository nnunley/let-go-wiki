---
type: Entity
category: entity
title: "let-go"
description: "A Clojure dialect with a bytecode compiler and stack VM, written in Go."
tags: [clojure, go, vm, wasm]
resource: "https://github.com/nooga/let-go"
sources: ["repo: nooga/let-go README, 2026-07-01"]
created: "2026-07-01"
updated: "2026-07-01"
status: stable
---

# let-go

let-go is a Clojure dialect implemented as a bytecode compiler and stack-based
virtual machine in Go. It produces a single ~12MB binary with ~8ms cold start,
no JVM, and passes the jank-lang Clojure test suite. It supports AOT compilation
to standalone binaries and self-contained WASM web pages, two-way Go interop, and
most of Clojure (persistent data structures, lazy seqs, transducers, protocols,
records, multimethods, core.async, BigInts).

See the [stack VM](../concepts/stack-vm.md) for how compiled bytecode executes.

# Citations

[1] [let-go repository](https://github.com/nooga/let-go)
