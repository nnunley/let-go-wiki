# let-go-wiki

A knowledge base for **developing and using [let-go](entities/let-go.md)** — a Clojure dialect with a bytecode compiler and stack VM in Go. Start with the map below; browse everything via the top tabs or the interactive [Graph ↗](https://nnunley.github.io/let-go-wiki/viz.html). The full per-category catalog is at the bottom.

## Start here
- [let-go](entities/let-go.md) — what it is and why it exists
- [Stack VM](concepts/stack-vm.md) · [Bytecode Compiler](concepts/bytecode-compiler.md) — the two anchor concepts

## Developing let-go — internals
The path from source to execution:
[Bytecode Compiler](concepts/bytecode-compiler.md) → [Indexed-RPN IR](concepts/indexed-rpn-ir.md) → [IR Pipeline](concepts/ir-pipeline.md) → [IR Passes](concepts/ir-passes.md) / [IR Optimizations](concepts/ir-optimizations.md) → [Stack VM](concepts/stack-vm.md)

Runtime internals: [Value Representation](concepts/value-representation.md) · [Exec Context](concepts/exec-context.md) · [Concurrency Model](concepts/concurrency-model.md) · [Runtime Image](concepts/runtime-image.md) · [Type Inference](concepts/type-inference.md) · [deftype & Protocols](concepts/deftype-and-protocols.md) · [Debug Info](concepts/debug-info.md) · [.lgb Format](concepts/lgb-bytecode-format.md) · [I/O Host Decoupling](concepts/io-host-decoupling.md)

## Using let-go — building programs
- **Interop:** [Go Interop](concepts/go-interop.md) · [lginterop](concepts/lginterop.md) · [Go Structs](concepts/go-structs.md)
- **Build & run:** [lg-compile](concepts/lg-compile.md) · [WASM Compilation](concepts/wasm-compilation.md) · [nREPL Server](concepts/nrepl-server.md) · [Pods](concepts/pods.md)
- **Compatibility & stdlib:** [Clojure Compatibility](references/clojure-compat.md) · [clojure.core reference](references/clojure.core/map.md)

## Built with let-go
[xsofy](projects/xsofy.md) · [legmacs](projects/legmacs.md) · [lgx](projects/lgx.md) · [lgcr](projects/lgcr.md) · [let-go-lab](projects/let-go-lab.md)

## Roadmap & ideas
[Master Roadmap](ideas/master-plan-roadmap.md) · [Self-hosting AOT](ideas/self-hosting-aot.md) · [Clojure-like Refactor](ideas/clojurelike-refactor.md) · [JVM Compat](ideas/jvm-compat.md) · [malli on let-go](ideas/malli-on-let-go.md) · [nREPL in the Browser](ideas/nrepl-in-browser.md)

## Sources & provenance
Every page cites where its claims come from. The [Sources](sources/let-go-readme.md) section has a summary page per ingested source — the README, design docs, guides, and external IR references — each listing the wiki pages derived from it.

---

# Full catalog
Exhaustive listing by category (the LLM retrieval path; humans use the map above or the top tabs).


## Entities
- [entities/let-go](entities/let-go.md) — A Clojure dialect with a bytecode compiler and stack VM, written in Go.

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
- [concepts/nrepl-server](concepts/nrepl-server.md) — A TCP server exposing let-go's compiler and runtime over the nREPL protocol for editor tooling and interactive development.
- [concepts/pods](concepts/pods.md) — Babashka-compatible external process integration for let-go: loading pods and accessing libraries like SQLite, AWS, Docker, and file watching.
- [concepts/runtime-image](concepts/runtime-image.md) — Precompiled runtime images for fast cold startup and reproducible deployments, including the standard library cache.
- [concepts/stack-vm](concepts/stack-vm.md) — The stack-based bytecode interpreter: operand-stack frames, the fetch-decode-dispatch loop, and specialized arithmetic opcodes.
- [concepts/type-inference](concepts/type-inference.md) — How the let-go compiler infers types during IR lowering and uses a mergeable cache to make parallel lowering both fast and deterministic.
- [concepts/value-representation](concepts/value-representation.md) — How let-go represents values in memory and optimizes numeric operations on the stack VM.
- [concepts/wasm-compilation](concepts/wasm-compilation.md) — Compiling let-go programs to self-contained WebAssembly pages with bytecode, terminal emulation, and fast startup.

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
- [references/testing-conformance](references/testing-conformance.md) — How let-go validates correctness through unit tests, conformance suites, property testing, and performance guardrails.

## Ideas
- [ideas/bytecode-to-go-translation](ideas/bytecode-to-go-translation.md) — Translate let-go bytecode (.lgb) to idiomatic Go source code, enabling faster/native execution paths alongside the stack VM.
- [ideas/clojure-at-your-go-dayjob](ideas/clojure-at-your-go-dayjob.md) — Make it feasible and idiomatic to write Clojure code in Go codebases via two-way interop and single-binary deployment.
- [ideas/clojurelike-refactor](ideas/clojurelike-refactor.md) — Aligning let-go's collection semantics with Clojure through persistent data structures; Phases 1–3 shipped, Phase 4 (transducers) in progress.
- [ideas/jvm-compat](ideas/jvm-compat.md) — A phased plan to run real-world Clojure libraries in let-go by mapping JVM symbol shapes to let-go runtime values.
- [ideas/malli-on-let-go](ideas/malli-on-let-go.md) — Feasibility of running metosin's malli (Clojure data-schema library) on let-go via Babashka-compatible reader branches and Go-backed interop.
- [ideas/master-plan-roadmap](ideas/master-plan-roadmap.md) — Consolidated roadmap toward the fastest and most useful Clojure-on-Go, spanning 9 phases from baseline semantics through Go AOT compilation.
- [ideas/nrepl-in-browser](ideas/nrepl-in-browser.md) — Run the let-go VM in WASM in the browser with an nREPL server reachable over WebSocket, enabling external editor connections to live in-browser runtimes.
- [ideas/self-hosting-aot](ideas/self-hosting-aot.md) — Roadmap for let-go compiling itself ahead-of-time to native Go: using the IR pipeline and Go AOT backend to bootstrap a self-hosted runtime.

## Projects
- [projects/legmacs](projects/legmacs.md) — An Emacs-flavored terminal editor written in and scripted with let-go (~4,000 lines) — same language for implementation and config, no separate plugin API.
- [projects/let-go-lab](projects/let-go-lab.md) — Sixel graphics / terminal-UI / WASM experiments on let-go (e.g. a browser Mandelbrot renderer compiled to WASM in xterm.js).
- [projects/lgcr](projects/lgcr.md) — A small Linux container runtime written in let-go, built on the syscall namespace.
- [projects/lgx](projects/lgx.md) — A git-based dependency manager, runner, build tool, test runner, scaffolder, and task runner for let-go in one binary (config in lgx.edn).
- [projects/xsofy](projects/xsofy.md) — A browser-and-terminal roguelike written in let-go where the magic system is a Lisp.

## Sources
- [sources/design-exec-context](sources/design-exec-context.md) — Design for eliminating goroutine-ID keying and unifying Scope + dynamic-var bindings into an explicitly-threaded ExecContext.
- [sources/design-go-aot-backend](sources/design-go-aot-backend.md) — Design for a second backend that compiles let-go code to Go while preserving runtime semantics and enabling mixed compiled+interpreted execution.
- [sources/design-io-host-decoupling](sources/design-io-host-decoupling.md) — Design for decoupling runtime I/O from concrete host implementations across native, Go embedder, and WebAssembly platforms.
- [sources/design-parallel-lowering](sources/design-parallel-lowering.md) — Investigation into parallelizing IR lowering passes and a proposed mergeable type-discovery cache for deterministic, full-precision parallel compilation.
- [sources/design-pods](sources/design-pods.md) — Babashka-compatible external process integration via EDN-based RPC for script-friendly access to system APIs, databases, and tools.
- [sources/design-runtime-image](sources/design-runtime-image.md) — Design specification for dumping/loading self-contained runtime images and precompiling the standard library for fast startup and reproducible deployments.
- [sources/design-value-representation](sources/design-value-representation.md) — Design documentation on value representation in let-go and performance optimizations for numeric operations in Go.
- [sources/design-vm-performance](sources/design-vm-performance.md) — Design document detailing VM interpreter bottlenecks, calling convention optimization, and a phased plan to reduce GC pressure and improve bytecode call performance.
- [sources/guide-clojure-compatibility](sources/guide-clojure-compatibility.md) — Comprehensive reference documenting let-go's Clojure dialect compatibility, including passing test suite results, supported standard namespaces, unimplemented features, and behavioral differences from JVM Clojure.
- [sources/guide-embedding-in-go](sources/guide-embedding-in-go.md) — Guide to embedding let-go as a scripting layer in Go programs, with struct roundtripping, channel integration, and function interop.
- [sources/guide-resources-and-source-paths](sources/guide-resources-and-source-paths.md) — Guide to let-go resource loading and namespace resolution via `-resource-paths` and `-source-paths` flags.
- [sources/guide-usage](sources/guide-usage.md) — Operational guide for running, compiling, and distributing let-go programs.
- [sources/let-go-readme](sources/let-go-readme.md) — Official project README documenting let-go's design, features, benchmarks, compatibility, and distribution methods.
- [sources/let-go-source-code](sources/let-go-source-code.md) — The core packages of the let-go bytecode compiler and stack VM.
- [sources/plan-clojurelike-refactor](sources/plan-clojurelike-refactor.md) — Staged plan to refactor VM data structures toward Clojure semantics: persistent collections, seq tower, structural equality, and transducers.
- [sources/plan-jvm-compat](sources/plan-jvm-compat.md) — Three-layer architecture for loading real-world Clojure libraries in let-go via class-symbol resolution, protocol fallback, and receiver method dispatch.
- [sources/plan-master](sources/plan-master.md) — Official 9-phase roadmap for let-go development, from baseline semantics through AOT compilation and advanced optimizations.
- [sources/ref-block-param-irs](sources/ref-block-param-irs.md) — Swift SIL, Cranelift, and MLIR — three compiler IRs that employ block parameters instead of phi nodes for SSA-style cross-block value threading.
- [sources/ref-carbon-sem-ir](sources/ref-carbon-sem-ir.md) — Block-parameter SSA intermediate representation design used as reference for let-go's indexed-RPN IR control flow.
- [sources/ref-indexed-rpn-emir](sources/ref-indexed-rpn-emir.md) — Emir's design for positional value numbering in postfix form, the foundation for let-go's IR encoding.
- [sources/testing-and-conformance](sources/testing-and-conformance.md) — Framework, CI, and conformance strategy for testing let-go's clojure.test API, conformance suite, property testing, performance benchmarks, and CI integration.
