---
type: Concept
category: concept
title: "lg-compile"
description: "Ahead-of-time compilation of let-go source files to Go packages with cross-package function calls."
tags: [compiler, tooling, go]
resource: "https://github.com/nooga/let-go/blob/main/scripts/lg-compile"
sources: ["repo: nooga/let-go scripts/lg-compile, pkg/rt/core/ir/lower_go.lg (lowering), 2026-07-02", "repo: nooga/let-go scripts/lg-compile, pkg/rt/core/lg/compiler.lg, pkg/rt/core/ir/passes/pipeline.lg, pkg/rt/core/ir/lower_go.lg @ b82588292b, 2026-10-19", "repo: nooga/let-go docs/guide/usage.md @ b82588292b, 2026-10-19", "run: lg dev (b825882) at nooga/let-go b82588292b, 2026-10-20 (--entry-frame stdout line)"]
created: "2026-07-02"
updated: "2026-10-19"
status: stable
---

# lg-compile

`lg-compile` is a let-go script that AOT-compiles a set of `.lg` source files into Go packages. The script is a thin command-line shim. It parses its arguments and calls the `lg.compiler` namespace (`pkg/rt/core/lg/compiler.lg`), which is embedded in every `lg` binary, so the script runs without a let-go checkout on disk ([6]). Unlike the standard bytecode compiler (which produces `.lgb` files or standalone binaries), `lg-compile` generates a tree of `.go` files with **direct inter-package function calls** (`pkg.Fn(ec, ...)` in Go) instead of runtime trampoline indirection.

This is useful for embedding let-go-authored code as native Go libraries, reusing let-go logic from Go programs, or compiling multi-file let-go projects to a Go package hierarchy.

## Usage

```bash
./lg scripts/lg-compile [--entry-frame] <out-dir> <import-prefix> <file.lg>...
```

**Parameters:**

- `--entry-frame` — optional. Also emit `<out-dir>/main.go`, a native-entry frame for the program's `-main` (or `main`); the run prints `native-entry frame -> <out>/main.go` on stdout. Without the flag, only the lowered packages are written. The orchestrator places `program.lgb` beside `main.go` before `go build` ([6]).
- `<out-dir>` — output directory for the generated Go package tree
- `<import-prefix>` — Go import path prefix (each package is `<import-prefix>/<reldir>`)
- `<file.lg>...` — one or more `.lg` files to compile

**Output and exit status:** each package that is written prints a line `<file> -> <path>`. A namespace whose functions do not lower prints `EMIT-FAIL <file> pkg=<pkg> returned <type>`. Its functions stay on the VM, and the script still exits 0. A namespace with no lowerable `defn`, `defn-`, `defmulti` or `defmethod` is skipped with a message. Only a fatal error exits 1, such as an unsupported entry arity when `--entry-frame` is given ([6]). External tools scrape `EMIT-FAIL` from stdout, so the printed lines and the exit status are a compatibility contract (`pkg/rt/core/lg/compiler.lg`, `exit-code`).

**Example:**

```bash
./lg scripts/lg-compile /tmp/out github.com/example/generated-api \
  api/core.lg api/handlers.lg
```

Each `.lg` file's namespace becomes a Go package under `<out-dir>`. For example:

- `api/core.lg` (ns `api.core`) → `<out-dir>/api/core/core.go` (package `core`)
- `api/handlers.lg` (ns `api.handlers`) → `<out-dir>/api/handlers/handlers.go` (package `handlers`)

The directory is the namespace path with dots as separators, and the package name is its last segment, with hyphens turned into underscores (`gogen/ns->go-reldir`, `gogen/ns->go-pkg`, [6]). A file with no `ns` form gets a synthetic `ys_<stem>` package.

The generated Go packages are importable:

```go
import "github.com/example/generated-api/api/core"

// Call compiled let-go functions directly
result, err := core.MyFunction(ec, arg1, arg2)
```

## Compile Paths Comparison

| Path | Command | Output | Use Case |
|------|---------|--------|----------|
| **Bytecode** | `lg -c app.lgb app.lg` | `.lgb` (binary module) | Distribute bytecode, run with `lg app.lgb` |
| **Standalone binary** | `lg -b myapp app.lg` | Self-contained executable | Single-file distribution, no let-go runtime needed |
| **Native binary** | `lg compile app.lg` | Native executable built through the Go backend ([7]) | Native distribution; needs a Go toolchain on `PATH`. Code that does not lower stays on the VM |
| **WASM** | `lg -w site app.lg` | `index.html` (~6MB, embedded bytecode + WASM) | Web apps, browser deployment |
| **Go package** | `lg scripts/lg-compile <out> <prefix> app.lg` | `.go` package tree | Embed in Go programs, direct function calls |

`lg compile` is a separate path from the script. It builds a single program into an executable by writing a Go module and running `go build` on it. It reuses the same Go lowering (`compile-program` in `pkg/rt/core/lg/compiler.lg`), and it writes the same per-namespace package tree into its work directory. That tree is an internal build step, not a library the caller places. It uses a fixed `lgprogram` import prefix, and `-work <dir>` keeps the generated module (`lg compile -work gen app.lg`, [7], [6]). The script differs in that the caller chooses `<out-dir>` and `<import-prefix>`, so its output is a library ([7], [6]).

## How It Works

`lg-compile` (a let-go script) runs the `lg.compiler` driver, which orchestrates the full-program lowering pipeline ([6]):

