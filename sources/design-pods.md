---
type: Source
category: source
title: Pods design
description: "Babashka-compatible external process integration via EDN-based RPC for script-friendly access to system APIs, databases, and tools."
tags: [interop, runtime, tooling, go]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/pods.md"
sources: ["repo: nooga/let-go docs/design/pods.md, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

## Pods — Babashka-compatible external process integration

This source proposes implementing Babashka-compatible pods to provide an industrial-strength extension mechanism without relying on Go plugins. Pods are external processes speaking a simple EDN-based RPC over stdio (or TCP). let-go acts as a host, enabling script-friendly access to system APIs, databases, and tools while staying safe and portable.

### Key takeaways

- **Protocol compatibility**: Pods follow the Babashka pod protocol with EDN-encoded, newline-delimited messages over stdio (or TCP). Operations include `:describe` (introspection), `:invoke` (function calls), and `:shutdown`.
- **Host architecture**: Pod manager spawns processes, sends descriptors, materializes proxy namespaces, and maintains goroutines for request/response routing.
- **Proxy functions**: Each described pod var becomes a let-go `Fn` that serializes args to EDN, sends an `:invoke` request with unique `:id`, awaits response, and maps results back to let-go values.
- **Data mapping**: Scalars and collections (vectors, lists, maps, sets) map 1:1 between EDN and let-go types; future tagged literals for extensions.
- **Concurrency & security**: Per-request contexts with timeouts; allowlist/denylist; resource limits on CPU, memory, and concurrent calls.
- **Developer ergonomics**: Host API via `pods/load`, `pods/unload`, `pods/list`; CLI helpers for `describe` and `run`.
- **MVP scope**: Load and invoke Babashka pods via stdio with structured args, error handling, and timeouts. Stretch goals include TCP, streaming, and binary/transit encoding.

## Derived pages

- [pods](../concepts/pods.md)

## Citations

- Babashka pod protocol (external standard; described in design)
- let-go [runtime](../concepts/runtime-image.md) value representation
- let-go [Go interop](../concepts/go-interop.md)
