---
type: Concept
category: concept
title: ".lgb Bytecode Format"
description: "Binary serialization format for let-go compiled code: versioned header, capability mask with opcode-set signature, per-tag versioning, opt-in DEFLATE body, and split debug companions."
tags: [bytecode, vm, compiler, runtime]
resource: "https://github.com/nooga/let-go/blob/main/pkg/bytecode/tags.go"
sources:
  - "repo: nooga/let-go pkg/bytecode/{tags,encoder,decoder,capabilities,strip,debug_companion}.go @ 0911118, 2026-09-05"
  - "pr: nooga/let-go#443 (opcode-set capability), #608/#622 (capability reject messages, lg -v), #501 (DEFLATE body), #502 (compressed embedded core), #745 (func chunk identity), #624 (split debug), 2026-09-05"
  - "design: docs/superpowers/specs/2026-05-23-lgb-v2-design.md (local, 2026-07-02)"
created: "2026-07-02"
updated: "2026-09-05"
status: stable
---

## What is `.lgb`?

The `.lgb` format is let-go's binary bytecode representation. It encodes compiled modules (code chunks, constants, namespace tables, and optional debug tables) in a compact, versioned wire format. `lg -c` emits `.lgb` files, `lg -b` appends one to a copy of the `lg` binary, and the runtime loads either through `DecodeToExecUnit`. The core library ships the same way: `pkg/rt/core_compiled.lgb` is the bytecode the runtime boots from instead of compiling `core.lg` (see [runtime image](runtime-image.md)).

## When it matters

- **Startup speed**: decoding is faster than recompiling, so bytecode caching trades compile time for decode time.
- **Version skew**: the header carries enough to refuse a bundle from a different `lg` before any instruction runs. The costly failure this prevents is an opcode enum that moved between the compiling tree and the running tree, which used to surface deep in execution as `unknown instruction op=37`.
- **Artifact size**: compression and split debug information are both opt-in trades of size against convenience.

## Header

```
Magic          [4]byte   "LGB\x01"
Version        uint16    1, 2, or 3
Flags          uint16    see below
[Capabilities] uint32    only when FlagCapabilities is set
[OpcodeSet]    varint count + uint64 FNV-64a   only when CapOpcodeSet is set
```

Everything in the header stays plaintext, including in compressed bundles, so version, flag, and capability checks run before any inflate.

### Format versions

| Version | Written when | Adds |
|---|---|---|
| 1 | never (read only) | original encoding; decoded by a frozen `decodeToExecUnitV1` path |
| 2 | default | per-tag versioning, batch collection decode, local-variable tables |
| 3 | `-z` is passed | compressed-body framing; the body is one DEFLATE stream |

The encoder picks the lowest version that admits the module's flags, so a plain bundle stays byte-identical to what a pre-compression `lg` wrote. `lg -v` reports both numbers: `lgb: format 2 (default write), 3 (max)`.

### Flags

Bits are positional in declaration order, and each version admits only the flags that existed when it was defined. A flag from a later version is rejected at the header with `unsupported LGB flags 0x%04x for version %d (supported: 0x%04x)`.

| Flag | Since | Meaning |
|---|---|---|
| `FlagConstsBase` | v1 | a `ConstsBase` field is present in the consts section |
| `FlagCapabilities` | v1 | a capability mask follows the header |
| `FlagLocalVars` | v2 | per-chunk local-variable tables follow the NS table |
| `FlagCompressed` | v3 | the body after the header is a declared-size, codec-tagged compressed stream |
| `FlagDebugSplit` | v3 | source maps and local-variable tables were moved to an external `.debug` companion |

### Capability mask and opcode-set signature

The capability mask reserves bits for features a decoder must understand to run the bundle at all. One bit is defined:

- `CapOpcodeSet` (bit 0, since v1.12.0): the mask is followed by the producer's opcode count and an FNV-64a hash of the opcode mnemonics in enum order. The decoder compares it with the running VM's `vm.OpcodeSetSignature()` and rejects a mismatch:

```
opcode set mismatch: bundle compiled with 52 opcodes (signature 8c6f19e2a4b07d31), runtime has 44 (ecde554a791d0f51) — recompile the bundle with a matching lg
```

(The bundle side is illustrative; the runtime side is what `lg -v` reports at `0911118`.)

Unknown capability bits are rejected too. The message names the unsupported bits (known ones with the `lg` release that introduced them, unknown ones as `unknown bit N`), then the runtime's supported set, then the minimum `lg` version when one is known, so a "recompile or upgrade" decision can be made from the error alone. `lg -v` and `lg-runtime -v` print the supported mask and the local opcode signature.

## Body

Sections in order:

1. **String table**: deduplicated string pool; later sections reference strings by index.
2. **Chunks**: one entry per `CodeChunk` with its instruction words, `maxStack`, and source map.
3. **Consts**: value constants (literals, functions, types). A function constant names its chunk by index; the encoder uses the module builder's live `*vm.CodeChunk` pointer index for that mapping, because two functions can have identical bytecode and different source metadata (#745).
4. **NS table**: namespace name to chunk index, in load order.
5. **Local-variable tables** (only with `FlagLocalVars`): per chunk, `(slot, name)` pairs in chunk-index order.

### Tag encoding

Each value's tag byte is `0bVV_TTTTTT`: two bits of tag version and a six-bit tag ID. All current tags are version 0, byte-identical to v1. When a tag's semantics change, its version bits increment, so an old decoder sees an unknown byte and fails instead of misreading the payload.

