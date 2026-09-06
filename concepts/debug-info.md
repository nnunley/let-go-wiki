---
type: Concept
category: concept
title: "Debug Info & Source Maps"
description: "Mapping bytecode back to source locations and local variable names for readable crash traces and error reporting."
tags: [compiler, bytecode, vm, tooling]
resource: "https://github.com/nooga/let-go/blob/main/pkg/vm/source.go"
sources:
  - "design: docs/superpowers/specs/2026-05-30-debug-info-and-symmap-design.md (local, 2026-07-02)"
  - "repo: nooga/let-go pkg/bytecode/{strip,debug_companion}.go, pkg/rt/run.go, pkg/vm/errfmt.go @ 0911118, 2026-09-05"
  - "pr: nooga/let-go#624 (split debug companion), 2026-09-05"
created: "2026-07-02"
updated: "2026-09-05"
status: active
---

# Debug Info & Source Maps

When the [stack VM](stack-vm.md) encounters an error or crash, a readable stack trace must answer four questions: **which source file?** **which function?** **which line?** **which local variables were in scope?** Debug info (source maps, symbol tables, and forms indices) enable [bytecode](bytecode-compiler.md) to remain self-describing under bundle execution—especially in WASM and precompiled `.lgb` artifacts where the original source is not available at runtime.

The system is organized in tiers by cost, sensitivity, and deployment model:

## Tier 0: Always In — File, Function, Line (+ Local Names Captured)

Tier 0 debug data (source file, function name, line/column) is serialized into every `.lgb` bundle by default and exposes only identifiers, not values. The design doc's figure was about 20 KB (+4.7%) on the 2026-05-30 bundle; at `0911118` (2026-09-05) `cmd/lgbstat` measures the source maps at 47,476 bytes and the local-variable tables at 7,745, together about 18% of a 308,176-byte core bundle.

As of PR #131 (merged 2026-06-01), **local variable names** are also captured and stored, enabling future rendering in error traces. The data layer is complete; rendering is planned.

