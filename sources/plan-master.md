---
type: Source
category: source
title: Master Plan
description: Official 9-phase roadmap for let-go development, from baseline semantics through AOT compilation and advanced optimizations.
tags: [runtime, compiler, vm, clojure, idea]
resource: "https://github.com/nooga/let-go/blob/main/docs/master-plan.md"
sources: ["repo: nooga/let-go docs/master-plan.md, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

## What this source is

The authoritative master plan for let-go development, last verified on 2026-06-05. It consolidates existing plans for VM performance, Clojure-like collections, numeric representation, and runtime images into a single staged roadmap with success metrics, acceptance criteria, and dependency management.

## Key contribution

Defines **9 cumulative phases** (Phases 0–9) to achieve the goal: "fastest and most useful Clojure-on-Go."

- **Vision metrics**: startup < 50 ms (cold), < 5 ms (warm); 2–3× throughput improvement on functional pipelines; O(1) allocations for transducers; Clojure-aligned semantics and deployability.
- **Guiding principles**: correctness first, tight hot paths, incremental rollout, benchmark-driven.
- **Phases**: Phase 0 (baseline semantics, numeric fast paths), Phase 1 (VM calling convention), Phase 2 (PersistentVector + transients), Phase 3 (HashMap/Set + equality), Phase 4 (transducers), Phase 5 (runtime images), Phase 6 (tooling), Phase 7 (Go AOT backend), Phase 8 (advanced polish), Phase 9 (register VM).
- **CI discipline**: micro and end-to-end benchmarks with >10% regression alerts; pprof sampling; deterministic image serialization.
- **Cross-cuttings**: comprehensive testing strategy (conformance, property tests, fuzzing), file index mapping phases to code locations, immediate workboard for next actions.

This plan is **authoritative for** Phase skeleton, success metrics, and cross-cutting benchmarks/CI. It is **superseded on direction** by `contribution-policy.md`, which commits Phase 7 Go AOT as the deployment path (not optional).

## Derived pages

- [master-plan-roadmap](../ideas/master-plan-roadmap.md) — detailed expansion of phases and milestones

## Citations

**Resource**: https://github.com/nooga/let-go/blob/main/docs/master-plan.md
