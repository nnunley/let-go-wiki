---
type: Concept
category: concept
title: "WASM Compilation"
description: "Compiling let-go programs to self-contained WebAssembly pages with bytecode, terminal emulation, and fast startup."
tags: [wasm, compiler, runtime]
resource: "https://github.com/nooga/let-go/tree/main/wasm"
sources: ["repo: nooga/let-go wasm/, docs/guide/usage.md, pkg/bundle, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# WASM Compilation

let-go compiles itself to WebAssembly, enabling programs to run in the browser from the same source as native binaries. A single `lg -w site app.lg` command produces a self-contained `index.html` file (~6MB, inlined and gzipped) that boots the let-go runtime and your bytecode in ~10ms—well within a 60fps frame budget at 16ms per frame.

## Build Process

**Source → Bytecode → WASM Bundle**

1. **Bytecode Compilation**: Source is compiled to bytecode using the standard [bytecode compiler](bytecode-compiler.md) pipeline. The `.lgb` module is generated in-memory.

2. **WASM Bundling** (`pkg/bundle`): The bytecode is embedded into the WASM blob. Resource files (templates, assets) specified by `-resource-paths` are collected and archived alongside the bytecode using the bundle trailer format.

3. **HTML Generation**: The WASM binary (inlined and gzipped), the bytecode, and a `LetGoHost` JavaScript harness are embedded into a single `index.html` file. No external assets are required; the page is self-contained and can be copied anywhere (including served from GitHub Pages).

4. **Service Worker**: A service worker is included to provide COOP/COEP headers needed for SharedArrayBuffer support (required by the let-go runtime for goroutines and channels). The service worker intercepts fetch requests transparently.

## Runtime Environment

When `index.html` loads, it:

1. **Starts during `requestAnimationFrame`** (~10ms available at 60fps): The Go runtime boots, initializes the let-go VM, and loads the embedded bytecode. This tiny budget is why startup must be fast — the WASM runtime footprint is ~6MB compressed, but boot + init is designed to finish in milliseconds.

2. **Initializes the VM**: The let-go stack VM (`pkg/vm`) comes up inside WASM. The bytecode is decoded and registered as functions. Core library (persistent data structures, `core.async`, etc.) is available via precompiled image or embedded bytecode.

3. **Provides Terminal Emulation** (for `term`-using programs): The browser page includes xterm.js for full terminal emulation—ANSI colors, cursor positioning, raw keyboard input, and screen clearing. Calls to `(term/...)` functions interact with the emulated terminal, not the browser console.

4. **Sets up JavaScript Interop**: A global `Eval` function is exposed to JavaScript, allowing the browser to eval let-go code:
   ```js
   window.Eval("(+ 1 2)") // returns "3"
   ```
   This enables live coding in the browser REPL and embedding let-go snippets in web pages.

## Example: Roguelike Game

[xsofy](https://github.com/nooga/xsofy) is a roguelike written in let-go that compiles to both native (terminal) and WASM (browser) from the same source. Run `lg -w www game.lg` and open `www/index.html` in your browser. The game window is a terminal emulation; all game logic runs in let-go bytecode inside the WASM VM.

## Compile-Time Predicates

Programs can branch on compilation target:
- `*compiling-aot*` is `true` during `-w` compilation; `false` at runtime (useful for skipping side effects at compile time).
- `*in-wasm*` is `true` when running inside a WASM build; `false` for native.

Use `:lg` reader conditionals to guard WASM-only or native-only code:
```clojure
#?(:lg (require '[let-go.wasm :as wasm]))  ; only when compiling for WASM
```

# Citations

[1] **wasm/** — WASM entry point and build orchestration  
https://github.com/nooga/let-go/tree/main/wasm

[2] **pkg/bundle** — bytecode and resource bundling  
https://github.com/nooga/let-go/tree/main/pkg/bundle

[3] **docs/guide/usage.md** — `lg -w` build mode  
https://github.com/nooga/let-go/blob/main/docs/guide/usage.md

[4] **README.md** — WASM web apps description  
https://github.com/nooga/let-go#wasm-web-apps

[5] **xsofy** — roguelike example  
https://github.com/nooga/xsofy

[6] **Bytecode Compiler** (this wiki)  
[bytecode-compiler.md](bytecode-compiler.md)

[7] **Stack VM** (this wiki)  
[stack-vm.md](stack-vm.md)

---

See also: [let-go](../entities/let-go.md)
