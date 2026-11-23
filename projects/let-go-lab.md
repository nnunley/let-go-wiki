---
type: Project
category: project
title: "let-go-lab"
description: "Sixel graphics / terminal-UI / WASM experiments on let-go (e.g. a browser Mandelbrot renderer compiled to WASM that draws to a canvas)."
tags: [wasm, graphics]
resource: "https://github.com/mparrett/let-go-lab"
sources: ["repo: mparrett/let-go-lab README, 2026-07-02", "repo: nooga/let-go pkg/cli/wasm.go pkg/rt/wasm pkg/rt/surface_js_wasm.go pkg/rt/term.go pkg/rt/term_wasm.go pkg/api/api.go docs/guide/usage.md docs/design/runtime-io-host-decoupling.md README.md @ b82588292b, 2026-10-20", "repo: mparrett/let-go-lab README, CLAUDE.md, config/, demos/mandelbrot/, demos/mandelbrot-sixel/ @ 6f64b4ac9 (default branch HEAD, 2026-10-18), 2026-10-20"]
created: "2026-07-02"
updated: "2026-10-20"
status: active
---

# let-go-lab

let-go-lab is a repository of small experiments on [let-go](../entities/let-go.md), a Clojure dialect on a Go bytecode VM. The repository README describes it as experiments on sixel graphics, terminal UI, and wasm-in-the-browser, "decoupled from any one client app" [3]. Its flagship demo is an escape-time Mandelbrot set. In a native terminal that supports sixel, the demo draws the set as sixel graphics. In a browser, the same let-go program compiled to WASM draws to a `<canvas>` [3][4]. A separate demo, `demos/mandelbrot-sixel`, runs the sixel output inside xterm.js in the browser [3]. The README says the browser demos need no install [3].

# Using let-go

let-go-lab uses [let-go](../entities/let-go.md)'s runtime and build targets in these ways:

- **WASM compilation** — `lg -w site app.lg` compiles a program to a self-contained `index.html` of about 6 MB, with the WASM inlined and gzipped, plus a service worker that supplies the COOP/COEP headers needed for SharedArrayBuffer [4]. The lab's browser demos are let-go programs compiled to WASM [3]. The generated page contains JavaScript: a host bundle (`pkg/rt/wasm/lg-host-core.js`) embedded in the page, and, with the default `-w-shell xterm`, an xterm.js shell (`pkg/rt/wasm/lg-shell-xterm.js`) [4]. The Mandelbrot program itself is written in let-go.
- **Sixel output** — let-go at b82588292b has no sixel code. `git grep -i sixel` matches only `docs/design/runtime-io-host-decoupling.md`, which lists graphics (sixel or canvas) as a planned peer capability, scoped in nooga/let-go#255 [4]. The sixel encoder is part of the lab's demo source. `demos/mandelbrot/mandelbrot.lg` streams each frame as a sixel DCS: `render` writes the introducer with `term/write`, then one `term/write` of `encode-band` output and a `term/flush` per band (`encode-band` and `rle-row` do the encoding), then the string terminator (`mandelbrot.lg` lines 334-340) [3]. `build-frame` builds a whole frame as one string; the headless bench uses it (`mandelbrot.lg` lines 284-291) [3].
- **Three branches in `-main`** — `-main` in `demos/mandelbrot/mandelbrot.lg` checks `(surface/available?)` first. When a surface sink is present, it runs the canvas loop (`loop-keys` with `canvas?` true), which calls `render-canvas`. That computes the grid, maps it through a palette into an RGBA buffer, and calls `surface/present` [3]. When `(term/size)` is nil (a non-TTY native run), it runs the headless bench (`run-bench`) [3]. Otherwise it runs `setup!` and the sixel loop (`loop-keys` with `canvas?` false), which calls `render`, which writes sixel to the terminal [3]. Natively, `surface/present` is a no-op unless the host installs a sink (`pkg/api/api.go`, `WithSurface`: "Default: no-op") [4]. Under WASM, the sink is `HostSurface`, which calls the `_lgSurface` global (`pkg/rt/surface_js_wasm.go`) [4].
- **Terminal namespaces on both targets** — the `term` namespace has native and WASM implementations (`pkg/rt/term.go`, `pkg/rt/term_wasm.go`). The demo's setup and teardown calls (`term/raw-mode!`, `term/enable-mouse`, `term/alternate-screen`) are used on both. Under WASM, `raw-mode!` and `restore-mode!` are no-ops and the escape output goes to xterm.js [3][4].
- **Mouse and keyboard input** — `term/enable-mouse` turns on SGR button press and release reporting (1000 and 1006). Natively, `read-key` returns mouse reports as tagged maps (`pkg/rt/term.go:392`). Under WASM, `read-key` returns the raw SGR string (`pkg/rt/term_wasm.go`), and the demo parses it itself (`demos/mandelbrot/mandelbrot.lg` lines 421-428) [3][4]. Drag and motion modes are not enabled [4]. The lab README lists the controls: `+/-` zoom, `hjkl` or arrows pan, `,/.` max iterations, `r` reset, `q` quit, wheel zoom, and click or tap to recenter. A central tap zooms in and an edge tap pans. Shift-click zooms out [3]. The README states that click-to-recenter is exact in the browser, and native where the terminal's cell size can be measured, with keyboard pan and zoom as the fallback [3].

