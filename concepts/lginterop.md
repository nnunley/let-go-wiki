---
type: Concept
category: concept
title: "lginterop"
description: "Wrapping Go packages as callable functions in let-go via code generation."
tags: [interop, go, tooling]
resource: "https://github.com/nooga/let-go/blob/main/scripts/lginterop.lg"
sources: ["repo: nooga/let-go scripts/lginterop.lg, pkg/rt/interop_xxh3.go (generated example), pkg/rt/core/hash.lg (usage), 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# lginterop

`lginterop` is a code generator that wraps Go packages so their functions become callable from let-go. Given a Go package path, it inspects the package's public exports and generates a `.go` file with:

1. **Type-aware wrapper functions** for each exported function (converting let-go values to Go types and back)
2. **Struct registrations** for exported types
3. **An installer function** that registers everything on a let-go namespace at runtime

This eliminates hand-wrapping boilerplate when integrating external Go libraries into let-go programs.

## Usage

Generate interop bindings for a Go package:

```bash
./lg scripts/lginterop -packages github.com/zeebo/xxh3
```

This generates a file (typically named after the package) with wrapper functions and an `install` function. The wrapper is added to the let-go build, and functions become available:

```clojure
(require '[hash])

(hash/xxh3-64 (byte-array [1 2 3]))  ; => uint64 hash value
```

Under the hood, the let-go program calls into wrapped Go functions like `xxh3/Hash`:

```clojure
(def xxh3-64 xxh3/Hash)  ; wrapper function from lginterop output
```

## How it Works

**lginterop** (`scripts/lginterop.lg`) is itself a let-go program that:

1. **Reflects over Go packages** using the `go/ast` and `go/types` facilities (bridged from Go)
2. **Catalogs exports** into a compact vector format:
   ```clojure
   [:func "Hash" [] ["[]uint8" "uint64"] false]  ; name, type-params, params, results, variadic?
   ```
3. **Generates Go code** using the `gogen` library to emit wrapper functions with type conversions, struct registrations, and an installer

The generated `.go` file contains:

- **Wrapper functions** (`wrapXxh3Hash`, etc.) that:
  - Unbox let-go `Value` arguments to Go types (strings → `string`, numbers → `int64`, etc.)
  - Call the original Go function
  - Box the Go return value back to a let-go `Value`

- **Struct registration** (for types matching let-go's record protocol) using `vm.RegisterStruct`

- **An installer function** (`InstallXxh3`, etc.) that:
  - Creates a new let-go namespace (e.g., `"xxh3"`)
  - Defines each wrapper function on the namespace
  - Registers structs
  - Calls `RegisterNS` to wire it into the runtime

At runtime, calling `(xxh3/Hash bytes)` from let-go invokes the wrapper, which converts bytes to Go `[]uint8`, calls the real `Hash`, and returns the result as a let-go number.

## Smart Wrappers

When all a function's parameters and results are simple types (`string`, `int`, `float64`, `bool`, `error`, or `interface{}`), lginterop can generate a "smart wrapper" that uses `vm.NativeFnType` — a fast-path specialization bypassing reflection at call time.

## Citations

[1] **lginterop** — Go package interop code generator (let-go script)  
https://github.com/nooga/let-go/blob/main/scripts/lginterop.lg

[2] **interop_xxh3.go** — generated example (xxh3 package wrapping)  
https://github.com/nooga/let-go/blob/main/pkg/rt/interop_xxh3.go

[3] **hash.lg** — user-facing API wrapping lginterop-generated functions  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/hash.lg

[4] **Go Interop** (this wiki)  
[go-interop.md](go-interop.md)

---

See also: [Go Interop](go-interop.md), [let-go](../entities/let-go.md)
