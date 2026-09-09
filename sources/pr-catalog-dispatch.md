---
type: Source
category: source
title: "Catalog-driven dispatch (PRs #612, #666, #667, #712)"
description: "nnunley's refactors that moved per-op and per-form facts into single-source catalogs with load-time coherence checks, and closed the accessor seam around the IR function's shape."
tags: [compiler, bytecode, go]
resource: "https://github.com/nooga/let-go/pull/612"
sources:
  - "pr: https://github.com/nooga/let-go/pull/612, 2026-09-05"
  - "pr: https://github.com/nooga/let-go/pull/666, 2026-09-05"
  - "pr: https://github.com/nooga/let-go/pull/667, 2026-09-05"
  - "pr: https://github.com/nooga/let-go/pull/712, 2026-09-05"
created: "2026-09-05"
updated: "2026-09-05"
status: active
---

# Catalog-driven dispatch (PRs #612, #666, #667, #712)

Four PRs by Norman Nunley under the consolidation epic #268, merged 2026-07-22 to 2026-08-12.

## Key takeaways

- **#612:** `local-carrying?` as a catalog column, reified infer facets with `:try` lowering re-homed, and a generated `opByKeywordExact` string switch: canonical `OpByKeyword` from 57 ns to 2.1 ns and allocation-free.
- **#667:** the 14 special-form heads catalogued in `form_heads.lg`; `build-list` dispatches by catalog lookup; `free-vars` and `captures-of` derive membership from it; bidirectional load-time coherence check that names the missing form. Corpus at 99.55%, parity 6311 assertions identical.
- **#666:** `function-needs-rt?` consolidated into a per-op contribution rule (`op-contributes-rt?`) with gates that go red if either conditional is flattened.
- **#712:** thirteen sites that read `(:insts @f)` / `(:blocks @f)` moved onto accessors (`all-insts`, `raw-blocks`, `all-types` added); no `@f` outside the data layer; the intern-block trap documented; `ir.passes.legalize` given its missing `(:require [ir.data])`.

## Derived pages

[op-catalog](../concepts/op-catalog.md) · [ir-representation-roadmap](../ideas/ir-representation-roadmap.md)

# Citations

- [PR #612 — catalog-driven op dispatch](https://github.com/nooga/let-go/pull/612)
- [PR #666 — per-op runtime contribution rules](https://github.com/nooga/let-go/pull/666)
- [PR #667 — catalog-driven form-head dispatch](https://github.com/nooga/let-go/pull/667)
- [PR #712 — IR function accessors](https://github.com/nooga/let-go/pull/712)
