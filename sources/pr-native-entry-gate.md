---
type: Source
category: source
title: "Native-entry lowering gate and frame fix (PR #729)"
description: "nnunley's gate proving that --entry-frame binaries execute lowered entries as generated Go, and the frame defect it found: a single-file program's empty namespace table left every namespace-level var undefined."
tags: [compiler, go, tooling]
resource: "https://github.com/nooga/let-go/pull/729"
sources: ["pr: https://github.com/nooga/let-go/pull/729, 2026-09-05", "repo: nooga/let-go pkg/cli/cli.go, pkg/rt/core/ir/passes/entry_frame.lg @ 36b13f79, 2026-09-20", "issue: nooga/let-go#796 closed by pr #902, 2026-09-20"]
created: "2026-09-05"
updated: "2026-09-20"
status: active
---

# Native-entry lowering gate and frame fix (PR #729)

Merged 2026-08-13. Before it, an `--entry-frame` binary could silently drop every namespace-level definition and nothing in the test suite would notice.

## Key takeaways

- **The defect:** for a single-file program `lg -c` emits a bundle with an empty NS table, so `LoadProgramNamespaces` iterated nothing; the binary was correct only when every reachable callee lowered to a direct call, and otherwise panicked on a nil var.
- **The fix:** `entry_frame.lg` emits `rt.RunProgramMainChunk(unit)` after `LoadProgramNamespaces`, idempotent so a bundle with NS entries still runs top-level forms once.
- **The gate:** `make native-entry-gate` discovers `test/native-entry/*.lg`; each fixture needs an exact `.expect` and a structural `.goexpect.json`, and a missing sidecar fails rather than skips; it proves the fixture's `defn` exists as a Go function of the expected shape exactly once.
- **Follow-up:** #783 reports a related nil var for lambda-lifted `__lifted0` names in entry-frame binaries.
- **Follow-up:** #796 rode on the replay this PR added. Those top-level forms include the guard `docs/guide/usage.md` recommends, `(when-not *compiling-aot* (-main))`, and the var is false at runtime, so an `--entry-frame` binary built from a guarded program entered the entry once on the VM and once natively. #902 closed it in v1.13.0 by compiling the frame's bytecode with `-entry-frame-entry`, which omits the selected entry call. The empty-NS-table framing above is single-file only: once a program requires another namespace, `MainChunk` is one of the `NSOrder` chunks, the top level runs inside `LoadProgramNamespaces`, and `RunProgramMainChunk` returns early, so either half of the prologue can be the one that runs the guard.

## Derived pages

[go-backend](../concepts/go-backend.md) · [compile-paths](../concepts/compile-paths.md)

# Citations

[1] https://github.com/nooga/let-go/pull/729