Tag IDs: scalars `0x00`–`0x0C` (nil, true, false, int, float, string, keyword, symbol, char, big-int, void, UUID, instant), code `0x10`–`0x11` (func, var-ref), collections `0x20`–`0x24` (empty-list, list, vector, map, set), user types `0x30`–`0x33` (record-type, record, regex, atom). `0x34`–`0x3F` are reserved (`TagIDReserved0`–`TagIDReserved11`).

### Batch collection construction (v2)

Collections decode through batch constructors rather than per-element `Assoc`: a vector preallocates its slice, and a map or set accumulates its entries and calls `NewPersistentMap` or `NewPersistentSet` once. This removed the per-element persistent copies that dominated decode time for large literals.

## Compression (v3)

`lg -c app.lgb -z app.lg` and `lg -b myapp -z app.lg` write a version-3 bundle whose body is one raw DEFLATE stream (`compress/flate`, chosen because it is stdlib and works under TinyGo and wasip1). After the plaintext header come a varint with the exact uncompressed body size and a codec byte (`1` = flate; the byte is a value rather than a flag bit so a future codec such as zstd costs no flag space). The decoder caps the declared size at 256 MiB and rejects a stream that stops short of, or runs past, the declaration. A version-2 decoder rejects the bundle by version before touching the stream.

The embedded core bundle can be compressed the same way at `lgbgen` time; that is off by default (#502).

## Split debug information (v3)

`lg -strip -c app.lgb app.lg` writes `app.lgb` without its source maps and local-variable tables plus `app.lgb.debug`, a companion that can restore them. `lg -strip -b myapp app.lg` does the same for a bundle (`myapp` + `myapp.debug`), and `-debug-output <path>` picks another location. On the fib sample the stripped runtime artifact is about 9% smaller; on the core bundle the debug sections are about 20%.

The companion (`LGD\x01`, version 1) stores the SHA-256 of the exact stripped payload, a string table, and per chunk the source-map entries (`StartIP`, file, line, column, end line, end column) and local-variable `(slot, name)` pairs. A companion whose digest does not match is rejected rather than producing misleading tracebacks. `SplitDebug` also re-decodes the stripped output and checks chunk count, code, and `maxStack` against the original before emitting a companion.

At load time `lg app.lgb`, a standalone bundle, and `lg-runtime` look for `<artifact>.debug` beside the artifact; `LG_DEBUG_FILE=<path>` loads one from elsewhere, and `LG_DEBUG_FILE=` (empty) disables loading. Without a companion the stripped artifact runs and reports frames without source locations. Stripping applies to program bytecode from `-c` and `-b`; the embedded core and the `-w`/WASI paths are not stripped. See [debug info](debug-info.md) for what the tables hold.

## Implementation

The [bytecode package](https://github.com/nooga/let-go/tree/main/pkg/bytecode) provides:

- `Encode(w, m *Module)` and `Decode(r) (*Module, error)`: serialize and deserialize.
- `DecodeToExecUnit(r, resolve VarResolver) (*ExecUnit, error)`: decode ready to run.
- `StripDebug` and `SplitDebug`: produce the stripped artifact and its companion; `HasSplitDebug` is the cheap header probe the loaders use.
- `DescribeCapabilities` and `FormatVersionReport`: the human-readable capability and version text used by reject errors and `lg -v`.

`pkg/rt/core_compiled.lgb` is regenerated by `make generate` whenever `pkg/rt/core/**/*.lg` changes; `make check-generated` verifies it is in sync.

## Citations

**Resource:** [pkg/bytecode/tags.go](https://github.com/nooga/let-go/blob/main/pkg/bytecode/tags.go): magic, versions, flags, capability bits, tag layout  
**Related:**
- [pkg/bytecode/encoder.go](https://github.com/nooga/let-go/blob/main/pkg/bytecode/encoder.go): version selection, section order, compressed framing
- [pkg/bytecode/decoder.go](https://github.com/nooga/let-go/blob/main/pkg/bytecode/decoder.go): per-version flag admission, dual v1/v2 paths, batch collection decode
- [pkg/bytecode/capabilities.go](https://github.com/nooga/let-go/blob/main/pkg/bytecode/capabilities.go): capability registry and `lg -v` report
- [pkg/bytecode/strip.go](https://github.com/nooga/let-go/blob/main/pkg/bytecode/strip.go) and [debug_companion.go](https://github.com/nooga/let-go/blob/main/pkg/bytecode/debug_companion.go): split debug
- [pkg/rt/run.go](https://github.com/nooga/let-go/blob/main/pkg/rt/run.go): `LoadDebugCompanion` and `LG_DEBUG_FILE`
- [docs/guide/usage.md](https://github.com/nooga/let-go/blob/main/docs/guide/usage.md): `-z`, `-strip`, `-debug-output`
- PRs: [#443](https://github.com/nooga/let-go/pull/443) opcode-set signature, [#608](https://github.com/nooga/let-go/pull/608) and [#622](https://github.com/nooga/let-go/pull/622) capability reject messages, [#501](https://github.com/nooga/let-go/pull/501) compression, [#502](https://github.com/nooga/let-go/pull/502) compressed embedded core, [#745](https://github.com/nooga/let-go/pull/745) chunk identity, [#624](https://github.com/nooga/let-go/pull/624) split debug

**Design doc:** the v2 design spec (`docs/superpowers/specs/2026-05-23-lgb-v2-design.md`, local) covers format versioning, migration from v1, and the allocation and startup success criteria.
