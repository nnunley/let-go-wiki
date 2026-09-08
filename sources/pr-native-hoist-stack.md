---
type: Source
category: source
title: "The //lg:native hoist stack (PRs #627, #639, #640, #641)"
description: "nnunley's four-PR stack that turned inline core primitives into annotated Go functions with generated registrars, then generalized the registrar per package and added a provenance manifest for selective regeneration."
tags: [runtime, go, interop, tooling]
resource: "https://github.com/nooga/let-go/pull/639"
sources: ["pr: https://github.com/nooga/let-go/pull/639, 2026-09-05"]
created: "2026-09-05"
updated: "2026-09-05"
status: active
---

# The //lg:native hoist stack (PRs #627, #639, #640, #641)

A stack by Norman Nunley, merged between 2026-07-27 and 2026-08-16. #627 (alias resolution in `LookupOrRegisterNSNoLoad`) was closed in favour of the same fix landing inside #639.

## Key takeaways

- **#639, hoist 222 primitives:** a codemod (`cmd/hoist-natives`) lifted 222 of 292 inline closures in `lang.go` into named `//lg:native` functions; the rest were skipped by a five-category safety analysis. Also the runtime-free `lgprimgen` generator, `LG_REGPRIM_DEBUG` and `LG_GUARD_DEBUG` diagnostics, and the `native-prims-intact?` gate. Surface unchanged at 807 publics at the time.
- **#640, per-package registrar surface:** any Go package can expose primitives by annotation and commit a self-registering registrar; contribute mode (metadata only) versus own mode (`//lg:bind`, also binds vars); `corefns` migrated off its hand-written module; `BindGeneratedPrimitive` exported but not yet wired.
- **#641, provenance manifest:** a content-hash dependency manifest maps each generated output to its inputs and generator sources, so `make generate` reruns only stale stages; generator closure from `go list -deps -json -tags bootstrap ./cmd/lgbgen`; torn lowered trees detected.

## Derived pages

[native-primitives](../concepts/native-primitives.md) · [generated-artifacts](../concepts/generated-artifacts.md) · [namespaces-and-vars](../concepts/namespaces-and-vars.md)

# Citations

[1] https://github.com/nooga/let-go/pull/639
