---
type: Reference
category: reference
title: "Testing & Clojure Conformance"
description: "How let-go validates correctness through unit tests, conformance suites, property testing, and performance guardrails."
tags: [clojure, tooling, runtime]
resource: "https://github.com/nooga/let-go/blob/main/docs/testing-and-conformance.md"
sources:
  - "/Users/ndn/development/let-go/docs/testing-and-conformance.md"
  - "/Users/ndn/development/let-go/docs/clojure-test-suite.md"
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

## Testing and Conformance Strategy

[let-go](../entities/let-go.md) is designed to validate correctness through a multi-layer testing approach: a `clojure.test`-compatible test layer for user code, conformance measured against the jank-lang clojure-test-suite (~230 core functions, ~5000 assertions), property testing with shrinking, and CI-gated performance benchmarks. The goal is to prove Clojure compatibility across core semantics, persistent data structures, seq behavior, and runtime stability.

## Test Framework and CLI

let-go will provide a `clojure.test`-compatible API (macros like `deftest`, `testing`, `is`, `are`, `use-fixtures`) with output formats including human-readable logs, TAP, and JUnit XML for CI integration. The `lg test` command will support namespace globs, file selection, `--watch` for file changes, `--fail-fast`, and `--seed` for randomized/property tests. Implementation targets core test macros under `pkg/rt/core/test.lg` with the runner in Go (`pkg/rt/lang.go`) for performance, exposing JUnit/TAP encoders to let-go code via native functions.

## Conformance: The Clojure Test Suite

let-go's conformance strategy targets running the [jank-lang/clojure-test-suite](https://github.com/jank-lang/clojure-test-suite), a cross-dialect test suite with ~105 test files and ~5000 assertions. The planned test runner (`test/zz_compat_test.go`) will compile upstream `.cljc` files through let-go and execute assertions, with safety guards: 5-second timeout per test, 512MB memory limit, and panic recovery. Portability shims in `test/compat/clojure/core-test/portability.lg` will provide predicates like `when-var-exists` and `thrown?` that the upstream tests expect. Namespace aliases (e.g., `clojure.test` → `test`) and resolver improvements (`.cljc` extension support, underscore→hyphen path mapping) will enable upstream code to load transparently.

The runner will track expected failures in a `knownFailing` list; tests that pass but are listed are flagged as "graduated" so contributors can remove them. When complete, the suite will track 105 files with pass/fail/skipped metrics to guide priority fixes (reader issues unlock the most assertions, followed by resolver fixes, then missing builtins and behavioral corrections).

## Property Testing, Fuzzing, and Guardrails

let-go is designed to include a minimal `test.check`-style property-testing library with generators and `prop/for-all` for properties like vector append/assoc invariants, HAMT idempotence, and equality/hash consistency. Planned fuzzing will occur at two levels: reader fuzzing with Go's `testing/fuzz` for literals and nested collections, and differential tests comparing VM vs Go AOT results on random inputs. Performance tests will use `go test -bench` microbenchmarks covering VM call arities, TCO recursion, vector/HAMT ops, numeric arithmetic, transducers, and image load time. Benchstat thresholds in CI will alert on >10% regressions; baselines will be stored per branch and refreshed with manual approval.

## Phase 0–1 Acceptance Criteria

The Phase 0–1 goals include: a working `clojure.test`-compatible layer and `lg test` CLI with human-readable and JUnit output; a conformance seed suite running in CI for core semantics (seq coercion, `count nil`, `conj` semantics, basic equality); initial property tests for vectors and numeric operations; and a bench harness wired with call-arity and numeric microbenchmarks. CI will run a matrix across macOS/Linux/Windows and the latest two Go versions, including `go vet`, `staticcheck`, unit/integration/property/fuzz tests, and benchmarks, with artifacts (JUnit XML, TAP logs, coverage, perf CSV) published for review.

# Citations

**Resource (Public)**: [docs/testing-and-conformance.md](https://github.com/nooga/let-go/blob/main/docs/testing-and-conformance.md) — Testing and Conformance — framework, CI, and compatibility strategy.

**Sources**:
- `/Users/ndn/development/let-go/docs/testing-and-conformance.md` — goals, test framework, conformance strategy, property testing, performance guardrails, CI integration, and Phase 0–1 acceptance.
- `/Users/ndn/development/let-go/docs/clojure-test-suite.md` — Clojure Test Suite workflow, runner architecture, safety, knownFailing list, coverage prioritization, and common pitfalls.
