# let-go-wiki Index

Catalog of pages by category. Updated on every ingest.

## Entities
- [entities/let-go](entities/let-go.md) — the Clojure-dialect bytecode VM in Go.

## Concepts
- [concepts/bytecode-compiler](concepts/bytecode-compiler.md) — How let-go compiles source code to bytecode: the reader, Indexed-RPN IR intermediate form, and code emission pipeline.
- [concepts/concurrency-model](concepts/concurrency-model.md) — Goroutine-local dynamic bindings and scoped async supervision for concurrent namespace and binding isolation.
- [concepts/debug-info](concepts/debug-info.md) — Mapping bytecode back to source locations and local variable names for readable crash traces and error reporting.
- [concepts/deftype-and-protocols](concepts/deftype-and-protocols.md) — Custom types and protocol-based polymorphism in let-go, unifying Clojure's deftype/defprotocol with native Go lowering.
- [concepts/exec-context](concepts/exec-context.md) — How the ExecContext carries execution state (scopes and dynamic bindings) through the VM, threaded rather than stored in goroutine-local maps.
- [concepts/go-interop](concepts/go-interop.md) — Two-way Go ↔ let-go interoperability: calling Go from let-go, embedding let-go in Go, struct/channel roundtripping, and code generation.
- [concepts/go-structs](concepts/go-structs.md) — Defining and using Go structs from let-go via compile-time code generation.
- [concepts/indexed-rpn-ir](concepts/indexed-rpn-ir.md) — let-go's intermediate representation: an indexed-RPN (postfix) encoding — an SSA-equivalent form — with block-parameter control flow.
- [concepts/io-host-decoupling](concepts/io-host-decoupling.md) — How the runtime decouples I/O operations from the host platform, enabling the same runtime to run natively, in WASM, and on exotic hosts.
- [concepts/ir-optimizations](concepts/ir-optimizations.md) — Lambda lifting and higher-order specialization to eliminate dynamic dispatch and closure allocation in combinator-based code.
- [concepts/ir-passes](concepts/ir-passes.md) — Lisp-implemented optimization passes that transform the semantic IR to improve runtime performance.
- [concepts/ir-pipeline](concepts/ir-pipeline.md) — let-go's compiler IR framework, written in let-go itself: building, optimizing, and lowering to bytecode.
- [concepts/lg-compile](concepts/lg-compile.md) — Ahead-of-time compilation of let-go source files to Go packages with cross-package function calls.
- [concepts/lgb-bytecode-format](concepts/lgb-bytecode-format.md) — Binary serialization format for let-go compiled code, with per-tag versioning, batch collection decoding, and capability-mask extensibility.
- [concepts/lginterop](concepts/lginterop.md) — Wrapping Go packages as callable functions in let-go via code generation.
- [concepts/pods](concepts/pods.md) — Babashka-compatible external process integration for let-go: loading pods and accessing libraries like SQLite, AWS, Docker, and file watching.
- [concepts/runtime-image](concepts/runtime-image.md) — Precompiled runtime images for fast cold startup and reproducible deployments, including the standard library cache.
- [concepts/stack-vm](concepts/stack-vm.md) — The stack-based virtual machine that executes let-go bytecode.
- [concepts/type-inference](concepts/type-inference.md) — How the let-go compiler infers types during IR lowering and uses a mergeable cache to make parallel lowering both fast and deterministic.
- [concepts/value-representation](concepts/value-representation.md) — How let-go represents values in memory and optimizes numeric operations on the stack VM.
- [concepts/wasm-compilation](concepts/wasm-compilation.md) — Compiling let-go programs to self-contained WebAssembly pages with bytecode, terminal emulation, and fast startup.

## Projects
- [projects/legmacs](projects/legmacs.md) — An Emacs-flavored terminal editor written in and scripted with let-go (~4,000 lines) — same language for implementation and config, no separate plugin API.
- [projects/let-go-lab](projects/let-go-lab.md) — Sixel graphics / terminal-UI / WASM experiments on let-go (e.g. a browser Mandelbrot renderer compiled to WASM in xterm.js).
- [projects/lgcr](projects/lgcr.md) — A small Linux container runtime written in let-go, built on the syscall namespace.
- [projects/lgx](projects/lgx.md) — A git-based dependency manager, runner, build tool, test runner, scaffolder, and task runner for let-go in one binary (config in lgx.edn).
- [projects/xsofy](projects/xsofy.md) — A browser-and-terminal roguelike written in let-go where the magic system is a Lisp.

## Ideas
- [ideas/bytecode-to-go-translation](ideas/bytecode-to-go-translation.md) — Translate let-go bytecode (.lgb) to idiomatic Go source code, enabling faster/native execution paths alongside the stack VM.
- [ideas/clojure-at-your-go-dayjob](ideas/clojure-at-your-go-dayjob.md) — Make it feasible and idiomatic to write Clojure code in Go codebases via two-way interop and single-binary deployment.
- [ideas/malli-on-let-go](ideas/malli-on-let-go.md) — Feasibility of running metosin's malli (Clojure data-schema library) on let-go via Babashka-compatible reader branches and Go-backed interop.
- [ideas/nrepl-in-browser](ideas/nrepl-in-browser.md) — Run the let-go VM in WASM in the browser with an nREPL server reachable over WebSocket, enabling external editor connections to live in-browser runtimes.
- [ideas/self-hosting-aot](ideas/self-hosting-aot.md) — Roadmap for let-go compiling itself ahead-of-time to native Go: using the IR pipeline and Go AOT backend to bootstrap a self-hosted runtime.


## References
- [references/clojure-compat](references/clojure-compat.md) — Where let-go IS and ISN'T compatible with Clojure JVM: known limitations, feature parity, and behavioral differences.
- [references/clojure.core/apply](references/clojure.core/apply.md) — Applies a function to a sequence of arguments, unpacking the final argument list.
- [references/clojure.core/comp](references/clojure.core/comp.md) — Composes functions, returning a new function that applies them from right to left.
- [references/clojure.core/defn](references/clojure.core/defn.md) — Defines a named function and binds it to the current namespace.
- [references/clojure.core/filter](references/clojure.core/filter.md) — Returns a lazy sequence of elements from a collection that satisfy a predicate.
- [references/clojure.core/fn](references/clojure.core/fn.md) — Creates an anonymous function with specified parameters and body.
- [references/clojure.core/inc](references/clojure.core/inc.md) — Returns the next integer, adding 1 to the argument.
- [references/clojure.core/let](references/clojure.core/let.md) — Binds local variables to values within a limited scope.
- [references/clojure.core/map](references/clojure.core/map.md) — Returns a lazy sequence of results applying a function to elements of one or more collections.
- [references/clojure.core/mapv](references/clojure.core/mapv.md) — Like map, but returns a vector instead of a lazy sequence.
- [references/clojure.core/partial](references/clojure.core/partial.md) — Creates a new function with some arguments already supplied.
- [references/clojure.core/when](references/clojure.core/when.md) — Evaluates body forms only if the condition is truthy, otherwise returns nil.

## Sources
*(none yet)*
