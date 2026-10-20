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
  - "repo: nooga/let-go pkg/rt/core/test/tap.lg, pkg/rt/core/test.lg, pkg/clojuretest/testing.go, scripts/lg-test-go, docs/clojure-go-test.md, test/zz_compat_test.go, pkg/rt/core/check.lg @ b82588292b, 2026-10-19"
  - "doc: nooga/let-go docs/testing-and-conformance.md (lines 26-29, 72 still list lg test and JUnit output) @ b82588292b, 2026-10-19"
  - "spec: nooga/let-go docs/specs/clojure-test-conformance.md (status: planning; Sections 1, 12.3) @ b82588292b (777597bab, #793), 2026-10-19"
  - "pr: nooga/let-go#936 (AOT clojure.test bodies run through go test), #793 (clojure.test conformance spec), #863 (TAP reporter ported in cffc09e10); issue #929 still open per gh, 2026-10-19"
created: "2026-07-03"
updated: "2026-10-19"
status: active
---

## Testing and Conformance Strategy

[let-go](../entities/let-go.md) validates correctness in layers: a
`clojure.test`-compatible layer for user code, conformance measured against the
jank-lang clojure-test-suite, property testing, and CI-gated performance
guardrails.

This page was written in 2026-07 against a design document, in future tense
throughout. Most of it has since shipped. Each section below says what exists at
`b82588292b` (upstream main, 2026-10-19) and what is still only planned.

## Test Framework and CLI

