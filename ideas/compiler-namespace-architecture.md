---
type: Idea
category: idea
title: "Compiler Namespace Architecture (lg.compiler)"
description: "Norman's proposal to consolidate the IR, AOT orchestration, and the Go backend under lg.compiler, with lg.commands.compile as a thin CLI adapter: the seams it names, the migration order, and the acceptance criteria."
tags: [compiler, idea, tooling, go]
resource: "https://github.com/nooga/let-go/issues/786"
sources:
  - "issue: nooga/let-go#786 (open, nnunley) and mparrett's comments there (2026-08-28 inventory, 2026-09-08 migration notes); nnunley's review and comments on #735 (2026-08-26, 2026-09-02, approval 2026-09-08, bundle answer 2026-09-09); mparrett's corrected boot measurement on #735 (2026-09-08); #596, #425, #557 as related work; #735 verified against the decisions at head ab699061, 2026-09-09"
created: "2026-09-05"
updated: "2026-09-09"
status: active
---

# Compiler Namespace Architecture (`lg.compiler`)

Issue #786 (Norman, open as of 2026-09-05) is a proposal, not shipped code: it argues that the compiler's namespaces should be settled before more compiler services are added. It is recorded here as an idea because it names the target shape that several in-flight pieces are supposed to converge on.

## The seams as they are

The compiler implementation spans four places that grew separately:

- `ir.*` owns the IR, analyses, optimization passes, and the lowering pipeline (see [IR pipeline](../concepts/ir-pipeline.md)).
- `gogen` owns Go source construction and emission, embedded as an auxiliary source behind the `!bootstrap` tag (see [generated artifacts](../concepts/generated-artifacts.md) and [Go backend](../concepts/go-backend.md)).
- `scripts/lg-compile` owns program-level AOT orchestration (see [lg-compile](../concepts/lg-compile.md)).
- #735 extracts that orchestration into a namespace of its own as groundwork for #596, the first-class `lg compile` command. It proposed `lg.aotdriver`; after the review below it now lands as `lg.compiler`.

The objection was not to the extraction but to the destination: `lg.aotdriver` would have been a second permanent compiler architecture beside `ir.*`, and it treated `gogen`'s auxiliary embed as where the Go backend lives. That embed solved shipped-binary self-containment (#557); it was never meant to be the permanent home of a backend that is intended to become bootstrapped.

## The proposed shape

| Namespace | Role |
|---|---|
| `lg.compiler` | stable compilation API and program-level orchestration |
| `lg.compiler.ir` | IR model and construction |
| `lg.compiler.ir.passes.*` | analyses, optimization, legalization, lowering passes |
| `lg.compiler.backend.go` | the bootstrapped Go backend, today `gogen` plus the Go-emission code |
| `lg.commands.compile` | a thin CLI adapter: parse arguments, call `lg.compiler`, map results to diagnostics and exit status |

`scripts/lg-compile` stays as a compatibility shim over the same API while external users depend on its path, output, and exit-code contracts. The existing top-level modes (`lg script.lg`, `lg -e`, bare `lg`) are explicitly preserved; subcommands are not made mandatory.

## Migration order

1. Inventory every consumer of `ir.*` and `gogen`: generated Go, bootstrap manifests, tests, scripts, downstream tools.
2. Define the `lg.compiler` API boundary and move program-level AOT orchestration behind it.
3. Migrate `ir.*` to `lg.compiler.ir.*`, with compatibility namespaces only where the inventory finds supported external consumers that cannot move atomically.
4. Move Go emission under `lg.compiler.backend.go` and complete the intended `gogen` bootstrap path. The issue is specific that this is not enrolling the current file in the bootstrap universe: the cold/hot lowering fixpoint and determinism constraints #557 documented have to be resolved first.
5. Add `lg.commands.compile` for #596.
6. Regenerate and verify every persisted compiler artifact the moves touch.

Each slice can land separately, but each must preserve the complete destination rather than narrowing to the current auxiliary-embed architecture.

## Acceptance criteria (abridged)

Program-level AOT exposed through `lg.compiler` and nowhere else; IR namespaces under `lg.compiler.ir.*`; Go generation under `lg.compiler.backend.go` and part of the bootstrap design; `lg.commands.compile` containing only CLI adaptation; `scripts/lg-compile` keeping its contract until an explicit deprecation; script, one-liner, and REPL invocation unchanged; cold/hot bootstrap output deterministic; generated manifests regenerated intentionally and passing their content gates; default and `bootstrap` suites green; cross-build and AOT end-to-end matrices green; any temporary compatibility namespace carrying tracked removal criteria.

## The decisions on #735 (2026-08-26 and 2026-09-02)

