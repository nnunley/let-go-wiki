---
type: Concept
category: concept
title: "Performance Ratchet"
description: "How let-go catches regressions without same-machine benchmarking: the anchor-normalized bench-ratchet, its one-way baseline, the deterministic allocation bars, the lowering-coverage and lowering-shape ratchets, and where each one gates."
tags: [tooling, vm, compiler, runtime]
resource: "https://github.com/nooga/let-go/blob/main/docs/perf/ratchet.md"
sources:
  - "doc: nooga/let-go docs/perf/ratchet.md (last-verified 2026-08-04), scripts/ir-stress.md @ 0911118, 2026-09-05"
  - "repo: nooga/let-go cmd/bench-ratchet, docs/perf/{baseline.json,ir-stress-baseline.edn}, .pre-commit-config.yaml, Makefile, .github/workflows/perf-timeline.yml @ 0911118, 2026-09-05"
  - "pr: nooga/let-go#561/#564 (median sampling), #740 (per-release baseline), #780 (deterministic rebaseline, Go 1.26.5 baseline, pre-push gate), #579 (lowering-shape ratchet), #795 (bench-baton, open), #794 (PrepareCall allocation-free, merged 2026-09-06 as 3ae0a08); issue #791 (the regression the gate caught), 2026-09-05"
created: "2026-09-05"
updated: "2026-09-06"
status: stable
---

# Performance Ratchet

let-go has three ratchets, and they share one rule: the bar only moves one way. A benchmark that gets faster tightens the baseline; a benchmark that gets slower fails the gate until someone explains it. The word covers a timing ratchet (`bench-ratchet`), a lowering-coverage ratchet (`ir-stress-gate`), and a lowering-shape ratchet (a test that pins instruction counts). All three run before a push, not only in CI.

## bench-ratchet: anchor-relative timing

The problem it solves is that CI does not run on the hardware developers benchmark on. `cmd/bench-ratchet` therefore reports every benchmark as a multiple of a frozen calibration loop, `BenchmarkRatchetAnchor` in `pkg/vm`, which has no allocations and no project code. That ratio is roughly stable within a CPU family, so a baseline captured on one machine still flags a regression on another, and `benchstat`'s two-runs-on-one-machine model is not needed for the gate (it still composes for same-machine investigation).

Two phases, separately invokable:

1. **capture** runs `go test -bench` per package and streams each result as one JSON line to a `.jsonl` file, fsynced as it goes, so a later benchmark that hangs cannot lose the earlier results.
2. **aggregate** normalizes against the anchor and writes `docs/perf/baseline.json`. `check`, `update`, and `show` are wrappers over capture then aggregate; `snapshot` writes an immutable timeline file instead.

