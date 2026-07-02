# let-go-wiki Index

Catalog of pages by category. Updated on every ingest.

## Entities
- [entities/let-go](entities/let-go.md) — the Clojure-dialect bytecode VM in Go.

## Concepts
- [concepts/bytecode-compiler](concepts/bytecode-compiler.md) — How let-go compiles source code to bytecode: the reader, Indexed-RPN IR intermediate form, and code emission pipeline.
- [concepts/go-interop](concepts/go-interop.md) — Two-way Go ↔ let-go interoperability: calling Go from let-go, embedding let-go in Go, struct/channel roundtripping, and code generation.
- [concepts/indexed-rpn-ir](concepts/indexed-rpn-ir.md) — let-go's intermediate representation: an indexed-RPN (postfix) encoding — an SSA-equivalent form — with block-parameter control flow.
- [concepts/stack-vm](concepts/stack-vm.md) — The stack-based virtual machine that executes let-go bytecode.
- [concepts/wasm-compilation](concepts/wasm-compilation.md) — Compiling let-go programs to self-contained WebAssembly pages with bytecode, terminal emulation, and fast startup.

## Projects
- [projects/legmacs](projects/legmacs.md) — An Emacs-flavored terminal editor written in and scripted with let-go (~4,000 lines) — same language for implementation and config, no separate plugin API.
- [projects/let-go-lab](projects/let-go-lab.md) — Sixel graphics / terminal-UI / WASM experiments on let-go (e.g. a browser Mandelbrot renderer compiled to WASM in xterm.js).
- [projects/lgcr](projects/lgcr.md) — A small Linux container runtime written in let-go, built on the syscall namespace.
- [projects/lgx](projects/lgx.md) — A git-based dependency manager, runner, build tool, test runner, scaffolder, and task runner for let-go in one binary (config in lgx.edn).
- [projects/xsofy](projects/xsofy.md) — A browser-and-terminal roguelike written in let-go where the magic system is a Lisp.

## Ideas
*(none yet)*

## References
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