**Shipped.** [#863](https://github.com/nooga/let-go/pull/863) replaced the
partial namespace with a real port: the report, assert, fixture and runner
contract, in `pkg/rt/core/test.lg`. `deftest`, `testing`, `is`, `are` and
`use-fixtures` are there, with `thrown?`, `thrown-with-msg?`, `run-test-var` and
`run-test` from #754 and #671, and #798 made `run-tests` restore the caller's
namespace instead of throwing.

The TAP reporter is ported too, as `clojure.test.tap` in
`pkg/rt/core/test/tap.lg` (added in the same #863 port, cffc09e10). It prints the
TAP plan, diagnostic, and ok/not-ok lines, and `with-tap-output` wraps a body so
its results print as TAP. It is a library namespace: no command-line flag selects
it.

**Experimental.** [#936](https://github.com/nooga/let-go/pull/936) added a second
route into `go test`. `scripts/lg-test-go` lowers each `deftest` body in one
namespace to Go (`bodies.go`) and emits a `clojure_test.go` wrapper;
`pkg/clojuretest/testing.go` runs the bodies as subtests of `TestClojure`, with
`:once` and `:each` fixtures honored and failures reported through Go's `testing`
package. Namespace helpers and the test framework still run
from embedded bytecode, so this is per-test Go execution, not a lowered namespace.
The generator accepts one namespace per run and runs sequentially; it replaces the
`clojure.test/report` binding, so custom reporters are outside its contract. The
adapter is documented as experimental in
[docs/clojure-go-test.md](https://github.com/nooga/let-go/blob/main/docs/clojure-go-test.md).

**Not shipped.** There is no `lg test` command: no namespace globs, `--watch`,
`--fail-fast` or `--seed`. A search of `cmd/` and `pkg/cli` finds no `test`
subcommand at `b82588292b`. The JUnit XML encoder the design called for does not
exist either: `git grep -i junit` over `pkg`, `test`, `cmd` and `scripts` is
empty. CI runs `go test` over the Go test packages
(`.github/workflows/go.yml`), not `lg test`. The upstream strategy document still
lists `lg test` and JUnit output as features
(`docs/testing-and-conformance.md`, lines 26–29 and 72); the code is the
reference here.

**A trap worth knowing.** Since #863, a bare `(run-tests)` runs only the
*current* namespace, which in a script that has just loaded its suites is
usually none of them. `run-tests` with no arguments defaults to `*ns*`
(`pkg/rt/core/test.lg`), so it reports zero tests and exits 0, and a green run can
mean nothing ran. `(run-all-tests)` is the one that walks every loaded namespace.
Tracked as [#929](https://github.com/nooga/let-go/issues/929), still open at
`b82588292b`.

## Conformance: The Clojure Test Suite

**Shipped.** `test/zz_compat_test.go` compiles upstream `.cljc` files through
let-go and runs their assertions, with the per-test timeout, memory cap and
panic recovery the design described.
`test/compat/clojure/core-test/portability.lg` supplies the predicates the
upstream tests expect. The namespace aliasing and resolver work that lets
upstream code load transparently is in place.

The `knownFailing` list exists and is **empty** — `var knownFailing =
map[string]bool{}` at `test/zz_compat_test.go:30`, unchanged at `b82588292b`. The
runner fails any test that passes while it is listed. That is the machine-readable
form of the 5621 / 5621 figure on [clojure compatibility](clojure-compat.md):
nothing is being excused. Both numbers predate #863's rewrite and are worth
re-measuring.

## Property Testing, Fuzzing, and Guardrails

**Shipped.** `pkg/rt/core/check.lg` is the `test.check`-style layer, and it is
substantial: 41 top-level `def`, `defn`, `defn-` and `defmacro` forms, including
the generator combinators, `gen-let`, `for-all` and `defprop`.

**Shipped, differently than planned.** The performance guardrails exist but not
as the benchstat-threshold-per-branch scheme described here. What runs is the
anchor-relative ratchet with a one-way baseline and deterministic allocation
bars — see [performance ratchet](../concepts/perf-ratchet.md), which is the
current reference for how regressions are actually gated.

**Unverified.** The reader fuzzing and VM-versus-AOT differential testing this
page projected were not checked for this pass.

## Phase 0–1 Acceptance Criteria

Kept as a record of what was aimed at. The `clojure.test` layer and the
conformance suite in CI are met. The TAP reporter is met as a library namespace.
The `lg test` CLI and JUnit XML output are not met, and nothing in the tree builds
them: the spec at `docs/specs/clojure-test-conformance.md` (status: planning,
#793) excludes `clojure.test.junit` and running kaocha or cognitect test-runner
end to end.

The spec also describes per-`deftest` Go subtests through the `report`
multimethod (its Section 12.3), with failures attributed to the deftest that
produced them. Throw-site positions wait on the trace work in Sections 3.5, 4.8,
4.10 and 5 of that spec. That bridge has not landed at `b82588292b`: the Go
harness in `test/language_test.go` still runs every namespace a file's load
defines or redefines a deftest in through one `run-tests` call and reads the
aggregate result. The #936 adapter reaches per-test subtests by a different route, generating
Go code rather than bridging the reporter.

# Citations

**Resource (Public)**: [docs/testing-and-conformance.md](https://github.com/nooga/let-go/blob/main/docs/testing-and-conformance.md) — framework, CI, and compatibility strategy.

**Also public**: [docs/clojure-test-suite.md](https://github.com/nooga/let-go/blob/main/docs/clojure-test-suite.md) — runner architecture, safety limits, the `knownFailing` list, and coverage prioritisation.

**Also public**: [docs/clojure-go-test.md](https://github.com/nooga/let-go/blob/main/docs/clojure-go-test.md) — the experimental `go test` adapter (#936).

**Also public**: [docs/specs/clojure-test-conformance.md](https://github.com/nooga/let-go/blob/main/docs/specs/clojure-test-conformance.md) — the `clojure.test` and `clojure.test.tap` specification (#793, status: planning).

**Code this page was re-grounded in** (the 2026-07 version cited two local paths under a gitignored directory, which a reader cannot follow):

- [pkg/rt/core/test.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/test.lg) — the `clojure.test` layer, including `run-tests` and `run-all-tests`.
- [pkg/rt/core/test/tap.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/test/tap.lg) — the `clojure.test.tap` reporter.
- [pkg/clojuretest/testing.go](https://github.com/nooga/let-go/blob/main/pkg/clojuretest/testing.go) and [scripts/lg-test-go](https://github.com/nooga/let-go/blob/main/scripts/lg-test-go) — the experimental `go test` adapter.
- [pkg/rt/core/check.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/check.lg) — the property-testing layer.
- [test/zz_compat_test.go](https://github.com/nooga/let-go/blob/main/test/zz_compat_test.go) — the conformance runner and its `knownFailing` list.

---

See also: [clojure compatibility](clojure-compat.md), [performance ratchet](../concepts/perf-ratchet.md)
