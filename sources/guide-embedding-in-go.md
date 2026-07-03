---
type: Source
category: source
title: "Embedding let-go in Go"
description: "Guide to embedding let-go as a scripting layer in Go programs, with struct roundtripping, channel integration, and function interop."
tags: [go, interop, reference]
resource: "https://github.com/nooga/let-go/blob/main/docs/guide/embedding-in-go.md"
sources: ["repo: nooga/let-go docs/guide/embedding-in-go.md, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

# Embedding let-go in Go

This guide documents how let-go integrates cleanly as a scripting layer within Go programs via the [go-interop](../concepts/go-interop.md) layer.

## What the source is

An official let-go guide covering practical embedding patterns: defining Go values and functions via the `api` package, executing let-go code against Go data, and roundtripping Go structs and channels through the VM.

## Key takeaways

- **VM initialization**: `api.NewLetGo()` bootstraps a runtime context; `Def()` binds Go values and functions into the let-go namespace.
- **Struct integration**: Registered Go structs become records in let-go; unmodified values unbox back to Go types for free via field accessors like `:name`.
- **Channel first-class**: Go `chan` and `vm.Chan` integrate directly into `go`, `<!`, and `>!` primitives for async coordination.
- **Function calls**: Go functions become callable from let-go expressions with automatic type marshaling.

The guide anchors practical [go-interop](../concepts/go-interop.md) patterns and points to the full test suite in `pkg/api/interop_test.go`.

## Derived pages

- [go-interop](../concepts/go-interop.md)

# Citations

Resource: https://github.com/nooga/let-go/blob/main/docs/guide/embedding-in-go.md