1. **Parse** each `.lg` file. The whole file is read as one `(do …)` form, so a file cut off inside an open form is an error, not a shorter program (#1021). The `ns` form gives the namespace, and the file's lowerable forms are kept.
2. **Load** the namespaces in dependency order. The inputs are sorted on their `require` and `use` clauses, so the order on the command line does not matter. Only definitional forms are evaluated (`ns`, `def`, `defn`, `defmacro`, `require`, and similar), so top-level expressions are not run at compile time. Top-level macro calls are macroexpanded, though, and `macroexpand-1` runs the macro's own code at compile time (`definitional-forms!` in `pkg/rt/core/lg/compiler.lg`). Top-level forms are macroexpanded first, so a `defn` that a macro emits, or one wrapped in `do`, is loaded and lowered ([#1049](https://github.com/nooga/let-go/pull/1049), [#1052](https://github.com/nooga/let-go/pull/1052)). A definition nested in another form, such as `(when c (defn …))`, is not loaded; the script prints a warning.
3. **Lower** all namespaces together through `ir.passes.pipeline/lower-all-ns-to-go-result` ([8]), with `*target*` set to `:go`. The first phase collects each namespace's direct-callable exports and its cross-package references. The second phase lowers each namespace with that registry visible. Each form goes through the IR pipeline (`compile-form*`) and `ir.lower-go/lower` (converting IR to Go AST, [2]).
4. **Emit `.go` files** organized by namespace/package, with:
   - Go functions for each let-go defn, taking `*ExecutionContext` as first argument
   - Direct inter-package calls where both functions are in the generated tree
   - Fallback trampolines for functions not eligible for direct calls (e.g., variadic functions, or `^:dynamic` and `^:redef` defns)
   - Necessary imports and Go build scaffolding
5. **Frame** (only with `--entry-frame`): emit `main.go` with a native-entry frame for the program's entry, plus a bridge file when the entry is private.

The generated code is valid Go that can be imported and linked into any Go program. A function whose parameters and result are all `vm.Value` takes `ec` and its arguments and returns `vm.Value`. It also returns an `error` when its body contains an error-producing call or `try` (`function-needs-error?`), which is the case for the `(vm.Value, error)` example above. The error result is gated on `function-needs-error?` in both the result list and the `return` statement (`pkg/rt/core/ir/lower_go.lg`, `result-node` and `return-stmt`). A function with typed parameters or a typed result is emitted with Go types, for example `func f(ec, x int) int`. Its call sites are direct calls when the argument types are proven. An unproven `vm.Value` argument into a typed scalar parameter gets a type-guarded direct call: comma-ok type assertions on the boxed arguments, the static call when they all hold, and the trampoline fallback when a runtime type does not match. The plain trampoline is used only when an argument cannot be coerced at all, or when a parameter or result type is not coercion-supported (`override-coercible?` and `emit-typed-direct-call` in `pkg/rt/core/ir/lower_go.lg`).

## Cross-Package Calls

When function A (in package `api.core`) calls function B (also in the generated tree, in package `api.handlers`), `lg-compile` emits a direct Go call:

```go
result, err := handlers.MyFunction(ec, arg1, arg2)  // direct call, not trampoline
```

A public defn is exported under its PascalCase name, and a private one keeps a lowercase name. The direct call uses that name, with no forwarding wrapper (`pkg/rt/core/ir/passes/pipeline.lg`, the ITER-0037 note in the package-emit code). This avoids runtime Var lookups and enables inlining by Go's compiler.

Direct linking has these limits:

- **Variadic** functions are not direct-callable. They fall back to cached-var trampolines at runtime (`rt.CachedVarFnEC`).
- **`^:dynamic` and `^:redef` defns** are never linked directly, as in Clojure. Calls to them go through the var, which is dereferenced in the caller's execution context, so a `binding` takes effect as it does under bytecode ([#1017](https://github.com/nooga/let-go/pull/1017)).
- **Other siblings** are linked directly, as Clojure links them. A redefinition with `with-redefs`, `alter-var-root` or `def` reaches lowered callers only after they are recompiled.
- **Import cycles:** a cross-package call that would close an import cycle keeps trampolining. `lower-all-ns-to-go-result` in `pkg/rt/core/ir/passes/pipeline.lg` takes the transitive closure of the candidate call graph (`cross-pkg-dep-graph` and `transitive-reach`) to find these.

## Citations

[1] **lg-compile** — AOT compiler to Go packages (let-go script)  
https://github.com/nooga/let-go/blob/main/scripts/lg-compile

[2] **ir.lower-go** — IR → Go AST lowering (let-go module)  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg

[3] **Bytecode Compiler** (this wiki)  
[bytecode-compiler.md](bytecode-compiler.md)

[4] **WASM Compilation** (this wiki)  
[wasm-compilation.md](wasm-compilation.md)

[5] **let-go** (this wiki)  
[../entities/let-go.md](../entities/let-go.md)

[6] **lg.compiler** — the AOT compile driver namespace, which `scripts/lg-compile` calls (let-go core namespace; added in [#735](https://github.com/nooga/let-go/pull/735))  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/lg/compiler.lg

[7] **Usage: native binaries** — `lg compile` (let-go guide; added in [#977](https://github.com/nooga/let-go/pull/977))  
https://github.com/nooga/let-go/blob/main/docs/guide/usage.md

[8] **ir.passes.pipeline** — whole-program Go lowering, direct-call registry, and cross-package emit (let-go module)  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/pipeline.lg

---

See also: [Bytecode Compiler](bytecode-compiler.md), [WASM Compilation](wasm-compilation.md), [Go backend](go-backend.md), [let-go](../entities/let-go.md)
