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
  - "repo: nooga/let-go scripts/lint.lg, scripts/lint-code-rules.edn, scripts/quality.lg, scripts/quality/, scripts/spec-evidence.lg, Makefile @ b82588292b, 2026-10-19"
  - "pr: nooga/let-go#917 (make lint runs lint-comments), #941 (quality.lg --generated, make quality-aot), 2026-10-19"
  - "repo: nooga/let-go test/lint_lg_test.go, test/spec_evidence_test.go, .github/workflows/go.yml, scripts/quality/score.lg, scripts/quality/report.lg @ b82588292b, 2026-10-19"
  - "run: lg dev (b825882) at nooga/let-go b82588292b, 2026-10-20 (quality.lg usage and --generated runs)"
created: "2026-09-20"
updated: "2026-10-19"
status: active
---

# Quality Tooling

Three contributor-facing tools, all written in let-go and run through `lg`,
which makes them a working demonstration of the language as well as a gate.
They sit beside the [performance ratchet](perf-ratchet.md): that one guards
speed, these guard the source.

## `lint.lg` — comment abuse

```
lg scripts/lint.lg [paths...]                       # default: pkg scripts
lg scripts/lint.lg --edn [paths...]                 # machine-readable findings
lg scripts/lint.lg --gate KIND[,KIND...] [paths...] # exit non-zero on findings
lg scripts/lint.lg --churn RANGE [paths...]         # R6 measures added comments over a git range
```

**Report-only by default.** It never edits source, and exits non-zero only when
`--gate` names a finding kind that actually found something. A finding is a map
`{:file :line :end :kind :measure :evidence}`.

