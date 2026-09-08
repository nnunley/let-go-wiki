---
type: Concept
category: concept
title: "lginterop"
description: "Wrapping Go packages as callable functions in let-go via code generation."
tags: [interop, go, tooling]
resource: "https://github.com/nooga/let-go/tree/main/cmd/lginterop"
sources: ["repo: nooga/let-go cmd/lginterop (main.go, lginterop.lg), docs/guide/go-interop.md, pkg/rt/interop_xxh3.go, pkg/rt/core/hash.lg @ 638b4a6a, 2026-09-07"]
created: "2026-07-02"
updated: "2026-09-07"
status: stable
---

# lginterop

`lginterop` is a code generator that wraps Go packages so their functions become callable from let-go. Given a Go package path, it inspects the package's public exports and generates a `.go` file with:

1. **Wrapper functions** for each exported function (adapted with `vm.MustBox` by default, or with explicit type-specific unboxing/boxing under `-smart`)
2. **Struct registrations** for exported types (or opaque boxed handles under `-opaque-structs`)
3. **An installer function** that registers everything on a let-go namespace at runtime

This eliminates hand-wrapping boilerplate when integrating external Go libraries into let-go programs.

Since #773 (2026-09-06, `f19e9f8a`) the tool is a Go binary, `cmd/lginterop`, that links the let-go runtime and runs its emitter in the same process. It needs neither a let-go checkout nor an `lg` binary, so `go run github.com/nooga/let-go/cmd/lginterop@<version>` works from any module. Before #773 it was a script, `scripts/lginterop.lg`, that had to be run by an `lg` built inside a checkout and could only emit files that compile as part of `pkg/rt`.

## Usage

The in-tree form, which is how `pkg/rt/interop_xxh3.go` is produced:

```bash
go run ./cmd/lginterop -packages github.com/zeebo/xxh3 -opaque-structs -build-tags '!tinygo' -out pkg/rt
```

The out-of-tree form, for a third-party module:

```bash
go run github.com/nooga/let-go/cmd/lginterop@<version> -packages github.com/mattn/go-sqlite3 -out-pkg interop -out ./interop
```

`-out-pkg <name>` is what makes the output usable outside the let-go tree; without it the generator emits `package rt`. The generated file's header records the invocation (flags, non-default aliases, and the `@<version>` when one was used), so regenerating from the header round-trips byte-identically; `test/e2e/lginterop_regen_test.go` holds `interop_xxh3.go` to that.

Once the file is in the build, the functions are available under a namespace named after the package:

```clojure
(require '[hash])

(hash/xxh3-64 (byte-array [1 2 3]))  ; => uint64 hash value
```

`pkg/rt/core/hash.lg` is the veneer over the generated `xxh3` namespace:

```clojure
(def xxh3-64 xxh3/Hash)  ; wrapper function from lginterop output
```

## How it Works

`cmd/lginterop` is a two-stage pipeline:

1. **`main.go` scans the package** with `go/types` and catalogs its exports into a compact vector format:
   ```clojure
   [:func "Hash" [] ["[]uint8" "uint64"] false]  ; name, type-params, params, results, variadic?
   ```
2. **The embedded `lginterop.lg` emitter renders Go source** using the `gogen` library. The binary evaluates the script through the runtime it already links (`gogen` registers via `pkg/rt`'s installer queue, so any binary importing `rt` has the emitter). It is compiled with `CompileMultiple` rather than `pkg/api`'s `Run`, because the script is a sequence of top-level forms and `Run` compiles only the first.

The generated `.go` file contains:

- **Wrapper functions** that unbox let-go `Value` arguments to Go types, call the original Go function, and box the result back to a let-go `Value`
- **Struct registration** (for types matching let-go's record protocol) using `vm.RegisterStruct`, unless `-opaque-structs` keeps them as `vm.Boxed` handles with reflective method dispatch, which xxh3 needs for `Hasher`
- **An installer function** (`install<Alias>NS`) that creates the namespace, `Def`s each wrapper on it, registers structs, and calls `RegisterNS`

How the installer is invoked is the load-bearing difference between the two forms. In-tree output calls `RegisterInstaller(install<Alias>NS)` from `init()`, so the namespace joins `rt`'s installer queue and is installed in order with the rest of core boot. Out-of-tree output calls `install<Alias>NS()` directly from `init()`: `rt` drains its installer queue during its own package init, and Go runs an imported package's `init` before the importer's, so a `RegisterInstaller` from outside the tree would enqueue after the drain and silently never run.

At runtime, calling `(xxh3/Hash bytes)` from let-go invokes the wrapper, which converts bytes to Go `[]uint8`, calls the real `Hash`, and returns the result as a let-go number.

## Smart Wrappers

With `-smart`, a function whose parameters and results are all simple types (`string`, `int`, `float64`, `bool`, `error`, `interface{}`) and whose result arity fits `NativeFnType.Wrap` (zero or one result, or two where the second is `error`) gets an explicit wrapper with type-specific unboxing and boxing instead of a `vm.MustBox` adapter (`smartable?` in `lginterop.lg`). Anything else falls back to `vm.MustBox` even under the flag.

## Citations

[1] **cmd/lginterop** — the generator: `main.go` scanner and embedded `lginterop.lg` emitter  
https://github.com/nooga/let-go/tree/main/cmd/lginterop

[2] **docs/guide/go-interop.md** — usage, flag reference, and out-of-tree generation  
https://github.com/nooga/let-go/blob/main/docs/guide/go-interop.md

[3] **PR #773** — self-contained interop packages and an importable pkg/cli (merged 2026-09-06)  
https://github.com/nooga/let-go/pull/773

[4] **interop_xxh3.go** — generated example (xxh3 package wrapping)  
https://github.com/nooga/let-go/blob/main/pkg/rt/interop_xxh3.go

[5] **hash.lg** — user-facing API wrapping lginterop-generated functions  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/hash.lg

[6] **Go Interop** (this wiki)  
[go-interop.md](go-interop.md)

---

See also: [Go Interop](go-interop.md), [let-go](../entities/let-go.md)