The issue was written against Matt's #735, and Norman's review there is where the direction was actually set, in two comments:

- **2026-08-26:** reusable program compilation belongs behind `lg.compiler`; IR implementation under `lg.compiler.ir.*`; `lg.commands.compile` stays a thin adapter. The broader migration and the `gogen` bootstrap can be follow-ups, but the PR must not establish `lg.aotdriver` as the permanent seam or treat the auxiliary `!bootstrap` embed as the destination.
- **2026-09-02, "Architecture decision":** enroll `lg.compiler` immediately in the standard embedded and generated namespace set (`EmbeddedNSNames` plus the genmanifest source specs), with no temporary auxiliary-embed exception; keep `scripts/lg-compile` as the compatibility shim; add the promised contract test pinning `EMIT-FAIL` stdout and its non-fatal exit status; then rebase and rerun the default, `bootstrap`, AOT, and native-entry checks.

So the one exception in the tree today, `gogen`'s auxiliary embed, is not to be copied: a new compiler namespace goes into the bootstrap universe from the start. What remains gated on the fixpoint work is moving `gogen` itself, not `lg.compiler`.

#735 was revised to match, Norman approved it on 2026-09-08, and at head `ab699061` it satisfies both. The driver is `lg.compiler` at `pkg/rt/core/lg/compiler.lg`; `EmbeddedNSNames` walks `core/` only, so living there is what enrolls it, and the genmanifest sweep picks it up from the same location. `pkg/rt/aotdriver/` is gone. `gogen` stays outside `core/` and so stays out of `EmbeddedNSNames`: the PR drops its `!bootstrap` build gate so lgbgen can *resolve* it while compiling `lg.compiler`, which is not the same as enrolling it, and leaves step 4's fixpoint work untouched.

One decision the issue does not cover is bundle membership, which is a separate axis from embedded-source enrollment. On `main`, `cmd/lgbgen`'s `isIRBundleSkipped` keeps `ir.*` out of the bytecode bundle (see [IR pipeline](../concepts/ir-pipeline.md)); #735 renames it `isBundleSkippedTool` and adds `lg.compiler`, both families matched by prefix so the `lg.compiler.ir.*` rename in step 3 does not silently drop the exclusion. Both load from embedded source on demand. Whether to bundle the driver eagerly instead was put to Norman on #735, and the numbers behind the question changed on 2026-09-08: the 23 ms boot figure from 2026-09-02, which also sits in `docs/design/go-aot-backend.md`, did not reproduce and was withdrawn. Measured interleaved on the current head, bundling takes the driver's require closure with it (the `ir.*` pipeline and `gogen`, 937 to 2,164 chunks) and costs about 3.2 times the boot, 1.9 ms to 6.0 ms median on a quiet host, inside the 8 ms budget there and over it on a loaded one. So eager bundling is a few milliseconds and a gate question, not a categorical failure, and it reverses the `ir.*` skip as a side effect. Norman answered on 2026-09-09 that he is fine with `gogen` and the compiler in the bundle, and in the bootstrap universe, and had removed them only for the size bump at the time. The PR has not yet moved on that answer.

Matt's step-1 inventory (comment on #786, 2026-08-28, against `0003a0bb`): 33 `ir.*` namespaces under `pkg/rt/core/ir/`, 58 `.lg` files outside that tree referencing one, 64 Go files referencing `core/ir` or `gogen`, and 137 manifest lines naming `ir` paths, so the manifest moves with the rename rather than after it. A second comment (2026-09-08) gives step 5 its starting point, `lg.compiler/main-from-args` plus `exit-code` being the whole surface `lg.commands.compile` takes over, and warns that step 3 can silently regress boot time if either prefix in the bundle skip is narrowed to an exact name during the move; the boot figure quoted in that comment is the withdrawn one.

## Non-goals

Fixing existing lowering or optimization gaps in the migration; removing `scripts/lg-compile` as part of the rename; replacing the scripting CLI with mandatory subcommands.

## Citations

- [nooga/let-go#786](https://github.com/nooga/let-go/issues/786): the proposal, with the step-1 inventory in its comments
- [nooga/let-go#735](https://github.com/nooga/let-go/pull/735): the review and the two decision comments
- Related: [#735](https://github.com/nooga/let-go/pull/735), [#596](https://github.com/nooga/let-go/issues/596), [#425](https://github.com/nooga/let-go/issues/425), [#557](https://github.com/nooga/let-go/pull/557)

See also: [Compile Paths](../concepts/compile-paths.md), [Self-hosting AOT](self-hosting-aot.md), [Master Plan Roadmap](master-plan-roadmap.md), [let-go](../entities/let-go.md)
