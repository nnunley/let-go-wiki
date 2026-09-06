---
type: Source
category: source
title: "IR pipeline dynamic vars (design reference)"
description: "The single index of every ^:dynamic var the IR compile and lowering pipeline reads: compilation-mode knobs, pass toggles, cross-package lowering control, per-compile state, and how to verify a var change with the ir-stress harness."
tags: [compiler, reference, tooling]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/ir-dynamic-vars.md"
sources: ["doc: https://github.com/nooga/let-go/blob/main/docs/design/ir-dynamic-vars.md, 2026-09-05"]
created: "2026-09-05"
updated: "2026-09-05"
status: active
---

# IR pipeline dynamic vars (design reference)

Design reference added in #555 (last-verified 2026-07-19). The pipeline is configured almost entirely through dynamic vars scattered across `core.lg`, `passes/pipeline.lg`, `passes/inline.lg`, `passes/fusion.lg`, `passes/typeinfer.lg`, and `lower_go.lg`; only `*strict-structured?*` has an environment seed. The page is the index.

## Key takeaways

- **Mode control:** `*ir-compile*`, `*ir-compile-verbose*`, `*ir-compile-fallback-log*`, `*target*` (`:bytecode` or `:go`).
- **Cost of `*ir-compile*`:** pays back only on allocation-bound work (5 to 12 times fewer allocations, about 13% wall-clock, break-even near 64 runs on persistent-map); a net loss on compute-bound code. Figures from a single-machine gctrace proxy, directional not a contract.
- **Pass toggles:** `*enable-fusion*` (on, measured about 20% fewer allocations across the test suite), `*enable-inline*` (off), `*max-unroll*`, `*typeinfer-max-drains*`, `*strict-structured?*`, `*direct-calls-disabled?*`, `*pass-trace*`.
- **Cross-package lowering:** `*emit-exported-wrappers*`, `*cross-pkg-registry*`, `*wrapper-target-names*`, `*export-name-overrides*`, `*deftype-ctor-types*`.
- **Verification:** any default flip is a coverage change until `make ir-stress` / `ir-stress-gate` / `jank-stress` / `parity-full` say otherwise; diff bucket tallies, rebaseline with the tool, never hand-edit the EDN.

## Derived pages

[compile-paths](../concepts/compile-paths.md) · [ir-optimizations](../concepts/ir-optimizations.md) · [go-backend](../concepts/go-backend.md)

# Citations

[1] https://github.com/nooga/let-go/blob/main/docs/design/ir-dynamic-vars.md
