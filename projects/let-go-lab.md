---
type: Project
category: project
title: "let-go-lab"
description: "Sixel graphics / terminal-UI / WASM experiments on let-go (e.g. a browser Mandelbrot renderer compiled to WASM in xterm.js)."
tags: [wasm, graphics]
resource: "https://github.com/mparrett/let-go-lab"
sources: ["repo: mparrett/let-go-lab README, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# let-go-lab

let-go-lab is a collection of experimental projects exploring [let-go](../entities/let-go.md)'s capabilities for graphics, terminal UI, and WebAssembly. The flagship demo is an interactive Mandelbrot set visualization that renders via Sixel graphics in native terminals and via xterm.js in web browsers without any installation requirement.

# Using let-go

let-go-lab showcases [let-go](../entities/let-go.md)'s versatility across rendering targets and interaction models:

- **WASM compilation** — the Mandelbrot renderer compiles to self-contained WebAssembly, enabling real-time interactive graphics in a browser without JavaScript.
- **Sixel graphics support** — leverages single-pass encoding to render fractals efficiently in terminal environments that support Sixel, bridging the gap between legacy terminals and modern graphical rendering.
- **Cross-target deployment** — identical let-go code runs natively in terminals and compiles to WASM for browsers, eliminating the need for separate ports or JavaScript rewrites.
- **Interactive I/O** — implements click/tap-to-recenter, keyboard pan/zoom, and iteration adjustment, demonstrating real-time interactivity in both terminal and browser contexts.

# Idioms

- **Sixel as a rendering substrate** — treating Sixel as a first-class rendering target rather than an afterthought shows how [let-go](../entities/let-go.md) can power tools that bridge terminal and graphical interfaces.
- **WASM as a deployment target** — compiling graphics-heavy code to WASM keeps the implementation in a high-level language while maintaining performance in browser environments.

# Citations

[1] [let-go-lab repository](https://github.com/mparrett/let-go-lab)
[2] [Mandelbrot demo (live browser)](https://mparrett.github.io/let-go-lab/)
