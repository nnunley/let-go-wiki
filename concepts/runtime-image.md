---
type: Concept
category: concept
title: "Runtime Image and Stdlib Cache"
description: "Precompiled runtime images for fast cold startup and reproducible deployments, including the standard library cache."
tags: [runtime, compiler, go, bytecode]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/runtime-image-and-stdlib-cache.md"
sources: ["design: runtime-image-and-stdlib-cache.md, 2026-06-05"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# Runtime Image and Stdlib Cache

Let-go achieves millisecond cold startup by precompiling the standard library and serializing the runtime state to a **runtime image**—a self-contained snapshot of code, heap, and namespace metadata. Instead of reading source, analyzing, and compiling on boot, the runtime loads and deserializes this image in a fraction of the time.

## What a Runtime Image Contains

A runtime image is a persistent snapshot of:

- **Namespaces**: the registry, aliases, and current `*ns*` binding
- **Variables**: symbol → root value, metadata, macro flags
- **Code**: `Func` and `Closure` objects with `CodeChunk` (bytecode, stack depth, const refs) and closed-over values
- **Constant pool**: de-duplicated `Value`s (ints, strings, booleans, nil, symbols, keywords, vectors, lists, maps, sets)
- **Intern tables**: for symbols and keywords to preserve identity sharing across deserialization

Excluded from the image (they are rebound or rejected on load):

- `NativeFn` and `Boxed` host pointers (Go values): represented as **externs** by symbol and resolved from a host registry at load
- Non-serializable effects: channels, OS handles, goroutines, time values

## The Image Format

The binary format is structured in sections:

- **Header**: magic number, schema version, runtime version, endianness, feature flags
- **String table**: unique strings for symbols, keywords, and value interning
- **Atoms**: typed sections for nil, booleans, ints, chars, strings
- **Collections**: vectors, lists, maps, sets (encoded recursively; persistent encodings like BPTR/HAMT for determinism)
- **Const pool**: indices into value sections
- **Code**: functions with `maxStack`, bytecode, const refs, closed-over const refs
- **Namespaces**: table mapping ns name → alias map → var table
- **Variables**: name → const-id (root), flags
- **Trailer**: checksum/hash and optional signature

## Workflows: Build-Time and Boot-Time

**Precompiled stdlib cache**:

1. **Build step**: Compile the standard library once; emit `stdlib.img`.
2. **App boot**: Load `stdlib.img` with the host's `HostRegistry`. If invalid or mismatched, compile sources and regenerate.

**Full runtime image (REPL freeze)**:

1. Develop in the REPL, loading stdlib and evaluating app code.
2. Save the entire heap and namespace: `(image/save "app.img")`.
3. Deploy: embed or ship `app.img` and load it at startup.

## Host and Native Binding

During image load, the loader is provided a `HostRegistry` that maps core symbols to their `NativeFn` implementations. Extern placeholders (representing natives and boxed values) are resolved against this registry at load time. This ensures:

- Natives are rebound to the running host's implementations (which may differ between platforms).
- Signature/arity mismatches are caught immediately; no silent corruption.
- The image is platform-independent; the host binding makes it work on any platform.

## Layering and Versioning

- **Base image**: stdlib only, enabling fast cold start universally
- **App layer**: app-specific code; can be loaded atop the base image without reloading stdlib
- **Optional**: multiple layers chained with conflict checks

The image carries metadata for validation:

- **Schema version**: format compatibility
- **Runtime/VM version**: bytecode interpreter compatibility
- **Content hash**: of stdlib sources, to detect staleness
- The loader rejects incompatible versions and regenerates on mismatch

## Why It Matters

Runtime images enable:

- **Fast cold start**: Millisecond startup times. Compile-on-boot overhead is eliminated.
- **Reproducible deployments**: Freeze a known-good REPL state into a bytecode snapshot; deploy it anywhere.
- **Embedding**: Ship a precompiled image inside a Go binary (via `go:embed`), making the binary completely self-contained and independent of filesystem layout.
- **Deterministic CI/CD**: The same image loaded on every machine gives identical behavior.

For let-go's bootstrap workflow (3-minute lowering of the core library), image caching for the stdlib alone saves significant time in development and CI.

## Security Considerations

Runtime images are treated as **untrusted input**:

- Section sizes and offsets are validated.
- Content hashes are checked.
- Signatures can be verified before load.
- Extern placeholders are **only** resolved against an explicit host registry; no pointer deserialization happens blindly.

# Citations

[1] **pkg/rt/core/core.lg**: Standard library source  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg

[2] **pkg/rt/lang.go**: Runtime initialization; image loader called first, fallback to Eval  
https://github.com/nooga/let-go/blob/main/pkg/rt/lang.go

[3] **pkg/compiler/eval.go**: Compilation path (source → bytecode)  
https://github.com/nooga/let-go/blob/main/pkg/compiler/eval.go

[4] **pkg/vm/func.go**: `Func`, `Closure`, `CodeChunk` encoding  
https://github.com/nooga/let-go/blob/main/pkg/vm/func.go

[5] **pkg/vm/value.go**: `Value` serialization interface  
https://github.com/nooga/let-go/blob/main/pkg/vm/value.go

[6] **pkg/vm/native_func.go**: Extern resolution via `HostRegistry`  
https://github.com/nooga/let-go/blob/main/pkg/vm/native_func.go

---

See also: [Bytecode Compiler](bytecode-compiler.md), [Stack VM](stack-vm.md), [IR Pipeline](ir-pipeline.md)
