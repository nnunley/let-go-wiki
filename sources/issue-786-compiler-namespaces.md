---
type: Source
category: source
title: "Compiler namespaces: consolidate IR, AOT orchestration, and the Go backend under lg.compiler (issue #786)"
description: "nnunley's proposal for the compiler's namespace architecture: lg.compiler, lg.compiler.ir.*, lg.compiler.backend.go, and lg.commands.compile, with a migration plan and acceptance criteria."
tags: [compiler, go, tooling, idea]
resource: "https://github.com/nooga/let-go/issues/786"
sources: ["issue: https://github.com/nooga/let-go/issues/786 and its comments, 2026-09-09", "pr: https://github.com/nooga/let-go/pull/735 (approval 2026-09-08, comments 2026-09-08 and 2026-09-09), 2026-09-09"]
created: "2026-09-05"
updated: "2026-09-09"
status: active
---

# Compiler namespaces: consolidate IR, AOT orchestration, and the Go backend under lg.compiler (issue #786)

Open issue by Norman Nunley (nnunley), filed 2026-09 against #735's proposed `lg.aotdriver` extraction. It argues that the compiler currently spans four seams that grew separately (`ir.*`, `gogen` behind its `!bootstrap` auxiliary embed, `scripts/lg-compile`, and the proposed `lg.aotdriver`) and that a permanent namespace layout should be settled before more compiler services are added.

## Key takeaways

- **Target shape:** `lg.compiler` (API and program-level orchestration), `lg.compiler.ir` and `lg.compiler.ir.passes.*`, `lg.compiler.backend.go` (the bootstrapped Go backend that `gogen` is meant to become), `lg.commands.compile` (CLI adaptation only).
- **`gogen` is not enrolled, it is bootstrapped:** moving Go emission under the compiler must first resolve the cold/hot lowering fixpoint and determinism constraints #557 documented.
- **Compatibility:** `scripts/lg-compile` stays as a shim until an explicit deprecation; `lg script.lg`, `lg -e`, and bare `lg` keep working; subcommands are not made mandatory.
- **Six migration steps** that may land as separate PRs but each preserve the whole destination.
- **Non-goals:** fixing lowering gaps, removing `lg-compile`, replacing the scripting CLI.
- **Refined on #735 (2026-09-02):** `lg.compiler` enrolls in the standard embedded and generated set immediately, no temporary auxiliary-embed exception; the shim stays; a contract test pins `EMIT-FAIL`.
- **#735 approved (2026-09-08)** at head `ab699061`. On bundle membership, which the issue does not cover, Norman said on 2026-09-09 he is fine with `gogen` and the compiler in the bundle and in the bootstrap universe.
- **Second inventory comment (2026-09-08):** step 5's surface is `lg.compiler/main-from-args` plus `exit-code`; step 3 must keep both bundle-skip prefixes as prefixes.

## Derived pages

[compiler-namespace-architecture](../ideas/compiler-namespace-architecture.md) · [generated-artifacts](../concepts/generated-artifacts.md) · [go-backend](../concepts/go-backend.md)

# Citations

[1] https://github.com/nooga/let-go/issues/786
