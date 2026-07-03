---
type: Source
category: source
title: "Runtime Images and Stdlib Cache Design"
description: "Design specification for dumping/loading self-contained runtime images and precompiling the standard library for fast startup and reproducible deployments."
tags: [runtime, vm, compiler, bytecode]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/runtime-image-and-stdlib-cache.md"
sources: ["repo: nooga/let-go docs/design/runtime-image-and-stdlib-cache.md, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

## What This Source Is

Authoritative design document for runtime image serialization and caching in let-go. Specifies the mechanism for snapshotting bytecode, heap state, and namespaces to a binary image format, enabling cold-start performance, reproducible deployments, and embedded applications.

## Key Contributions

**Instant startup**: Images skip reader/analyzer/compiler phases on boot, eliminating heavy initialization.

**Image scope**: Captures namespaces, vars, functions/closures with bytecode, constant pools, and intern tables; excludes non-serializable host pointers (Go values), channels, OS handles, and goroutines.

**Layered architecture**: Base image (stdlib only) can be loaded independently; app-specific images layer atop without reloading stdlib.

**Host binding**: Extern placeholders for native functions resolved at load-time via a configurable `HostRegistry`, with validation of signatures and arity.

**Versioning and safety**: Images carry schema, runtime, and content hashes; loader rejects incompatible versions and treats images as untrusted input with hash/signature validation.

**Serialization strategy**: Persistent encodings (BPTR, HAMT) for collections; deterministic symbol/keyword interning rebuilt during load; no serialized hash caches.

## Derived pages

- [runtime-image](../concepts/runtime-image.md)

# Citations

Resource: https://github.com/nooga/let-go/blob/main/docs/design/runtime-image-and-stdlib-cache.md
