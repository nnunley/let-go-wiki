---
type: Source
category: source
title: let-go README
description: "Official project README documenting let-go's design, features, benchmarks, compatibility, and distribution methods."
tags: [clojure, runtime, compiler, reference, go]
resource: "https://github.com/nooga/let-go#readme"
sources: ["repo: nooga/let-go README.md, 2026-07-03"]
created: 2026-07-03
updated: 2026-07-03
status: stable
---

# let-go README

## What this source is

The official let-go project README, serving as the authoritative entry point. Covers project goals, implementation status, benchmarks against comparable Clojure runtimes (Babashka, Joker, go-joker, gloat, JVM), language compatibility (5621/5621 test assertions passing), compilation to bytecode/binaries/WASM, embedding in Go, nREPL support, and known limitations vs. Clojure JVM.

## Key takeaways

**let-go is a pragmatic Clojure dialect targeting Go environments.** It trades perfect JVM compatibility for portability: a 12MB native binary with 8.2ms cold startup (vs. Babashka's 17.7ms, Joker's 11.5ms, JVM's 360ms), passes the jank-lang test suite, and runs on Plan 9. Implements persistent data structures, lazy seqs, transducers, protocols, multimethods, BigInt, core.async, and Babashka pods. Go interop is two-way: define Go structs/functions/channels, invoke them from let-go; compile programs to standalone binaries or self-contained WASM web pages.

**Design pragmatism over purity.** No coordinated STM or async agents (`ref`/`agent` are atom-backed aliases); channels are real goroutines and always-blocking; regex uses re2 (not Java); numeric tower is simplified. Projects without external JVM dependencies (or willing to port them to Go interop) see idiomatic Clojure unmodified.

## Derived pages

[let-go](../entities/let-go.md) · [bytecode-compiler](../concepts/bytecode-compiler.md) · [wasm-compilation](../concepts/wasm-compilation.md) · [nrepl-in-browser](../ideas/nrepl-in-browser.md)

# Citations

- [https://github.com/nooga/let-go#readme](https://github.com/nooga/let-go#readme)
