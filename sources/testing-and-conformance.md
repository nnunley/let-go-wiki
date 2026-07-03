---
type: Source
category: source
title: Testing and Conformance
description: Framework, CI, and conformance strategy for testing let-go's clojure.test API, conformance suite, property testing, performance benchmarks, and CI integration.
tags: [clojure, tooling, runtime, reference]
resource: "https://github.com/nooga/let-go/blob/main/docs/testing-and-conformance.md"
sources: ["repo: nooga/let-go docs/testing-and-conformance.md, 2026-07-03", "repo: nooga/let-go docs/clojure-test-suite.md, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

## What is this source

The **Testing and Conformance** documents define let-go's testing strategy across three layers:

1. **Test Framework**: A `clojure.test`-compatible API (deftest, testing, is, are, use-fixtures) with a `lg test` CLI supporting namespace globs, --watch mode, JUnit/TAP output, and test selectors (focus/skip).

2. **Conformance Suite**: A curated subset of `clojure.core` behavior ported to let-go-compatible tests, with imports from Babashka/Joker test suites where semantics overlap. The suite covers reader/printer (EDN roundtrips), collections (vectors, maps, sets), seq tower, transients/transducers, numeric edge cases, and round-trip tests with runtime images and Go AOT embedding.

3. **Clojure Test Suite Integration**: The [jank-lang/clojure-test-suite](https://github.com/jank-lang/clojure-test-suite) as a git submodule tests ~230 clojure.core functions with ~5000 assertions. The test runner (`test/zz_compat_test.go`) iterates `.cljc` files, compiles through let-go, and reports results. Key safety features: 5s timeouts, 512MB memory guards, panic recovery, and a `knownFailing` list that auto-checks for graduated tests.

## Key takeaways

- **Familiar testing UX**: Users write tests in `clojure.test` style; the framework uses Go encoders (JUnit, TAP) for CI performance rather than re-implementing in let-go.

- **Conformance by scope**: Rather than emulate all of Clojure, the strategy publishes a spec of supported subset and deviations, imports battle-tested test cases, and uses property testing and fuzzing to catch edge cases.

- **High-value fix prioritization**: Reader fixes unlock the most test files (number literals, reader conditionals, symbolic values); then namespace/resolver fixes; then missing builtins (ranked by assertions unlocked); then behavioral fixes. The workflow doc provides diagnostic queries to rank blockers.

- **Safety and determinism**: Property tests use seeding; benchmarks enforce >10% regression thresholds; CI matrix spans macOS/Linux/Windows and Go versions; fuzz smoke tests run on PRs.

- **Gotchas documented**: BigDecimal M suffix parsed as Float, PersistentSet incorrectly implements Seq, nth bounds return nil (can't throw), drop/drop-while nil returns nil not (), reader conditionals need balanced-delimiter counting for dialect-specific syntax.

## Derived pages

- [testing-conformance](../references/testing-conformance.md)

# Citations

- **Testing framework & conformance strategy**: [docs/testing-and-conformance.md](https://github.com/nooga/let-go/blob/main/docs/testing-and-conformance.md)
- **Clojure test suite workflow & pitfalls**: [docs/clojure-test-suite.md](https://github.com/nooga/let-go/blob/main/docs/clojure-test-suite.md)
