---
type: Source
category: source
title: "Benchmark Ratchet (docs/perf/ratchet.md)"
description: "The contributor doc for bench-ratchet: anchor-relative measurement, the capture and aggregate phases, what the baseline records, how check compares, when the pre-push gate runs, seeding from CI, the one-way update rule, the -force policy, and the BENCH_WRAP sleep guard."
tags: [tooling, vm, reference]
resource: "https://github.com/nooga/let-go/blob/main/docs/perf/ratchet.md"
sources: ["doc: https://github.com/nooga/let-go/blob/main/docs/perf/ratchet.md, 2026-09-05", "repo: nooga/let-go docs/perf/ratchet.md @ b82588292b, 2026-10-19", "repo: nooga/let-go cmd/bench-ratchet/seed.go, cmd/bench-ratchet/main.go @ b82588292b, 2026-10-19", "repo: nooga/let-go cmd/ratchet-scope/main.go, scripts/bench-ratchet-if-affected.sh, .pre-commit-config.yaml @ b82588292b, 2026-10-19", "repo: nooga/let-go Makefile:284-290 (BENCH_WRAP) @ b82588292b, 2026-10-19", "repo: nooga/let-go .github/workflows/perf-pr.yml @ b82588292b, 2026-10-19", "repo: nooga/let-go pkg/rt/core/ir/lower_go.lg @ b82588292b, 2026-10-19", "pr: nooga/let-go#952 (436b407d8), #911 (680c1328a), #930 (39b189efc), 2026-10-19"]
created: "2026-09-05"
updated: "2026-10-19"
status: active
---

# Benchmark Ratchet (docs/perf/ratchet.md)

Active doc (upstream `last-verified` 2026-10-03; this page was checked against let-go `b82588292b`, 2026-10-19). Its one idea: report every benchmark as a multiple of a frozen CPU loop so a baseline captured on one machine still flags regressions on another.

## Key takeaways

