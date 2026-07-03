---
type: Concept
category: concept
title: ".lgb Bytecode Format (v2)"
description: "Binary serialization format for let-go compiled code, with per-tag versioning, batch collection decoding, and capability-mask extensibility."
tags: [bytecode, vm, compiler, runtime]
resource: "https://github.com/nooga/let-go/blob/main/pkg/bytecode/decoder.go"
sources:
  - "design: docs/superpowers/specs/2026-05-23-lgb-v2-design.md (local, 2026-07-02)"
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

## What is `.lgb`?

The `.lgb` format is let-go's binary bytecode representation. It encodes compiled modules—code chunks, constants, and namespace tables—in a compact, versioned wire format. The `lg` compiler emits `.lgb` files via the `-c` flag; the runtime loads them via `DecodeToExecUnit` for execution.

## When it matters

- **Startup speed**: Decoding is faster than recompiling. Bytecode caching trades compile time for decode time.
- **Format stability**: Per-tag versioning lets the decoder refuse incompatible future versions early instead of silently misinterpreting data.
- **Collection decode efficiency**: v2 batch construction reduces allocation churn for large vectors/maps/sets.

## Structure

### Header
```
Magic       [4]byte   "LGB\x01"
Version     uint16    = 2
Flags       uint16    (FlagConstsBase, FlagCapabilities, FlagLocalVars)
[Capabilities] uint32 (optional, if FlagCapabilities set)
```

The optional capability mask allows decoders to reject `.lgb` files with unsupported features:
```
if fileCaps & ~decoderCaps != 0 { return error }
```
This reserves capacity bits for future features (varint operands, lazy const loading, SSA metadata) without breaking old decoders.

### Sections (in order)
1. **String table** — deduplicated string pool
2. **Chunks** — bytecode instructions and metadata for each function
3. **Consts** — value constants (literals, functions, types)
4. **NS table** — namespace → chunk index mapping
5. **Local var tables** (optional) — debug symbols for slots

### Tag encoding
Each value's tag byte is `0bVV_TTTTTT`:
- `VV` (2 bits): tag version. `00` = v1 semantics, `01` = v2, etc.
- `TTTTTT` (6 bits): tag ID

For v2.0, all tags are version 0 (unchanged wire bytes from v1). When a tag semantics changes, its version bits increment; old decoders see a new byte value and fail safely instead of misinterpreting.

Known tag IDs (6-bit):
- Scalars: nil, true, false, int, float, string, keyword, symbol, char, big-int, void, UUID, instant
- Code: func, var-ref
- Collections: empty-list, list, vector, map, set
- User types: record-type, record, regex, atom

Reserved slots: `0x34`–`0x3F` (12 future tags).

## v2 optimizations

### Batch collection construction
Instead of building maps/sets with O(N log N) per-element `Assoc` calls, v2 decodes collections via batch constructors:

- **Vector**: preallocate slice, populate directly
- **Map**: accumulate key/value pairs, call `NewPersistentMap` once (builds tree from sorted keys)
- **Set**: accumulate values, call `NewPersistentSet` once

This eliminates per-element persistent copies and reduces heap churn measurably for large collections.

### Backward compatibility
The decoder is dual-path:
- v1 `.lgb` files → frozen `decodeToExecUnitV1()` path (no changes)
- v2 `.lgb` files → new `decodeToExecUnitV2()` path (batch decode, tag versioning)

Encoder always writes v2; old files still load.

## Implementation

The [bytecode package](https://github.com/nooga/let-go/tree/main/pkg/bytecode) provides:
- `Encode(w, m *Module)` — serialize to binary
- `Decode(r io.Reader) (*Module, error)` — deserialize
- `DecodeToExecUnit(r, resolve VarResolver) (*ExecUnit, error)` — decode ready-to-run

The core library (`pkg/rt/core_compiled.lgb`) is regenerated during compilation via `go generate`.

## Citations

**Resource:** [pkg/bytecode/decoder.go](https://github.com/nooga/let-go/blob/main/pkg/bytecode/decoder.go) — dual-path v1/v2 decoder with batch collection decode  
**Related:**
- [pkg/bytecode/encoder.go](https://github.com/nooga/let-go/blob/main/pkg/bytecode/encoder.go) — v2 encoder
- [pkg/bytecode/tags.go](https://github.com/nooga/let-go/blob/main/pkg/bytecode/tags.go) — tag definitions and version bits
- [pkg/bytecode/bench_test.go](https://github.com/nooga/let-go/blob/main/pkg/bytecode/bench_test.go) — startup/decode benchmarks

**Design doc:** Local design spec at `docs/superpowers/specs/2026-05-23-lgb-v2-design.md` details format versioning, migration from v1, and success criteria (allocation reduction, no startup regression).