**Implementation:**
- **SourceInfo** (`pkg/vm/source.go`): Struct tracking file, line, column, and optional symbol (variable name). Populated at read time by `vm.FormSource`, keyed by form object identity.
- **SourceMap** (`pkg/vm/source.go`): Maps bytecode instruction-pointer (IP) offsets to SourceInfo entries. The VM's `Lookup(ip)` finds the nearest source location for any instruction.
- **Local variable tables** (PR #131, `pkg/bytecode`): Each `CodeChunk` carries a table of **(slot, name)** pairs. A slot maps to a runtime stack frame position; the name is the original identifier from source. Serialized under `FlagLocalVars` in the `.lgb` format, decoded and reconstructed into each chunk at bundle load time. Available via `CodeChunk.LocalVars()`, but not yet rendered by error formatters.

**Usage in Error Reporting:**
Tier 0 data is fully captured and serialized: local variable names are stored in each `CodeChunk` via `LocalVars()` (populated by PR #131). However, rendering these names into stack traces is not yet implemented. Currently, the VM's `FormatError` function (in `pkg/vm/errfmt.go`) displays source location, file, line, and function name when rendering a frame, but does not yet query the `LocalVars` table. Wiring local-variable rendering into `FormatError` is a planned next step: the design doc describes it as "a natural next increment after #131." As of 2026-09-05 no non-test code outside `pkg/bytecode` reads `CodeChunk.LocalVars()` (the one other reader is `pkg/compiler/localvars_test.go`); the names are still stored and not shown.

**Planned rendering** (not yet shipped):
```
function div/2 at app.lg:42:8
  locals: numerator, denominator
  42 | (/ numerator denominator)
       ^
```

Tier 0 data capture is enabled by default and requires no deployment changes. Tier 0 rendering (displaying locals in error output) is planned.

## Split debug companion — Tier 0 data, externalized (shipped)

Since #624 (merged 2026-09-04) the Tier 0 tables no longer have to travel inside the shipped artifact. `lg -strip -c app.lgb app.lg` writes `app.lgb` without its source maps and local-variable tables plus `app.lgb.debug`, a companion that restores them; `lg -strip -b myapp app.lg` does the same for a standalone bundle, and `-debug-output <path>` picks another location. The stripped artifact carries `FlagDebugSplit` in its [`.lgb` header](lgb-bytecode-format.md).

What the companion is:

- A small binary (`LGD\x01`, version 1) holding the SHA-256 of the exact stripped payload, a string table, and per chunk the source-map entries and `(slot, name)` local-variable pairs. On the fib sample it is 201 bytes against a 1,421-byte runtime artifact; on the core bundle the debug sections are about 20% of the file.
- **Digest-bound.** A companion whose digest does not match the artifact is rejected rather than symbolizing a trace with the wrong tables. This is the build-id matching the Tier 1 design asked for, applied to Tier 0 data.
- **Optional at run time.** `lg app.lgb`, a standalone bundle, and `lg-runtime` load `<artifact>.debug` from beside the artifact when it exists; `LG_DEBUG_FILE=<path>` loads one from elsewhere, and `LG_DEBUG_FILE=` (empty) disables loading. Without a companion the program runs and reports frames without source locations.

What it is not: it contains no source text and no forms index, so it symbolizes to file, function, and line, not to highlighted form context. The embedded core and the `-w`/WASI paths are not stripped.

## Tier 1: Opt-In — Forms Index, Source Text, Build-ID Matching (Design)

Tier 1 (under design as of 2026-05-30) adds richer context for offline symbolization: a **forms index** (byte offsets and extents for each top-level form), optional compressed source text, and stable **build-id** linking to ensure traces are symbolized with the correct debug data.

**Planned Design:**

A **.lgsym sidecar** (debug-only artifact, shipped separately from the `.lgb`) carries:
- **Magic + version header** for forward compatibility
- **Build-id** (16-byte content hash of the bundle code + constants): Must match the bundle's build-id; the symbolizer refuses to symbolize on mismatch, preventing mismatched traces.
- **Forms index**: One entry per top-level form, recording start line, start column, byte offset in the source blob, and end byte. Keyed by chunk reference (chunk index / function ID).
- **Source blob**: Compressed via `flate` (single shared stream across all form texts for better compression than per-entry deflate). Indexed by form byte ranges, sliced by the forms index.

**Symbolizer tool** (planned): Takes a raw trace (chunk index + IP, or function ID) and the `.lgsym`, verifies build-id, and renders rich traces offline. Mirrors JavaScript source-map recovery or native `atos`/`addr2line` workflows.

**Deployment:**
- `lg -c` (compile) or `lgbgen`/`buildWasm` gains `--debug` flag:
  - `--debug`: embed Tier 1 inline in `.lgb` (rich live traces, no sidecar needed)
  - default: emit lean `.lgb` + separate `.lgsym` sidecar (keep source code out of shipped artifact)
  - `--no-symmap`: omit Tier 1 entirely (smallest bundle, no offline symbolization)

**Rationale for a custom binary format (not ZIP):**
- **Compression:** Single shared `flate` stream over concatenated form texts compresses ~3.8×; per-entry deflate yields ~2.9×, plus per-entry headers add up (30 B local + 46 B central-dir per entry). Custom format achieves denser packing.
- **Integration:** Reuses `.lgb` Reader/Writer primitives, varint encoding, string-table interning, and build-id/versioning machinery—no parallel mechanism needed.
- **Granularity:** ZIP forces per-file entries; custom format keeps compression at the level of the entire form corpus.

The forms index makes source **highlighting** practical: store a base line/column per form, express all inner `SourceInfo` relative to that base, and slice the exact form text from the blob—no need to load or search the whole source file.

Tier 1 is not shipped as designed: no `.lgsym` sidecar, forms index, or source blob exists in the tree as of 2026-09-05. The digest-bound companion above took over the build-id and sidecar roles for Tier 0 data; the forms index and source text remain open.

## Tier "Values": Never Default

Variable **values** in traces are a well-known security footgun: a frame holding `password`, `api_key`, or a token leaks it into logs and error trackers. By design:

- Default output shows **names only** (e.g., `locals: numerator, denominator, ratio`).
- **Values are never rendered by default.** If ever surfaced, it requires an explicit flag **and** a redaction pass:
  - Deny-list name patterns (`*pass*`, `*secret*`, `*token*`).
  - Length and entropy caps to block large or suspicious values.

The `.lgsym` sidecar is kept private (not shipped), so production operators cannot reconstruct the program from traces—debug data is joined to stack traces offline only by trusted processes.

## Integration with Crash Reporting

When a bundle-loaded program crashes (WASM or precompiled bytecode), the exception handler produces a **raw trace**: bytecode offsets, chunk indices, and frame stack. The raw trace is small and safe (no source exposure).

If Tier 1 debug info is available (either embedded or via `.lgsym`), a **symbolizer** (or integrated error reporter) enriches the raw trace with:
1. Verify build-id (bundle ↔ `.lgsym` match).
2. Resolve chunk index → function name (already in Tier 0).
3. Resolve IP → line/column in source file (Tier 0, SourceMap).
4. Slice the top-level form from the source blob (Tier 1, forms index + source blob).
5. Highlight the relevant line and column in the form's context (Tier 1, relative line/column).
6. Render named local bindings (Tier 0, local-var tables).

Result: a readable, context-rich trace indistinguishable from source-level debugging—without embedding source in the shipped binary.

## Security & Deployment Trade-offs

| Tier | Contents | Status | Cost | In Bundle? | Sensitivity | Use Case |
|---|---|---|---|---|---|---|
| **0 (file, function, line)** | source location | shipped | ~47 KB (15%) of the core bundle at 0911118 | always | low | live REPL, self-describing errors |
| **0 (local names, data layer)** | local var names captured | shipped (PR #131) | included | always | low | future trace rendering |
| **0 (local names, rendering)** | display locals in errors | planned | — | — | — | richer live debugging |
| **0, split** (`-strip`) | source maps + local names moved to `.debug` | shipped (#624) | −9% (fib), −20% (core) | companion, digest-bound | low | smaller deploy artifact, symbol store |
| **1 (forms index, source text)** | forms index, source blob | design only | ~50–100 KB | opt-in / sidecar | medium | offline symbolization, web deployment |
| **values** | variable values | never (out of scope) | varies | never | high | redaction / explicit flag only |

Production deployments can ship a stripped `.lgb` and keep the `.debug` companion in build artifacts or a symbol store. Local development and REPLs benefit from embedded Tier 1 for instant, detailed traces.

# Citations

[1] **Debug Info & Symbol Maps — Design Doc**  
`docs/superpowers/specs/2026-05-30-debug-info-and-symmap-design.md` (local, 2026-07-02)

[2] **SourceInfo and SourceMap — Core Types**  
https://github.com/nooga/let-go/blob/main/pkg/vm/source.go

[3] **Bytecode Decoder — Local Variable Deserialization**  
https://github.com/nooga/let-go/blob/main/pkg/bytecode/decoder.go

[4] **Local Variable Tables — Roundtrip Tests**  
https://github.com/nooga/let-go/blob/main/pkg/bytecode/localvars_test.go

[5] **Error Formatting — Trace Rendering**  
https://github.com/nooga/let-go/blob/main/pkg/vm/errfmt.go

[6] **Split debug: strip, companion, loader**  
https://github.com/nooga/let-go/blob/main/pkg/bytecode/strip.go  
https://github.com/nooga/let-go/blob/main/pkg/bytecode/debug_companion.go  
https://github.com/nooga/let-go/blob/main/pkg/rt/run.go  
https://github.com/nooga/let-go/pull/624

[7] **Bytecode Compiler** (this wiki)  
[bytecode-compiler.md](bytecode-compiler.md)

[8] **Stack VM** (this wiki)  
[stack-vm.md](stack-vm.md)

---

See also: [let-go](../entities/let-go.md)
