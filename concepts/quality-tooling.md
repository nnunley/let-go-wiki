---
type: Concept
category: concept
title: "Quality Tooling"
description: "The contributor-facing quality tools written in let-go itself: the comment linter and its six rules, the static complexity scorer, and spec-evidence for keeping a spec and its conformance tests in step."
tags: [tooling, compiler, runtime]
resource: "https://github.com/nooga/let-go/blob/main/scripts/lint.lg"
sources:
  - "repo: nooga/let-go scripts/lint.lg, scripts/quality.lg, scripts/quality/, scripts/spec-evidence.lg, scripts/lint-code-rules.edn @ 36b13f79, 2026-09-20"
  - "pr: nooga/let-go#836 (lint.lg), #870 (R1-R6 objective rules + code-verbosity catalog), #871 (complexity scorer), #861 (spec-evidence), #858/#890 (docs pages), 2026-09-20"
created: "2026-09-20"
updated: "2026-09-20"
status: active
---

# Quality Tooling

Three contributor-facing tools, all written in let-go and run through `lg`,
which makes them a working demonstration of the language as well as a gate.
They sit beside the [performance ratchet](perf-ratchet.md): that one guards
speed, these guard the source.

## `lint.lg` — comment abuse

```
lg scripts/lint.lg [paths...]                    # default: pkg scripts
lg scripts/lint.lg --edn [paths...]              # machine-readable findings
lg scripts/lint.lg --gate R1[,R2...] [paths...]  # exit non-zero on findings
```

**Report-only by default.** It never edits source, and exits non-zero only when
`--gate` names a rule that actually found something. A finding is a map
`{:file :line :end :kind :measure :evidence}`.

| Rule | What it flags |
|---|---|
| R1 | commented-out code (`.lg` only) |
| R2 | restatement — a comment that says what the code says |
| R3 | duplicated comment |
| R4 | comment density outlier |
| R5 | devlog phrase |
| R6 | comment churn, over a revision range |

**R1–R4 and R6 are objective**, computed from the source or the corpus with no
hand-curated wording. **R5 is the original phrase-list heuristic**, deliberately
segregated: it is reported separately and never gated, because a phrase list
only catches what someone thought of in advance.

R1 covers `.lg` files only, and the source is explicit that this is coverage
rather than a clean bill: a Go file is never flagged *and* never reported as
checked-and-clean for R1. Go analysis is planned as its own tool.

## `quality.lg` — static complexity scorer

```
lg scripts/quality.lg [--since DATE] [--go-cover FILE]
                      [--ci-run ID | --ci-seconds N] [--edn PATH] [--top N]
                      [--source-root PATH] [paths...]
```

Measures `.lg` and `.go` files and reports cost, duplication, a score, and
call-graph output. The implementation is split under `scripts/quality/`:
`cost.lg`, `dup.lg`, `forms.lg`, `graph.lg`, `diff.lg`, with the cost weights
in `cost-catalog.edn` rather than in code.

`--source-root` measures a tree as source even when it sits under `test/`, which
is what lets it be pointed at a fixture corpus.

## `spec-evidence.lg` — executable specs

```
LG_SOURCE_PATHS=scripts lg scripts/spec-evidence.lg <cmd> <spec.md> [args]
```

Subcommands: `lint`, `tangle`, `generate`, `run`, `render`, `accept`, `specs`.

It makes fenced code blocks in `docs/specs/*.md` executable, so a spec and its
conformance tests cannot silently drift apart. The `LG_SOURCE_PATHS=scripts`
prefix is load-bearing: without it the helper namespaces
(`spec-evidence.parse`, `spec-evidence.vocab`) do not resolve.

## Not covered here

Read off the tools' own usage and source rather than from running them across
the corpus. The calibration behind R2's and R4's thresholds, what the score in
`quality.lg` is on a scale of, and which of these run in CI versus locally are
all worth adding.
