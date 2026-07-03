---
type: Idea
category: idea
title: "nREPL in the Browser"
description: "Run the let-go VM in WASM in the browser with an nREPL server reachable over WebSocket, enabling external editor connections to live in-browser runtimes."
tags: [wasm, tooling]
resource: "https://github.com/nooga/let-go#goals"
sources: ["repo: nooga/let-go README (Goals), docs/guide/nrepl.md, docs/superpowers/plans/2026-06-29-browser-inspector-nrepl-bridge.md, docs/superpowers/specs/2026-06-29-browser-inspector-nrepl-bridge-design.md"]
created: "2026-07-02"
updated: "2026-07-02"
status: speculative
---

# nREPL in the Browser

## What It Is

Expose an nREPL server from the [let-go VM](../concepts/stack-vm.md) running in WASM inside the browser, connected to editors via WebSocket. This allows a developer to run `lg -n` (or equivalent) on a live in-browser runtime, then connect CIDER, Calva, or Conjure over WebSocket to evaluate Clojure forms directly against that browser-hosted VM.

## Why It Matters

Today, let-go's nREPL server only runs locally (native process), forcing developers to choose: either native development with REPL tooling, or browser-based work without live connection. Making nREPL available over WebSocket in the browser enables:

- **Live coding in the browser**: Developers can connect their editor to a running web app and iterate without page reloads.
- **Debugging web scripts**: Inspect and modify let-go code running inside a game, canvas app, or simulator in real time.
- **Unified workflow**: Same editor setup (Emacs, VS Code, Neovim) works whether the runtime is native or in-browser.
- **Bridge to web workflows**: Brings REPL-driven development to pure web environments (GitHub Codespaces, Gitpod, cloud IDEs).

## Building Blocks in Place

- **[WASM Compilation](../concepts/wasm-compilation.md)**: let-go already compiles to WASM and boots the VM in the browser (~10ms). The runtime is fully functional.
- **[nREPL Server](../concepts/nrepl-server.md)** (native): let-go ships an nREPL server (`lg -n`, `lgx nrepl`) that works with standard editors. The protocol layer and operations (eval, describe, completions) are proven.
- **Browser Inspector / nREPL Bridge**: A request/response bridge from the browser JS layer to the in-WASM runtime (JSON frames, sequential form evaluation) is being designed internally; it extends the public [nREPL server](../concepts/nrepl-server.md) seam and can grow to stream nREPL operations.
- **[LetGoHost Glue](https://github.com/nooga/let-go/blob/main/wasm/main.go)**: Browser-to-WASM JavaScript interop is already wired. A WebSocket layer and nREPL adapter are the main additions.

## Open Questions

- **WebSocket transport**: How does the browser JavaScript open a WebSocket to itself? (Answer: typically a Node.js dev server or a shared worker; or reverse: the WASM runtime pushes frames to a listener registered in JS.)
- **Multi-tab / multi-session isolation**: Do separate browser tabs get isolated nREPL sessions, or do they share state? (Likely per-tab for simplicity in the first cut.)
- **Backward compatibility**: Keep `LetGoHost.eval()` (the current browser eval hook) working unchanged while adding streamed nREPL ops on top.
- **Editor discovery**: How do editors discover an in-browser nREPL? (Likely manual connection or a bookmarklet / local proxy.)

## Roadmap Motivation

From the README Goals: `[ ] nREPL in the browser (let-go VM in WASM, editor over WebSocket)`. This is a high-leverage feature for bringing Clojure REPL workflows to pure web development and single-page applications.

---

# Citations

[1] **README Goals** — the unchecked roadmap item  
https://github.com/nooga/let-go#goals

[2] **docs/guide/nrepl.md** — native nREPL server  
https://github.com/nooga/let-go/blob/main/docs/guide/nrepl.md

[3] **pkg/nrepl/server.go** — the native nREPL server the browser bridge extends  
https://github.com/nooga/let-go/blob/main/pkg/nrepl/server.go

[4] **wasm/main.go** — LetGoHost browser/WASM glue the bridge builds on  
https://github.com/nooga/let-go/blob/main/wasm/main.go

[5] **WASM Compilation** (this wiki)  
[wasm-compilation.md](../concepts/wasm-compilation.md)

[6] **Stack VM** (this wiki)  
[stack-vm.md](../concepts/stack-vm.md)

[7] **let-go** (this wiki)  
[let-go.md](../entities/let-go.md)

---

See also: [nREPL Server](../concepts/nrepl-server.md), [let-go](../entities/let-go.md), [WASM Compilation](../concepts/wasm-compilation.md), [Stack VM](../concepts/stack-vm.md)