`--gate` takes finding kinds, not rule numbers. Only four kinds are
gate-eligible (`gateable-kinds` in `scripts/lint.lg`): `commented-out-code`
(R1), `restatement` (R2), `duplicated-comment` (R3) and `comment-density-outlier`
(R4). Naming any other kind, including `R1`, is accepted but printed as a
`note: --gate ignored` line, because those findings cannot fail a run.
`make lint-comments` runs the report with no gate; `make lint` runs it next to
`golangci-lint` (#917). The Makefile notes that CI lints Go through the
golangci-lint action rather than through this target.

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
only catches what someone thought of in advance. R6 is also not gate-eligible:
its gate note says it has no calibrated threshold, so it is reported only.

R1 covers `.lg` files only, and the source is explicit that this is coverage
rather than a clean bill: a Go file is never flagged *and* never reported as
checked-and-clean for R1. Go analysis is planned as its own tool. The Makefile
also records a known false negative for R1: a commented-out form with a prose
line above it is missed (#873), so the R1 count is a floor.

**Code verbosity** is a separate pass, run by the driver as the seventh rule
group, that is not one of the six comment rules. It matches `.lg` forms against
the catalog in `scripts/lint-code-rules.edn`, which is data, not code: each
entry has a `:pattern` and a `:replace`, and a symbol starting with `?` is a
metavariable. The catalog has 14 entries, among them `redundant-not-empty`,
`first-next` and `apply-str-interpose`. Adding a pattern needs no change to
`lint.lg`. Like R1, these findings come only from `.lg` files, and the report
says so. They are advisory and cannot be gated.

## `quality.lg` — static complexity scorer

```
LG_SOURCE_PATHS=scripts lg scripts/quality.lg [--since DATE] [--go-cover FILE]
                      [--ci-run ID | --ci-seconds N] [--edn PATH] [--top N]
                      [--source-root PATH] [--generated] [paths...]
```

The `LG_SOURCE_PATHS=scripts` prefix is needed as written. Without it, the script fails with `error: unable to load namespace quality.cost` (exit 1) at `b82588292b`; with it, the script runs (run: lg dev (b825882) at nooga/let-go b82588292b, 2026-10-20). The Makefile sets the same variable at `Makefile:658`.

Measures `.lg` and `.go` files and reports cost, duplication, a score, and
call-graph output. The implementation is split under `scripts/quality/`:
`cost.lg`, `dup.lg`, `forms.lg`, `graph.lg`, `diff.lg`, `inputs.lg`, `lex.lg`,
`metrics.lg`, `report.lg`, `score.lg`, `terms.lg` and `touched.lg`, with the
cost weights in `cost-catalog.edn` rather than in code.

By default only VCS-tracked files are measured, so a scratch file cannot move
the score. The report is deterministic for a given commit, working copy and
set of inputs, and the header pins those inputs (`scripts/quality.lg`).

The score is debt. Each metric is charged 0 when it is at or better than its
`good` threshold, and more debt the further it moves toward `bad`. The
`DEBT` figure is lower-is-better, with 0 as perfect and 1 as worst. It is the
weighted mean of terms that are each a share in [0, 1], so it is bounded
(`corpus-score` in `scripts/quality/score.lg`; `scripts/quality/report.lg`
prints the same bound). Nothing saturates, so moving the worst code always
moves the number. The "no upper clamp" wording in the `score.lg` header
(`scripts/quality/score.lg`, lines 7 and 109) predates `corpus-score`; it describes
the uncalled `penalty` function, not the composite. The `quality.lg` header
(`scripts/quality.lg`, line 16) calls DEBT "unbounded above", which is stale:
`corpus-score` is a weighted mean of shares in [0, 1], so the composite is bounded.

`--source-root` measures a tree as source even when it sits under `test/`, which
is what lets it be pointed at a fixture corpus.

`--generated` measures generated Go and `.lg` output instead of source. It
defaults to `pkg/rt/core_go_lowered`, but that tree is gitignored and was not present in the checkout used for the run (`generate` had not produced it). With no path argument the run found no files (`quality: no source files under pkg/rt/core_go_lowered`, exit 2), so pass the path explicitly: `LG_SOURCE_PATHS=scripts lg scripts/quality.lg --generated pkg/rt/core_go_lowered` (exit 0, 44 generated files). The omitted terms also depend on the path: that command omitted `:comment-debt`, `:dead`, `:defects`, `:testing` and `:uncovered`, while `--generated pkg/rt/core` omitted the first four and still showed `uncovered 1.000`. Generated mode omits the source-history and
testing terms, along with dead-code and comment-debt: those terms are left nil
(`scripts/quality.lg`, the `:generated` branches). The DEBT figure is still
computed from the terms that remain, renormalized over what is present.
Combining it with a git range (`--base`/`--head`) is an error, because
generated files have no Git baseline (`scripts/quality.lg`, #941).

Two make targets wrap the tool (`Makefile`). `make quality` runs the source
report and reads `QUALITY_SINCE` (default: 180 days back), `QUALITY_GO_COVER`,
`QUALITY_CI_SECONDS`, `QUALITY_EDN` and `QUALITY_TOP`. `make quality-aot`
depends on `generate` and passes `--generated`, so the emitter's output is
measured after it is rebuilt (#941).

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
the corpus. Two questions are answered by source and need no run: the score is
lower-is-better, with 0 as perfect and 1 as worst, and the composite is bounded.
On CI, a `git grep` of `.github/` at `b82588292b` finds no reference to
`lint.lg` or `quality.lg`, so neither runs as a CI step of its own. CI does
reach two of the three tools through the Go lane's `go test ./...`
(`.github/workflows/go.yml`): `test/lint_lg_test.go` executes `scripts/lint.lg`,
and `test/spec_evidence_test.go` executes `scripts/spec-evidence.lg`, neither
behind a skip guard. Whether CI reaches `quality.lg` was not traced. What is still open is the calibration
behind R2's and R4's thresholds (R4 uses the 95th percentile of the corpus, but
its printed value is only seen by running the tool), and what a score in
`quality.lg` means in practice. Both need a run of the tools across the corpus.
