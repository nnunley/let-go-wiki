---
type: Source
category: source
title: "Native-entry lowering gate and frame fix (PR #729)"
description: "nnunley's gate proving that --entry-frame binaries execute lowered entries as generated Go, and the frame defect it found: a single-file program's empty namespace table left every namespace-level var undefined."
tags: [compiler, go, tooling]
resource: "https://github.com/nooga/let-go/pull/729"
sources: ["pr: https://github.com/nooga/let-go/pull/729, 2026-09-05", "repo: nooga/let-go pkg/cli/cli.go, pkg/rt/core/ir/passes/entry_frame.lg @ 36b13f79, 2026-09-20", "issue: nooga/let-go#796 closed by pr #902, 2026-09-20", "repo: nooga/let-go pkg/rt/core/ir/passes/entry_frame.lg, pkg/rt/run.go, pkg/cli/cli.go, pkg/cli/compile.go @ b82588292b, 2026-10-19", "repo: nooga/let-go Makefile (native-entry-gate, test), test/e2e/native_entry_ast_gate_test.go, test/native-entry/ @ b82588292b, 2026-10-19", "repo: nooga/let-go commits ed0754504 (#729), f36a8c0bb (#902), fbc7d838f (#959), 45b7cd8cf (#1008) @ b82588292b, 2026-10-19", "issue: nooga/let-go#783 (lifted_fn fixture), 2026-10-19"]
created: "2026-09-05"
updated: "2026-10-19"
status: active
---

# Native-entry lowering gate and frame fix (PR #729)

Merged 2026-08-13. Before it, an `--entry-frame` binary could silently drop every namespace-level definition and nothing in the test suite would notice.

## Key takeaways

- **The defect:** for a single-file program `lg -c` emits a bundle with an empty NS table, so `LoadProgramNamespaces` iterated nothing; the binary was correct only when every reachable callee lowered to a direct call, and a VM-backed callee resolved to a nil var.
- **The fix:** `entry_frame.lg` emits `rt.RunProgramMainChunk(unit)` after `LoadProgramNamespaces` (`pkg/rt/core/ir/passes/entry_frame.lg` at b82588292b, lines 452-470), idempotent so a bundle with NS entries still runs top-level forms once. `RunProgramMainChunk` returns early when `MainChunk` is one of the `NSOrder` chunks (`pkg/rt/run.go`, b82588292b).
- **The gate:** the gate is `TestNativeEntryASTGate` in `test/e2e/native_entry_ast_gate_test.go`. It globs `test/native-entry/*.lg`; each fixture needs an exact `.expect` and a structural `.goexpect.json`, and a missing sidecar is a hard failure, not a skip. It proves the fixture's `defn` exists as a Go function of the expected shape exactly once (the same test's "evidence 1", at b82588292b).
- **Invocation changed:** `make native-entry-gate` is a deprecated delegate since [nooga/let-go#959](https://github.com/nooga/let-go/pull/959) (commit fbc7d838f, 2026-09-26). It prints a notice and runs `go test -run 'TestNativeEntryASTGate|TestJankSuiteDirectABIGeneratedGo' -short=false ./test/e2e/`. The replacement is `make test SHORT=false PKG=./test/e2e RUN='TestNativeEntryASTGate|TestJankSuiteDirectABIGeneratedGo'` (Makefile, b82588292b, around lines 396-399). The gate is `testing.Short()`-gated, so it must run with `-short=false`. The discovery and sidecar rules above are unchanged at b82588292b.
- **Corpus:** `test/native-entry/` now holds 10 fixtures (`closure_capture`, `conditional_closure`, `guarded_entry`, `int_arith`, `lifted_fn`, `loop_carried_closure`, `loop_join_closure`, `runtime_eval`, `toplevel_effect`, `vm_backed`), each with the three committed files described in `test/native-entry/README.md`. The fixture count is a source-level count; the gate's pass/fail result is not confirmed here.
- **Follow-up:** [nooga/let-go#783](https://github.com/nooga/let-go/issues/783) reported a related nil var for lambda-lifted `__lifted0` names in entry-frame binaries. The source now carries that case as the `lifted_fn` fixture (`test/native-entry/lifted_fn.lg`; its `.goexpect.json` note says the lifted var exists only once the program's overrides are installed after its main chunk runs). The source does not record whether #783 itself is closed; check the issue.
- **Follow-up:** #796 rode on the replay this PR added. Those top-level forms include the guard `docs/guide/usage.md` recommends, `(when-not *compiling-aot* (-main))`, and the var is false at runtime, so an `--entry-frame` binary built from a guarded program entered the entry once on the VM and once natively. [nooga/let-go#902](https://github.com/nooga/let-go/pull/902) closed it in v1.13.0 (`git tag --contains f36a8c0bb` lists v1.13.0). At b82588292b the frame's bytecode is compiled by `compileLGBSubprocess`, which runs `lg -c <dst> -entry-frame-entry <entry> <src>` (`pkg/cli/compile.go:155`). The flag is validated in `pkg/cli/cli.go:600` and the generated frame invokes the entry itself, as the comment at `entry_frame.lg:465-466` states. The #902 commit message describes a `RunProgramMainChunkForEntryFrame` helper that sets `*compiling-aot*` during the replay; that helper does not appear in the tree at b82588292b, so the commit message and the code disagree and the code is the reference here. The empty-NS-table framing above is single-file only: once a program requires another namespace, `MainChunk` is one of the `NSOrder` chunks, the top level runs inside `LoadProgramNamespaces`, and `RunProgramMainChunk` returns early, so either half of the prologue can be the one that runs the guard.
- **Follow-up:** [nooga/let-go#1008](https://github.com/nooga/let-go/pull/1008) (commit 45b7cd8cf, 2026-10-12) changed the frame's boot. The frame had booted through `rt.BootCore` and linked no compiler, so a lowered `-main` that called `eval` panicked and `load-string` or a run-time `require` could not work. The frame now imports `pkg/compiler`, whose `init()` boots core and installs `eval`. The `runtime_eval` fixture covers this path. The commit reports a stripped binary growing by 385 KB (2.7%); that figure is from the commit message, not re-measured here.

## Derived pages

[go-backend](../concepts/go-backend.md) · [compile-paths](../concepts/compile-paths.md)

# Citations

[1] https://github.com/nooga/let-go/pull/729
[2] https://github.com/nooga/let-go/pull/902
[3] https://github.com/nooga/let-go/pull/959
[4] https://github.com/nooga/let-go/pull/1008
[5] https://github.com/nooga/let-go/issues/783
