---
type: Reference
category: reference
title: "Testing & Clojure Conformance"
description: "How let-go validates correctness: the clojure.test layer #863 shipped, the jank conformance runner, property testing, and the performance guardrails — with what is still only planned marked as such."
tags: [clojure, tooling, runtime]
resource: "https://github.com/nooga/let-go/blob/main/docs/testing-and-conformance.md"
sources:
  - "doc: nooga/let-go docs/testing-and-conformance.md, docs/clojure-test-suite.md @ 36b13f79, 2026-09-20"
  - "repo: nooga/let-go pkg/rt/core/test.lg, pkg/rt/core/check.lg, test/zz_compat_test.go, test/compat/clojure/core-test/portability.lg @ 36b13f79, 2026-09-20"
  - "pr: nooga/let-go#863 (clojure.test ported), #754/#671 (thrown?, run-test-var), #798 (run-tests restores the caller's ns); issue #929 (bare run-tests runs nothing, open), 2026-09-20"
created: "2026-07-03"
updated: "2026-09-20"
status: active
---

## Testing and Conformance Strategy

[let-go](../entities/let-go.md) validates correctness in layers: a
`clojure.test`-compatible layer for user code, conformance measured against the
jank-lang clojure-test-suite, property testing, and CI-gated performance
guardrails.

This page was written in 2026-07 against a design document, in future tense
throughout. Most of it has since shipped. Each section below says what exists at
`36b13f79` and what is still only planned.

## Test Framework and CLI

**Shipped.** [#863](https://github.com/nooga/let-go/pull/863) replaced the
partial namespace with a real port: the report, assert, fixture and runner
contract, in `pkg/rt/core/test.lg`. `deftest`, `testing`, `is`, `are` and
`use-fixtures` are there, with `thrown?`, `thrown-with-msg?`, `run-test-var` and
`run-test` from #754 and #671, and #798 made `run-tests` restore the caller's
namespace instead of throwing.

**Not shipped.** There is no `lg test` command: no namespace globs, `--watch`,
`--fail-fast` or `--seed`, and `lg -h` lists nothing for it. The TAP and JUnit
XML encoders the design called for do not exist either — a search across `pkg/`
and `test/` finds neither format. CI consumes Go's own test output instead.

**A trap worth knowing.** Since #863, a bare `(run-tests)` runs only the
*current* namespace, which in a script that has just loaded its suites is
usually none of them: it reports zero tests and exits 0, so a green run can mean
nothing ran. `(run-all-tests)` is the one that walks every loaded namespace.
Tracked as [#929](https://github.com/nooga/let-go/issues/929), open.

## Conformance: The Clojure Test Suite

**Shipped.** `test/zz_compat_test.go` compiles upstream `.cljc` files through
let-go and runs their assertions, with the per-test timeout, memory cap and
panic recovery the design described.
`test/compat/clojure/core-test/portability.lg` supplies the predicates the
upstream tests expect. The namespace aliasing and resolver work that lets
upstream code load transparently is in place.

The `knownFailing` list exists and is **empty** — `var knownFailing =
map[string]bool{}`. That is the machine-readable form of the 5621 / 5621 figure
on [clojure compatibility](clojure-compat.md): nothing is being excused. Both
numbers predate #863's rewrite and are worth re-measuring.

## Property Testing, Fuzzing, and Guardrails

**Shipped.** `pkg/rt/core/check.lg` is the `test.check`-style layer, and it is
substantial: 41 enumerated concepts, the second-largest namespace under
`pkg/rt/core/` after `clojure.core` itself.

**Shipped, differently than planned.** The performance guardrails exist but not
as the benchstat-threshold-per-branch scheme described here. What runs is the
anchor-relative ratchet with a one-way baseline and deterministic allocation
bars — see [performance ratchet](../concepts/perf-ratchet.md), which is the
current reference for how regressions are actually gated.

**Unverified.** The reader fuzzing and VM-versus-AOT differential testing this
page projected were not checked for this pass.

## Phase 0–1 Acceptance Criteria

Kept as a record of what was aimed at. The `clojure.test` layer and the
conformance suite in CI are met; the `lg test` CLI with JUnit and TAP output is
not, and nothing currently in the tree is working toward it.

# Citations

**Resource (Public)**: [docs/testing-and-conformance.md](https://github.com/nooga/let-go/blob/main/docs/testing-and-conformance.md) — framework, CI, and compatibility strategy.

**Also public**: [docs/clojure-test-suite.md](https://github.com/nooga/let-go/blob/main/docs/clojure-test-suite.md) — runner architecture, safety limits, the `knownFailing` list, and coverage prioritisation.

**Code this page was re-grounded in** (the 2026-07 version cited two local paths under a gitignored directory, which a reader cannot follow):

- [pkg/rt/core/test.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/test.lg) — the `clojure.test` layer, including `run-tests` and `run-all-tests`.
- [pkg/rt/core/check.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/check.lg) — the property-testing layer.
- [test/zz_compat_test.go](https://github.com/nooga/let-go/blob/main/test/zz_compat_test.go) — the conformance runner and its `knownFailing` list.

---

See also: [clojure compatibility](clojure-compat.md), [performance ratchet](../concepts/perf-ratchet.md)
