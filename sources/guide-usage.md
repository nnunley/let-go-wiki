---
type: Source
category: source
title: "let-go usage guide"
description: "Operational guide for running, compiling, and distributing let-go programs."
tags: [tooling, bytecode, wasm, compiler, reference]
resource: "https://github.com/nooga/let-go/blob/main/docs/guide/usage.md"
sources: ["repo: nooga/let-go docs/guide/usage.md, 2026-07-03", "repo: nooga/let-go docs/guide/usage.md @ 36b13f79, 2026-09-20", "issue: nooga/let-go#796 closed by pr #902, 2026-09-20", "repo: nooga/let-go docs/guide/usage.md @ b82588292b, 2026-10-19", "repo: nooga/let-go pkg/cli/cli.go, pkg/cli/compile.go, pkg/cli/wasm.go @ b82588292b, 2026-10-19", "repo: nooga/let-go pkg/rt/core/lg/commands/compile.lg, pkg/rt/core/lg/compiler.lg @ b82588292b, 2026-10-19", "repo: nooga/let-go cmd/lg-runtime/main.go, pkg/rt/run.go, pkg/bytecode/debug_companion.go @ b82588292b, 2026-10-19", "repo: nooga/let-go pkg/gomod/gomod.go, pkg/rt/lang.go @ b82588292b, 2026-10-19", "repo: nooga/let-go pkg/cli/module.go, pkg/bytecode/decoder.go, pkg/rt/term_wasm.go, test/e2e/runtime_only_test.go @ b82588292b, 2026-10-19", "run: lg dev (b825882) at nooga/let-go b82588292b, 2026-10-20 (lg -w output)"]
created: "2026-07-03"
updated: "2026-10-19"
status: stable
---

# guide-usage

Official documentation covering how to run, compile, and distribute [let-go](../entities/let-go.md) programs.

## What this covers

The guide documents the complete lifecycle of a let-go program:
- **Running programs**: REPL, expression evaluation, file execution with arguments, and `*command-line-args*`
- **Bytecode and standalone binaries**: Compiling to [bytecode-compiler](../concepts/bytecode-compiler.md) format and bundling self-contained executables, with optional DEFLATE-compressed bodies (`-z`) and split debug companions (`-strip`)
- **Compiler-free deployment**: The `lg-runtime` binary, which executes precompiled `.lgb` bytecode with no reader, compiler, or resolver linked in
- **WASM compilation**: Generating web apps with full terminal emulation via xterm.js and COOP/COEP headers for SharedArrayBuffer
- **Native binaries**: `lg compile`, which builds a program into a native executable through the [go-backend](../concepts/go-backend.md)
- **Compile-time evaluation**: Controlling side effects via `*compiling-aot*` and `*in-wasm*` flags
- **Project management**: Using [lgx](../projects/lgx.md) as a dependency resolver, build tool, and test runner

## Key takeaways

