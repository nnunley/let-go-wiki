---
type: Concept
category: concept
title: "lginterop"
description: "Wrapping Go packages as callable functions in let-go via code generation."
tags: [interop, go, tooling]
resource: "https://github.com/nooga/let-go/tree/main/cmd/lginterop"
sources: ["repo: nooga/let-go cmd/lginterop (main.go, lginterop.lg), docs/guide/go-interop.md, pkg/rt/interop_xxh3.go, pkg/rt/core/hash.lg @ 638b4a6a, 2026-09-07", "repo: nooga/let-go cmd/lginterop (main.go, lginterop.lg), docs/guide/go-interop.md, docs/guide/custom-lg.md, pkg/rt/interop_xxh3.go, pkg/rt/interop_xxh3_tinygo.go, pkg/rt/hash_xxh3_wrap.go, pkg/rt/core/hash.lg, pkg/rt/gogen.go, pkg/rt/zz_run_installers.go, test/e2e/lginterop_regen_test.go @ b82588292b, 2026-10-20"]
created: "2026-07-02"
updated: "2026-10-20"
status: stable
---

# lginterop

`lginterop` is a code generator that wraps Go packages so their functions become callable from let-go. Given a Go package path, it inspects the package's exported identifiers and generates a `.go` file with:

1. **Wrapper functions** for each exported function (adapted with `vm.MustBox` by default, or with explicit type-specific unboxing/boxing under `-smart`)
2. **Struct registrations** for exported struct types (`vm.RegisterStruct`), or opaque boxed handles under `-opaque-structs`
3. **An installer function** (`install<Alias>NS`) that creates the namespace, defines each wrapper on it, registers the structs, and calls `RegisterNS`

This removes hand-written wrapper code when integrating external Go libraries into let-go programs.

Before #773 (`f19e9f8a`, 2026-09-06), `cmd/lginterop` found the let-go repository root, built an `lg` binary from it, and ran the emitter script `scripts/lginterop.lg` through that binary with `-source-paths scripts`. The tool needed a let-go checkout to run. #773 moved the emitter to `cmd/lginterop/lginterop.lg`, embedded it with `go:embed`, and evaluates it in the binary's own process, so the tool links the let-go runtime directly and needs neither a checkout nor an `lg` binary. #773 also added `-out-pkg`; the pre-#773 flags have no such option, so that tool produced only the in-tree form.

## Usage

The in-tree form, which is how `pkg/rt/interop_xxh3.go` is produced (the file header records this command):

```bash
go run ./cmd/lginterop -packages github.com/zeebo/xxh3 -opaque-structs -build-tags '!tinygo' -out pkg/rt
```

The out-of-tree form, for a third-party module:

```bash
go run github.com/nooga/let-go/cmd/lginterop@<version> -packages github.com/mattn/go-sqlite3 -out-pkg interop -out ./interop
```

`-out-pkg <name>` is what makes the output usable outside the let-go tree; without it the generator emits `package rt`. The generated file's header records the invocation: the flags, any non-default alias (as `-packages path=alias`), and a `// Generated with lginterop <version>.` line when the binary reports a module version (`generatorVersion()` in `cmd/lginterop/main.go`). `-out` is omitted from the header, so regenerating from the header's own command produces the same bytes. `test/e2e/lginterop_regen_test.go` holds `interop_xxh3.go` to that round trip.

A third-party package must be scanned from inside a module that already requires it. The scanner uses the `go/types` source importer, which resolves imports against the module of the working directory. The guide's example runs `go get github.com/mattn/go-sqlite3` before the generator. Standard-library packages resolve from any directory.

Once the file is in the build, the functions are available under a namespace named after the package:

```clojure
(require '[hash])

(hash/xxh3-64 (byte-array [1 2 3]))  ; => uint64 hash value
```

`pkg/rt/core/hash.lg` is the veneer over the generated `xxh3` namespace:

```clojure
(def xxh3-64 xxh3/Hash)  ; wrapper function from lginterop output
```

For a binary outside the let-go tree, the generated package is linked with a blank import. The `-import <pkg>` flag of a custom lg binary built as described in `docs/guide/custom-lg.md` (for `-w` with `-w-module`, and for `lg compile` with `-module`) adds that blank import to the generated program, so its `init()` registers the namespace (`docs/guide/custom-lg.md`).

## How it Works

`cmd/lginterop` is a two-stage pipeline:

1. **`main.go` scans the package** with `go/types` and catalogs its exports into a compact vector format:
   ```clojure
   [:func "Hash" [] ["[]byte"] ["uint64"]]  ; name, type-params, params, results; the marker " :variadic" follows results for variadic functions
   ```
2. **The embedded `lginterop.lg` emitter renders Go source** using the `gogen` library. The binary evaluates the script through the runtime it already links. `gogen` registers its namespace through `pkg/rt`'s installer queue (`pkg/rt/gogen.go`), so any binary importing `rt` has the emitter. The script is run with `CompileMultiple` rather than `pkg/api`'s `Run`, because the script is a sequence of top-level forms and `Run` compiles only the first (comment in `cmd/lginterop/main.go`).

The generated `.go` file contains:

