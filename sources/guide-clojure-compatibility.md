---
type: Source
category: source
title: Guide — Clojure Compatibility
description: Comprehensive reference documenting let-go's Clojure dialect compatibility, including passing test suite results, supported standard namespaces, unimplemented features, and behavioral differences from JVM Clojure.
tags: [clojure, runtime, reference]
resource: "https://github.com/nooga/let-go/blob/main/docs/guide/clojure-compatibility.md"
sources:
  - "repo: nooga/let-go docs/guide/clojure-compatibility.md, 2026-07-03"
created: 2026-07-03
updated: 2026-07-03
status: stable
---

# Clojure Compatibility Guide

Guide documenting let-go's relationship to JVM Clojure: a compatible dialect rather than a drop-in replacement. Establishes compatibility via conformance testing against jank-lang's test suite (5621/5621 assertions passing across 232 files), then catalogs supported and missing features, and behavioral divergences.

## Key takeaways

- **Conformance**: 5621 assertions pass with the `:clj` reader lens; no known failures, compile skips, panic skips, or runtime skips
- **Standard namespaces**: `clojure.core`, `clojure.string`, `clojure.set`, `clojure.walk`, `clojure.edn`, `clojure.pprint`, `clojure.test`, and `clojure.core.async` are broadly supported; additional namespaces (`io`, `http`, `json`, `transit`, `os`, `System`, `syscall`, `pods`) extend capability beyond JVM baseline
- **Key omissions**: STM coordination (`ref`, `dosync`), asynchronous agents, chunked sequences, custom tagged literals, Java-style `deftype` host methods, `Spec`, and sorted-collection range queries (`subseq`, `rsubseq`)
- **Behavioral shifts**: Numeric tower is pragmatic (int64, float64, BigInt, ratios, BigDecimal); base arithmetic throws on overflow; regex uses Go flavor (re2); `go` blocks are real goroutines (not IOC); channels always block

## Derived pages

- [clojure-compat](../references/clojure-compat.md)

# Citations

- nooga/let-go: [Clojure compatibility and differences](https://github.com/nooga/let-go/blob/main/docs/guide/clojure-compatibility.md)