- let-go supports interactive (REPL) and compiled distribution modes: bytecode (-c), standalone binary (-b), WASM (-w), and native binary (`lg compile`)
- Standalone binaries are portable copies of the `lg` runtime with bytecode appended—no let-go installation required at runtime. Built with `-bundle-base lg-runtime`, the binary is compiler-free: it cannot evaluate anything beyond the bytecode it was built from (`pkg/cli/cli.go`, added in commit 305487640; nooga/let-go#424, `cmd/lg-runtime/main.go`)
- WASM output includes a service worker for GitHub Pages compatibility and xterm.js for terminal programs
- `lg compile` lowers the program through the Go backend and runs `go build`, so it needs a Go toolchain. Code that does not lower stays on the VM, and the build still succeeds (nooga/let-go#977; `pkg/rt/core/lg/compiler.lg`)
- The `*compiling-aot*` flag separates compile-time setup from runtime execution. The guide now also covers the AOT native-entry case it used to omit: build the embedded bytecode with `lg -c program.lgb -entry-frame-entry ns/-main app.lg`, which drops the selected entry call so the guarded top-level call does not run a second time under the native frame (#796, closed by #902; see [wasm-compilation](../concepts/wasm-compilation.md))
- lgx provides a git-based, multi-file project workflow with scaffolding and task running

## Derived pages

[bytecode-compiler](../concepts/bytecode-compiler.md) · [let-go](../entities/let-go.md) · [wasm-compilation](../concepts/wasm-compilation.md) · [lgx](../projects/lgx.md) · [go-backend](../concepts/go-backend.md) · [lg-compile](../concepts/lg-compile.md) · [lgb-bytecode-format](../concepts/lgb-bytecode-format.md) · [debug-info](../concepts/debug-info.md)

## Running programs

The `lg` binary runs a REPL, evaluates an expression, or runs a file with arguments. `-r` runs the given files and then attaches the REPL.

`*command-line-args*` holds the positionals after the script as a seq of strings, or `nil` when there are none. The entry point computes it once for both a script and a bundled binary (`pkg/rt/run.go`, `SetCommandLineArgs`; the var was added in nooga/let-go#205).

## Bytecode and standalone binaries

`lg -c` writes bytecode and `lg -b` writes a standalone binary. `-z` is opt-in and applies to both. The header remains plaintext for early compatibility checks; the bytecode body is DEFLATE-compressed and inflated transparently by `lg` and `lg-runtime` (`pkg/cli/cli.go`, `-z`; `pkg/bytecode/decoder.go`; compression added in nooga/let-go#501).

The standalone binary is a copy of `lg` with your bytecode appended — copy it to another machine and it runs.

### Split debug information

`-strip` keeps the runtime artifact small without permanently losing its source maps or local-variable tables. It works with `-c`, `-b`, and `-w` (nooga/let-go#624; `-w` added in nooga/let-go#800):

```bash
lg -strip -c app.lgb app.lg       # app.lgb + app.lgb.debug
lg -strip -b myapp app.lg         # myapp + myapp.debug
lg -strip -debug-output symbols/app.debug -c app.lgb app.lg
```

The `.debug` companion is bound to the exact stripped payload by SHA-256 (`pkg/bytecode/debug_companion.go`). Keep it in build artifacts or a symbol store while distributing only the stripped `.lgb` or executable. A companion beside the runtime artifact is loaded automatically; set `LG_DEBUG_FILE` to load it from another path, or set the variable to an empty value to run without debug information. Mismatched companions are rejected rather than producing misleading stack traces: the SHA-256 digest comparison in `pkg/bytecode/debug_companion.go` fails with "debug companion does not match stripped LGB (SHA-256 mismatch)", and `DecodeExecUnitWithDebug` in `pkg/rt/run.go` passes the companion to that check. `LoadDebugCompanion` in `pkg/rt/run.go` only chooses the path (`LG_DEBUG_FILE` or `<artifact>.debug`) and reads the bytes.

## Compiler-free deployment: lg-runtime

`lg-runtime` executes precompiled `.lgb` bytecode with no reader, compiler, or resolver linked in. The guarantee is structural — the binary never links `pkg/compiler` or `pkg/resolver`, and `TestRuntimeOnlyDepGraph` checks this mechanically — so the deployed artifact has no `eval`, `load-string`, `read-string`, or dynamic source `require`: it runs only bytecode compiled ahead of time by a toolchain you trust (`cmd/lg-runtime/main.go`; `test/e2e/runtime_only_test.go`; nooga/let-go#424).

```bash
go build -o lg-runtime ./cmd/lg-runtime      # build the runtime-only binary

lg -c app.lgb app.lg                         # compile on your machine
lg-runtime app.lgb a b                       # run it, compiler-free

lg -b myapp -bundle-base lg-runtime app.lg   # standalone AND compiler-free
./myapp
```

With `-bundle-base`, the standalone binary appends your bytecode to `lg-runtime` instead of the full `lg`, so the shipped executable cannot evaluate anything beyond what you compiled. The flag also selects a target-platform binary for cross-OS bundling (`pkg/cli/cli.go`, `-bundle-base`, added in commit 305487640 at b82588292b).

## WASM web apps

```bash
lg -w site app.lg                 # compile to a WASM web app
open site/index.html
```

By default the output is an `index.html` (8.4 MB for the app built in the run, run: lg dev (b825882) at nooga/let-go b82588292b, 2026-10-20) with the WASM module gzip-base64 encoded and inlined, plus a `coi-serviceworker.js` written beside it that supplies the COOP/COEP headers GitHub Pages needs for SharedArrayBuffer. The default `xterm` shell loads xterm.js and its CSS from cdn.jsdelivr.net, so that page is not offline-self-contained (observed in the run's output). `-w-wasm external` emits a separate `main.wasm` that the loader fetches and streams instead. `-w-shell` selects the page shell: `xterm` (the default), `none` (core only; the client supplies its own shell through `window.LetGoHost`), or a path to a custom HTML template. `-w-host-eval` exposes `LetGoHost.eval(code)` and keeps the loaded image live after `main` returns (`pkg/cli/cli.go`, the `-w-*` flags).

Programs that use the `term` namespace get full terminal emulation via xterm.js: ANSI colors, cursor positioning, raw keyboard input.

## Native binaries

`lg compile` builds a program into a standalone native executable through the [go-backend](../concepts/go-backend.md). It needs a Go toolchain: the one under `GOROOT` when the `lg` binary records it, otherwise `go` on `PATH` (`pkg/gomod/gomod.go`, `GoToolPath`). The command is dispatched only when `compile` is the exact first argument, so `lg compile` is distinct from a script named `compile` (nooga/let-go#977; `pkg/cli/compile.go`).

```bash
lg compile app.lg                 # writes ./app
lg compile -o bin/app app.lg      # choose the output path
lg compile -work gen app.lg       # keep the generated Go module in gen/
```

Without `-o`, the output is the entry file's name with no `.lg` suffix. On success the command prints `built <out>`. The `-work` directory holds the generated module and is kept; without it, a temporary directory is used and removed.

One input must define `-main` or `main`, which the binary calls natively. Code that lowers runs as Go; what does not lower stays on the VM, and the build still succeeds (`build-program` in `pkg/rt/core/lg/compiler.lg`). The generated module requires the let-go this `lg` came from: a release pins its own version, and a dev build uses `LETGO_SRC` or the checkout it finds, as `-w` does (`writeGoModule` in `pkg/cli/wasm.go`). Pass several files when the program's own namespaces should lower too; namespaces you don't pass run from bytecode.

The program's bytecode, `program.lgb`, is written by a child `lg -c -entry-frame-entry` process rather than in-process, because lowering loads the compiler's own namespaces and an in-process compile would bundle them (`compileLGBSubprocess` in `pkg/cli/compile.go`). `lg compile` shares the Go lowering step (`compile-program` in `pkg/rt/core/lg/compiler.lg`) with the separate [lg-compile](../concepts/lg-compile.md) script, which has its own argv and output contract.

To build inside a Go module you manage, pass `-module dir`. lg then writes only `<dir>/lgprogram`, uses the module's `go.mod` and `go.sum` as they are, and builds with `-mod=readonly`. Each `-import pkg` blank-imports a Go package for its `init()`, so its namespaces register; the module must already require it. `-work` and `-module` are mutually exclusive (`lg.commands.compile`, `pkg/rt/core/lg/commands/compile.lg`).

## Compile-time vars

`*compiling-aot*` is `true` during `-c`/`-b`/`-w` compilation and `false` during ordinary runtime execution, useful for keeping side effects out of compile time (`pkg/cli/cli.go`; default in `pkg/rt/lang.go`):

```clojure
(defn -main []
  (start-server))

(when-not *compiling-aot*
  (-main))
```

`lg compile` does the following step for you. When driving the pipeline by hand, compile the embedded bytecode with `lg -c program.lgb -entry-frame-entry app/-main app.lg` (use `app/main` when that is the selected entry). `-entry-frame-entry` requires `-c` and a `namespace/main` or `namespace/-main` value. This omits the selected top-level entry call from the bytecode because the native frame calls it. Other top-level forms, including guarded initialization in required namespaces, run with `*compiling-aot*` false at runtime. Ordinary `lg -c` keeps the entry call (`pkg/cli/cli.go`; nooga/let-go#902, nooga/let-go#977).

`*in-wasm*` is `true` when running inside a WASM build (`pkg/rt/term_wasm.go`).

## Project management with lgx

For multi-file projects with dependencies, [lgx](https://github.com/abogoyavlensky/lgx)
is a git-based package and project manager for let-go — dependency resolution,
runner, build tool, test runner, scaffolder, and task runner in one binary:

```bash
lgx new myapp                     # scaffold a project
lgx install                       # install deps from lgx.edn
lgx run                           # fetch deps, run :main
lgx build                         # bundle a standalone binary
lgx test                          # run tests under test/
```

## Citations

Source: https://github.com/nooga/let-go/blob/main/docs/guide/usage.md (verified 2026-07-03; sections on standalone, lg-runtime, `-z`/`-strip`, and the compile-time vars re-checked at b82588292b, 2026-10-19)

Source code checked at b82588292b, 2026-10-19: `docs/guide/usage.md`, `pkg/cli/cli.go`, `pkg/cli/compile.go`, `pkg/cli/wasm.go`, `pkg/rt/core/lg/commands/compile.lg`, `pkg/rt/core/lg/compiler.lg`, `pkg/rt/run.go`, `pkg/rt/lang.go`, `pkg/bytecode/debug_companion.go`, `pkg/bytecode/decoder.go`, `pkg/cli/module.go`, `pkg/gomod/gomod.go`, `pkg/rt/term_wasm.go`, `cmd/lg-runtime/main.go`, `test/e2e/runtime_only_test.go`.
