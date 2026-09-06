---
type: Source
category: source
title: "Native-entry lowering gate and frame fix (PR #729)"
description: "nnunley's gate proving that --entry-frame binaries execute lowered entries as generated Go, and the frame defect it found: a single-file program's empty namespace table left every namespace-level var undefined."
tags: [compiler, go, tooling]
resource: "https://github.com/nooga/let-go/pull/729"
sources: ["pr: https://github.com/nooga/let-go/pull/729, 2026-09-05"]
created: "2026-09-05"
updated: "2026-09-05"
status: active
---

# Native-entry lowering gate and frame fix (PR #729)

Merged 2026-08-13. Before it, an `--entry-frame` binary could silently drop every namespace-level definition and nothing in the test suite would notice.

## Key takeaways

- **The defect:** for a single-file program `lg -c` emits a bundle with an empty NS table, so `LoadProgramNamespaces` iterated nothing; the binary was correct only when every reachable callee lowered to a direct call, and otherwise panicked on a nil var.
- **The fix:** `entry_frame.lg` emits `rt.RunProgramMainChunk(unit)` after `LoadProgramNamespaces`, idempotent so a bundle with NS entries still runs top-level forms once.
- **The gate:** `make native-entry-gate` discovers `test/native-entry/*.lg`; each fixture needs an exact `.expect` and a structural `.goexpect.json`, and a missing sidecar fails rather than skips; it proves the fixture's `defn` exists as a Go function of the expected shape exactly once.
- **Follow-up:** #783 reports a related nil var for lambda-lifted `__lifted0` names in entry-frame binaries.

## Derived pages

[go-backend](../concepts/go-backend.md) · [compile-paths](../concepts/compile-paths.md)

# Citations

[1] https://github.com/nooga/let-go/pull/729
