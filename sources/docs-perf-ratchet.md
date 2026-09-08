---
type: Source
category: source
title: "Benchmark Ratchet (docs/perf/ratchet.md)"
description: "The contributor doc for bench-ratchet: anchor-relative measurement, the capture and aggregate phases, what the baseline records, how check compares, seeding from CI, the one-way update rule, and the -force policy."
tags: [tooling, vm, reference]
resource: "https://github.com/nooga/let-go/blob/main/docs/perf/ratchet.md"
sources: ["doc: https://github.com/nooga/let-go/blob/main/docs/perf/ratchet.md, 2026-09-05"]
created: "2026-09-05"
updated: "2026-09-08"
status: active
---

# Benchmark Ratchet (docs/perf/ratchet.md)

Active doc (last-verified 2026-08-04). Its one idea: report every benchmark as a multiple of a frozen CPU loop so a baseline captured on one machine still flags regressions on another.

## Key takeaways

- **Phases:** capture streams `.jsonl` (fsynced per line); aggregate normalizes and writes `baseline.json`; `check`/`update`/`show` wrap them; `snapshot` writes immutable timeline files.
- **Check:** `delta = current.ratio / baseline.ratio - 1`, 5% default budget; `MISSING` and `NEW` flagged.
- **Scope:** narrow by default (anchor, suite, IR compile); `-full` adds the `pkg/vm` fleet; the doc warns that `gogen_ir` numbers show native dispatch working, not native being fast, because lowered code still boxes most calls.
- **Baseline:** seeded from a window of the five most recent CI amd64 snapshots per machine key, reduced to a median in ratio space (#684, 2026-09-07; before that, the newest snapshot alone), M3 preserved locally, M1 virtual excluded after #651; `update` takes the per-metric minimum; `-force` needs a paper trail and must not ride with the change being measured.
- **Stale spots noticed on 2026-09-05, still present at `a6763e77`:** the JSON example names `pkg/api` for the anchor (it is `pkg/vm`), and the Components table says `perf-timeline.yml` regenerates the page (it is `pages.yml`).

## Derived pages

[perf-ratchet](../concepts/perf-ratchet.md)

# Citations

[1] https://github.com/nooga/let-go/blob/main/docs/perf/ratchet.md