- **Wrapper functions** that unbox let-go `Value` arguments to Go types, call the original Go function, and box the result back to a let-go `Value`
- **Struct registration** for exported struct types using `vm.RegisterStruct`, unless `-opaque-structs` keeps them as `vm.Boxed` handles with reflective method dispatch. The guide gives xxh3 as the case that needs this, because its `Hasher` is used through methods (`.WriteString`, `.Sum64`)
- **An installer function** (`install<Alias>NS`) that creates the namespace, defines each wrapper on it (`ns.Def`), registers structs, and calls `RegisterNS` (see `pkg/rt/interop_xxh3.go`)

How the installer is invoked is the difference between the two forms. In-tree output calls `RegisterInstaller(install<Alias>NS)` from `init()`, so the namespace joins `rt`'s installer queue and is installed with the rest of core boot. Out-of-tree output calls `install<Alias>NS()` directly from `init()`. `pkg/rt` drains its installer queue in `pkg/rt/zz_run_installers.go`, during its own package `init`. Go runs an imported package's `init` before the importer's, so a `RegisterInstaller` call from outside the tree would enqueue after the drain, and the installer would never run. The guide describes the out-of-tree form in these terms.

Under `-out-pkg`, the file imports `github.com/nooga/let-go/pkg/rt` and calls `rt.RegisterNS(ns)`. The guide lists these three changes as the only differences from the in-tree output.

At runtime, calling `(xxh3/Hash bytes)` from let-go invokes the wrapper, which converts bytes to Go `[]uint8`, calls the real `Hash`, and returns the result as a let-go number.

Before writing a file, `validateEntries` in `cmd/lginterop/main.go` refuses aliases that are Go keywords or not valid Go identifiers, aliases that collide with the generated file's own `vm` import (or `fmt` under `-smart`), and two aliases that normalize to the same `interop_<alias>.go`. A scanned package with no eligible exports is reported as skipped in the final summary and is not counted as generated.

## Flags

| Flag | Effect |
|---|---|
| `-packages` | Comma-separated import paths to wrap. Overrides `:gointerop` in `deps.edn`. `path=alias` sets a non-default namespace alias. |
| `-dir` | Directory containing the `deps.edn` whose `:gointerop` key lists packages (default `.`). |
| `-out` | Output directory (default `.lg-interop`). |
| `-smart` | Explicit wrappers with type-specific unboxing and boxing, instead of `vm.MustBox`. |
| `-opaque-structs` | Skip `vm.RegisterStruct`. Struct types stay `vm.Boxed`. |
| `-build-tags` | Emit `//go:build <constraint>` as the first line of each generated file. The constraint is recorded in the header. |
| `-out-pkg` | Emit a self-contained package with this name, for use outside the let-go tree. `rt` is refused, because omitting the flag already selects the in-tree `package rt` output. |
| `-skeleton` | Also emit a `<alias>_skeleton.lg` of `defn-` stubs for hand customization. |
| `-primitives`, `-go-pkg`, `-primitives-out` | A separate mode. It scans `//lg:`-annotated Go sources and writes the internal primitive registrar, `pkg/rt/zz_primitives_generated.go` by default. |

The flag list is from `cmd/lginterop/main.go` and `docs/guide/go-interop.md`.

## Smart Wrappers

With `-smart`, a function whose parameters and results are all simple types and whose result arity fits `NativeFnType.Wrap` gets an explicit wrapper with type-specific unboxing and boxing instead of a `vm.MustBox` adapter (`smartable?` in `lginterop.lg`). The simple types are the names in `simple-types`: `string`, `float32`, `float64`, `int` through `int64`, `uint` through `uint64`, `bool`, and `interface {}`. `error` is not in that set. `smartable?` accepts `error` as a second result in its arity check, but its `simple-type?` check on the results runs first and rejects it, so a function with an `error` result falls back to `vm.MustBox` even under the flag. Anything else also falls back to `vm.MustBox`.

## Build tags and TinyGo

`pkg/rt/interop_xxh3.go` is generated with `-build-tags '!tinygo'`, because its reflect-boxed bindings cannot run under TinyGo (guide, flag reference). Under `tinygo && wasm`, `pkg/rt/interop_xxh3_tinygo.go` registers the `xxh3` namespace instead. It contains four functions (`Hash`, `HashSeed`, `HashString`, `HashStringSeed`), built from the hand-written adapters in `pkg/rt/hash_xxh3_wrap.go`. These have the same names and values as the generated ones. The generated namespace also defines `Hash128`, `New`, `NewSeed` and the other 128-bit and hasher functions, which are not in the TinyGo build.

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

[7] **docs/guide/custom-lg.md** — `-import` and `-w-module` for linking an interop package into a build  
https://github.com/nooga/let-go/blob/main/docs/guide/custom-lg.md

[8] **interop_xxh3_tinygo.go** and **hash_xxh3_wrap.go** — TinyGo xxh3 registration  
https://github.com/nooga/let-go/blob/main/pkg/rt/interop_xxh3_tinygo.go  
https://github.com/nooga/let-go/blob/main/pkg/rt/hash_xxh3_wrap.go

[9] **zz_run_installers.go** and **gogen.go** — installer queue drain and gogen registration  
https://github.com/nooga/let-go/blob/main/pkg/rt/zz_run_installers.go  
https://github.com/nooga/let-go/blob/main/pkg/rt/gogen.go

[10] **lginterop_regen_test.go** — round-trip tests for the generated output  
https://github.com/nooga/let-go/blob/main/test/e2e/lginterop_regen_test.go

---

See also: [Go Interop](go-interop.md), [let-go](../entities/let-go.md)