# Repository contents

- `demos/mandelbrot` — escape-time Mandelbrot. Canvas output in the browser, sixel output in a terminal [3].
- `demos/mandelbrot-sixel` — sixel output rendered by xterm.js in the browser, at `/mandelbrot-sixel/` on Pages [3].
- `demos/pathtrace` — a progressive Monte Carlo path tracer. It encodes a PNG and shows it through the iTerm2 inline-image protocol, in xterm.js or natively in iTerm2 [3].
- `demos/ptcanvas` — an allocation-free path tracer with scalar values and flat arrays, ported from a JavaScript original. It draws to a `<canvas>` in the browser [3].
- `demos/mandelbrot-aot` — the Mandelbrot `escape` kernel lowered from `.lg` to native Go with `lg compile`, driven by a Go terminal renderer. The README reports the same output as the VM and about 72× faster [3].
- `experiments/aot`, `experiments/microgpt`, `experiments/cueplay` — the Mandelbrot kernel lowered to native Go and compared against the VM and a hand-written Go port; Karpathy's scalar GPT in one let-go file; and an intro-then-loop audio player on oto with no cgo, which the README gives as the prototype for let-go's native audio binding (nooga/let-go#255) [3].

# Pinned versions

- The browser build uses let-go release `v1.13.0`, from `config/let-go-release` [3].
- The optional native build uses let-go SHA `49858bd247e5277874d3f5bad80c57c756a074d6`, from `config/let-go-native.sha` [3].
- The let-go commit this audit checked, b82588292b, is 90 commits after tag `v1.13.0` (`git describe --tags`) [4].

# Running

- `just play` runs the native TUI and needs a sixel-capable terminal. `just serve` builds the browser version and serves it. Both default to the `mandelbrot` demo and to the `lg` in the symlinked checkout (`./let-go`). The README says browser CI and Pages use the release in `config/let-go-release` [3].
- `just native mandelbrot` builds a native executable at `dist/native/mandelbrot`, using the SHA in `config/let-go-native.sha` [3].

# Idioms

- **Sixel written from let-go source** — the encoder is let-go code in the demo (`demos/mandelbrot/mandelbrot.lg`, `encode-band`, `rle-row`). The runtime calls it makes are `term/write`, and for the canvas path, array operations (`make-array`, `aset`) [3].
- **One program, two output paths** — the canvas path and the sixel path share the palette and the grid computation and differ in how they emit the frame (`surface/present` or `term/write`) [3].
- **WASM as a build target** — `lg -w` produces one HTML file that runs the program in the browser (see Using let-go) [4].

# Open points

- The header comment in `demos/mandelbrot/mandelbrot.lg` says the browser output is sixel in xterm.js and that there is no `<canvas>`. The code selects the canvas path when `surface/available?` is true, and the README says the browser demo draws to a canvas [3]. This page follows the code and the README.
- The Mandelbrot demo link in the citations below points to `mparrett.github.io`. The lab README at 6f64b4ac9 lists `matt.parrett.us/let-go-lab/` as the live index [3]. Neither URL was fetched in this audit.

# Citations

[1] [let-go-lab repository](https://github.com/mparrett/let-go-lab)
[2] [Mandelbrot demo (live browser)](https://mparrett.github.io/let-go-lab/)
[3] mparrett/let-go-lab at 6f64b4ac9 (default branch HEAD, 2026-10-18): [README](https://github.com/mparrett/let-go-lab/blob/6f64b4ac9dea51895de3b98c2190366b0ff1c29f/README.md), `config/let-go-release`, `config/let-go-native.sha`, `demos/mandelbrot/mandelbrot.lg`, `demos/mandelbrot/shell.html`, `demos/mandelbrot-sixel/mandelbrot-sixel.lg`
[4] nooga/let-go at b82588292b (2026-10-18): [README](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/README.md), [WASM web apps in docs/guide/usage.md](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/guide/usage.md), `pkg/rt/surface_js_wasm.go`, `pkg/rt/term.go`, `pkg/rt/term_wasm.go`, `pkg/api/api.go`, `docs/design/runtime-io-host-decoupling.md`