The check is, per benchmark, `delta = current.ratio_to_anchor / baseline.ratio_to_anchor - 1`, with a default budget of 5%: over budget is a regression and a non-zero exit, under is improvement, a benchmark in the baseline but not the run is `MISSING`, and one in the run but not the baseline is `NEW`. Sampling discards warmup and takes the median (#561, #564), and the report warns when the anchor itself drifted.

The default scope is narrow on purpose: the anchor; the Clojure test-suite exec and total benchmarks under three variants (bytecode, IR-compiled bytecode, and `gogen_ir`); `BenchmarkIRCompile` under two; and `BenchmarkInitFromLGB`, the one `pkg/compiler` benchmark gated, for core-bundle decode and replay. The broad `pkg/compiler` and `pkg/bytecode` fleets are excluded so a slow compile change does not trip a runtime gate. `-full` adds the whole `pkg/vm` fleet for a manual deep dive.

### Deterministic bars

Allocations and bytes per operation do not depend on the machine, so they are gated as absolute bars against the global minimum across every profile in the baseline, at a fixed 2% (`allocBudget` in `cmd/bench-ratchet/main.go`), the bar #791 reports `IRCompile` bytes/op crossing. A forced rebaseline resets these bars too since #780; before that a `-force` update carried stale bars forward.

### The baseline and the ratchet

`baseline.json` (version 2) holds one profile per machine key: the anchor's sampled `ns_per_op`, and per benchmark the raw numbers for same-machine eyeballing plus `ratio_to_anchor`, which is what `check` compares. `make bench-ratchet-update` merges rather than overwrites: each `(benchmark, metric)` becomes the minimum of baseline and current, so a faster run is adopted, a slower one is pinned at the baseline and reported, a new benchmark is adopted as is, and a benchmark missing from the run is kept so a rename cannot release its bar. `-force` writes current numbers as they are; the doc's rule is that a forced rebaseline needs a paper trail and must not ride along with the change being measured.

The active baseline is seeded from CI (`seed-baseline`): the newest amd64 snapshot per explicit machine key, merged with the existing Apple M3 profile so local gating stays free of runner noise. Apple M1 virtual runners are excluded on purpose after #651 found 27% of their benchmark entries moving more than 10% between reps of identical code (4 to 5% on the amd64 runners); they fall back to deterministic-only gating. `docs/perf/historical/` holds one frozen file, `v1.8.0.json`; #740 added `perf-release-baseline.yml`, which freezes `historical/<tag>.json` on every `v*` tag through an auto-opened PR, and as of `0911118` no tag since has been frozen or backfilled. `-baseline docs/perf/historical/v1.8.0.json check` answers "how far have we drifted since that release" with no ratchet logic involved.

### Where it runs

| Where | What |
|---|---|
| pre-push (`.pre-commit-config.yaml`, `always_run`) | `make bench-ratchet` on every push, because a runtime, generated-bundle, or policy change can regress a metric with no benchmark file in the diff (#780) |
| PR CI, opt-in | `perf-pr.yml` runs the A/B only when the PR carries the `perf` label and touches `pkg/**` or `cmd/**` |
| `main` | `perf-timeline.yml` snapshots every non-docs push to the `perf-data` branch; `pages.yml` fetches that branch on deploy and renders the "are we fast yet" page with `cmd/perf-page` from the committed baseline, the historical files, and the timeline |

A run needs a quiet machine. `cmd/bench-baton` (#795, open at the time of writing) is a per-machine lease with an exclusive `bench` lane and a shared `build` lane, so a test suite running beside the ratchet cannot produce a number the gate mistakes for a regression.

### What it caught

#791 is the worked example. After #780 recaptured the baseline on 2026-09-02, the pre-push gate went red on `main` itself. Bisecting on an M3 attributed it: #727's `PrepareCall` allocates an argument slice, a frame, and a struct on every `reduce`, about 1,900 extra allocations per `BenchmarkIRCompile` iteration (+2.4% bytes/op, over the deterministic bar), and #723 and #730 each added several percent of time to both compiler benchmarks. #794 (merged 2026-09-06, 3ae0a08) removed the `PrepareCall` allocations for native fold loops. The same report recorded two false positives worth knowing: macOS Low Power Mode moved the anchor 74%, so `pmset -g | grep lowpowermode` is the first check when the anchor shifts on the same machine class; and the bytes/op bar is not architecture-dependent, since an amd64 build under Rosetta allocated the same as arm64.

## ir-stress-gate: lowering coverage

The second ratchet measures what the IR pipeline can lower, not how fast it runs. `scripts/ir-stress.lg` drives every shipped, test, and example `.lg` through a backend and buckets each `defn`; `docs/perf/ir-stress-baseline.edn` records the failure count (11 of 2,429 for the Go path when last captured on 2026-07-21) and `make ir-stress-gate` fails when failures grow or the corpus total drifts. The bytecode path has its own baseline and gate (`ir-stress-bytecode-gate`), added with #580. Rebaselining is tool-maintained (`make ir-stress-rebaseline`, never hand-edited) and only tightens; the file's own note says a loosening is always a real regression. It runs pre-push, and deliberately not in CI, because it takes about a minute. See [compile paths](compile-paths.md) for the modes and buckets.

## The lowering-shape ratchet

The third pins the shape of what the bytecode backend emits. `test/ir_lower_stack_discipline_test.lg` (#579) asserts upper bounds on instruction count and `DUP_NTH` count for two fixtures (`fib` at most 23 instructions and 4 `DUP_NTH`; a `loop`/`recur` sum at most 18 and 8; the direct compiler's 18 and 16 with no shuffle are the targets), and that ordinary var loads are re-emitted per use. Upper bounds rather than equalities, following the other two: an improvement passes with room, then the numbers tighten in the same commit.

## Citations

**Resource:** [docs/perf/ratchet.md](https://github.com/nooga/let-go/blob/main/docs/perf/ratchet.md): architecture, baseline format, check semantics, seeding, `-force` policy  
**Related:**
- [cmd/bench-ratchet](https://github.com/nooga/let-go/tree/main/cmd/bench-ratchet): the tool
- [docs/perf/baseline.json](https://github.com/nooga/let-go/blob/main/docs/perf/baseline.json) and [docs/perf/ir-stress-baseline.edn](https://github.com/nooga/let-go/blob/main/docs/perf/ir-stress-baseline.edn): the two committed baselines
- [.pre-commit-config.yaml](https://github.com/nooga/let-go/blob/main/.pre-commit-config.yaml): the `bench-ratchet` and `ir-stress-gate` pre-push stages
- [.github/workflows/perf-timeline.yml](https://github.com/nooga/let-go/blob/main/.github/workflows/perf-timeline.yml): timeline snapshots on `main`
- [scripts/ir-stress.md](https://github.com/nooga/let-go/blob/main/scripts/ir-stress.md): the coverage harness
- PRs and issues: [#561](https://github.com/nooga/let-go/pull/561), [#564](https://github.com/nooga/let-go/pull/564) sampling; [#740](https://github.com/nooga/let-go/pull/740) per-release baseline; [#780](https://github.com/nooga/let-go/pull/780) deterministic rebaseline and pre-push gate; [#579](https://github.com/nooga/let-go/pull/579) shape ratchet; [#795](https://github.com/nooga/let-go/pull/795) bench-baton; [#791](https://github.com/nooga/let-go/issues/791) the caught regression; [#651](https://github.com/nooga/let-go/issues/651) CI noise measurement

See also: [Compile Paths](compile-paths.md), [Stack VM](stack-vm.md), [IR Optimizations](ir-optimizations.md), [let-go](../entities/let-go.md)