- **Phases:** capture streams `.jsonl` (fsynced per line); aggregate normalizes and writes `baseline.json`; `check`/`update`/`show` wrap them; `snapshot` writes immutable timeline files.
- **Check:** `delta = current.ratio / baseline.ratio - 1`, 5% default budget (`-budget`); `MISSING` and `NEW` flagged.
- **Scope:** the default gate (`cmd/bench-ratchet/main.go`, default case) is the anchor (`BenchmarkRatchetAnchor` in `pkg/vm`, untagged, bytecode only), `BenchmarkClojureTestSuite` (bytecode, `ir_bytecode` and `aot_native` under `gogen_ir`, plus the three `total_*` variants filtered to `BenchmarkClojureTestSuiteCompileAndRun`), `pkg/ir` `BenchmarkIRCompile` (bytecode and `gogen_ir`), and the `pkg/compiler` `BenchmarkInitFromLGB` startup job (bytecode, untagged). `-full` runs the whole `pkg/vm` fleet under `gogen_ir`, plus the same suite, IR compile and startup-init jobs. The six b.N=1 `BenchmarkClojureTestSuite*` variants are observational only and are filtered out of `update` and seeding.
- **Build tags:** the default is `-tags gogen_ir`, which compiles the lowered-to-Go VM into the benchmark binary. `-tags ""` gives a vanilla build.
- **gogen_ir numbers:** the doc says these numbers exercise the natively-lowered IR passes, and that the dispatch is guarded by `TestIRBenchDispatchesNativeUnderTag` (`pkg/ir/ir_compile_dispatch_test.go`). Lowered code reaches a cross-namespace or `clojure.core` callee through a cached var (`rt.CachedVarFnEC`) and passes one to four arguments as parameters, so the call builds no argument slice (`invoke-by-arity` in `pkg/rt/core/ir/lower_go.lg`, [5]). A call with five or more arguments still builds one, and that is the remaining per-call allocation in lowered calls.
- **Pre-push gate:** the ratchet is a blocking `pre-push` hook, but it runs only when the pushed range can change what it measures (#952, `436b407d8`). The trigger is the Go dependency closure of the benchmarked packages, computed by `cmd/ratchet-scope` with `go list -deps -test` under each build-tag configuration. Its `benchmarkRoots` are `pkg/vm`, `pkg/ir`, `pkg/compiler` and `test`, so edits under `pkg/compiler` trigger the gate even though the doc calls that package out of scope (the `BenchmarkInitFromLGB` startup job roots it); plus `pkg/rt/generated.sums` and `generated.manifest`, `go.mod`, `go.sum`, `mise.toml`, `test/compat/` and the clojure-test-suite submodule; plus any deleted file under a directory that still holds measured files. Editing `test/*.lg` files outside `test/compat/`, `docs/`, `cmd/bench-ratchet`, the baseline file or `scripts/` does not trigger it. The gate fails toward running: an undeterminable range, a pushed tip that is not the checkout, an empty change set, a build failure, or an unrecognised decision all run the benchmark. Pushing a different ref, or pushing with uncommitted changes, also runs it. To preview a change set, use `jj diff --summary --from 'fork_point(@ | main@upstream)' --to @ | go run ./cmd/ratchet-scope -v -summary`. The `ir-stress-gate` hook still runs unconditionally.
- **BENCH_WRAP:** every `make` target that runs `bench-ratchet` prefixes the command with `$BENCH_WRAP` (#911, `680c1328a`). It defaults to `caffeinate -is` where `caffeinate` exists, so the machine cannot idle-sleep mid-capture and move the anchor. `BENCH_WRAP= make bench-ratchet` runs bare. `systemd-inhibit` is deliberately not the Linux default. The wrapper reaches Make targets only; direct `go run ./cmd/bench-ratchet` calls and `scripts/recapture-release-baseline.sh` are unwrapped.
- **PR check:** CI runs the A/B on pull requests that carry the `perf` label, and on any PR number through manual `workflow_dispatch` (`.github/workflows/perf-pr.yml`, job `if:` at line 45). The `pull_request` path filter covers `pkg/**`, `cmd/**` and the workflow file itself; the `workflow_dispatch` trigger has no path filter. The workflow header calls the job informational and says it never fails the PR, but only the check step is guarded: it ends in `|| true` (line 131). The ref-resolution and base/head bench steps (lines 69, 105, 120) have no such guard, so a failure there fails the job, and the PR comment job runs only when the bench job succeeds (line 175). The PR job runs the `pr-fast` profile: the stable `pkg/vm` micro-benchmark families plus the anchor. The suite and IR compile run in the fuller profiles on `main`.
- **Baseline:** seeded from a window of the five most recent CI amd64 snapshots per machine key (`-seed-window`, default 5), reduced to a median in ratio space (#684, 2026-09-07; before that, the newest snapshot alone). A key with fewer than three snapshots (`-seed-min-window`) is skipped, and a snapshot whose ratios sit more than 5% off its window is rejected (`-seed-coherence-tolerance`). A benchmark present in fewer than half the surviving snapshots is not seeded. M3 is preserved locally, and M1 virtual is excluded after #651. `update` takes the per-metric minimum.
- **`-force`:** `-force update` bypasses the ratchet for this host's timing only. `allocs/op` and `bytes/op` are still gated on both this machine's bar and the newest row any profile carries (#930, `39b189efc`). A worse deterministic value is kept and printed under `NOT ACCEPTED`. Recording it needs `-accept-deterministic`, which should have a paper trail. The doc says not to bundle a baseline update with the change being measured.
- **Stale spots:** at `b82588292b` the upstream JSON example still names `pkg/api` for the anchor, but `BenchmarkRatchetAnchor` lives in `pkg/vm/bench_ratchet_anchor_test.go`, so the example is still wrong. The `perf-timeline.yml` error noted on 2026-09-05 is fixed upstream: the doc now says that workflow does not touch the static page, and that `pages.yml` builds it.

## Derived pages

[perf-ratchet](../concepts/perf-ratchet.md)

# Citations

[1] https://github.com/nooga/let-go/blob/main/docs/perf/ratchet.md
[2] https://github.com/nooga/let-go/pull/952 (pre-push scope, 436b407d8)
[3] https://github.com/nooga/let-go/pull/911 (BENCH_WRAP, 680c1328a)
[4] https://github.com/nooga/let-go/pull/930 (forced update gated on the deterministic bar, 39b189efc)
[5] https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/lower_go.lg (invoke-by-arity)
