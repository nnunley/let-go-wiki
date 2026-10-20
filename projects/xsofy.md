---
type: Project
category: project
title: "Xs of Y (xsofy)"
description: "A browser-and-terminal roguelike written in let-go where the magic system is a Lisp."
tags: [roguelike, wasm, lisp]
resource: "https://github.com/nooga/xsofy"
sources: ["repo: nooga/xsofy README.md, 2026-07-02", "repo: nooga/xsofy Makefile, .let-go-version, tools/, .github/workflows/deploy-pages.yml, .github/workflows/pr-preview.yml, .github/actions/build-wasm @ 0c38395422, 2026-10-20", "repo: nooga/let-go README.md, pkg/vm/persistent_vector.go, pkg/vm/persistent_map.go, pkg/vm/persistent_set.go, pkg/vm/persistent_queue.go, pkg/cli/cli.go, pkg/cli/wasm.go, pkg/gomod/gomod.go, pkg/rt/wasm/embed.go, pkg/rt/wasm/shell.go @ b82588292b, 2026-10-20"]
created: "2026-07-02"
updated: "2026-10-20"
status: stable
---

# Xs of Y (xsofy)

xsofy is a roguelike written in [let-go](../entities/let-go.md), notable because
its magic system *is* a Lisp. Every run generates a new title (*Gazebos of
Mounting Dread*), a new quest (*retrieve the Spatula of Futility*), and a new set
of rune mappings — the runes are secretly symbols, and spells are s-expressions.
You have root access to the dungeon's reality engine, but the man pages are in a
dead language that changes every boot. The power curve is inverted: early game is
desperate survival, late game is applied theology. It runs
[in the browser](https://nooga.github.io/xsofy/) and in the terminal from the
same source, and its main visual inspiration is
[Brogue](https://sites.google.com/site/broguegame/).

# Using let-go

xsofy is a complete game and a real program that uses let-go's core properties.
README claims cite [1]; build, workflow, and pin claims cite xsofy files at
0c38395422 [4]; PR claims cite [5] and [6]; let-go claims cite let-go at
b82588292b [3].

- **Persistent data structures.** let-go implements persistent vectors, maps,
  sets, and queues ([`pkg/vm/persistent_vector.go`](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/vm/persistent_vector.go),
  `persistent_map.go`, `persistent_set.go`, `persistent_queue.go`) [3]. The xsofy
  README says the project uses persistent data structures "all the way down" [1].
  This page does not check how xsofy's game state is modeled.
- **No dependencies.** The xsofy README states that the game has no dependencies
  [1]. The xsofy source tree was not checked against this claim.
- **Startup.** The xsofy README gives "6ms startup" [1]. The let-go README reports
  "~10ms cold start" and 11.1ms startup for let-go in its benchmark table
  (Apple M1 Pro) [3]. Its goals list includes booting the runtime "inside a single
  `requestAnimationFrame` (10ms left over at 60fps)" [3]. xsofy's
  `tools/startup_perf.lg` defines `measure-generate-level` and
  `measure-generate-floor`, which time level and floor generation with
  `System/currentTimeMillis` [4]. No xsofy boot-time measurement was found in the
  sources read.
- **Same source, two targets.** The same `main.lg` runs natively with `lg main.lg`
  [1] and compiles to a web page with `lg -w` [3]. By default `-w` writes an
  `index.html` with the WASM inlined as gzip+base64; `-w-wasm external` writes a
  separate `main.wasm` that the loader streams [3] (`pkg/cli/cli.go`,
  `pkg/rt/wasm/embed.go`). See
  [WASM compilation](../concepts/wasm-compilation.md).
- **xsofy's web build.** The `wasm` Makefile target runs
  `lg -w $(DIST) -w-shell none main.lg`. `-w-shell none` emits the core glue
  without let-go's xterm.js shell (`pkg/cli/cli.go`, `pkg/rt/wasm/shell.go`) [3].
  The target then injects xsofy's own shell
  (`tools/inject_shell.lg`) and patches the cross-origin-isolation lifecycle
  (`tools/patch_wasm_coi.lg`). The Makefile gives the reason: GitHub Pages cannot
  send COOP/COEP headers [4]. The target uses the default inline WASM output [4].
- **Deployed build.** `deploy-pages.yml` and `pr-preview.yml` call the composite
  action `.github/actions/build-wasm` [4] instead of the Makefile target. The
  action runs `let-go -w <dist> -w-shell none -w-wasm external main.lg`, injects
  the same shell, patches the COI startup guard, and writes `build-info.json`
  [4]. With `-w-wasm external`, the output is a separate `main.wasm` that the
  loader streams [4].

## Toolchain pin

`.let-go-version` pins let-go v1.13.0 [4]. That tag is an ancestor of let-go
commit b82588292b, 90 commits later [3]. `.let-go-version` says the `#app`
mount that the xsofy shell binds to (#378) shipped in v1.12.2, and that v1.13.0
carries it [4]. The Makefile names
`-w-shell none` (#245) and the `js/url-param` host seam (#339) as requirements of
the pinned release, and its guard refers to a stale PATH `lg` built before
let-go#378 [4].

## WASM build toolchain

- The `wasm_exec.js` glue is read from the GOROOT that `resolveGoRoot` in
  `pkg/cli/wasm.go` returns [3]. If the `GOROOT` environment variable is set,
  `resolveGoRoot` returns it as given and does not run a Go tool. If it is unset,
  `resolveGoRoot` runs `go env GOROOT` with `gomod.GoToolPath()`
  (`pkg/gomod/gomod.go`) [3]. The WASM build also runs `gomod.GoToolPath()` [3].
  So when `GOROOT` is unset, the glue and the build use the same Go tool. When
  `GOROOT` is set, the glue comes from that path whichever tool runs the build.
  This is the behavior of let-go#837 (commit 1b77130c9b, merged 2026-09-10) [5].
- A cached or relocated `lg` binary keeps a build-time GOROOT. If that toolchain's
  `bin/go` is missing, `GoToolPath` in `pkg/gomod/gomod.go` falls back to `go` on
  PATH [3].
- xsofy's deploy and PR-preview workflows set up Go 1.26 and restore a cached
  `lg` binary [4]. nooga/xsofy#193 (merged 2026-09-10) keys that cache on the exact
  active Go version [6]. The cache-key details belong to xsofy's workflow, not to
  let-go.

# Idioms

- **Same-source browser and terminal via WASM.** xsofy is the case where one
  `main.lg` is the input to both the web build and the terminal build [1][4]. The
  web build uses xsofy's own terminal shell rather than let-go's default.
- **Data-as-code as a game mechanic.** Spells are s-expressions and runes are
  symbols: the game exposes the language's own homoiconicity to the player,
  using let-go values (symbols, lists) directly as the spell substrate rather
  than inventing a separate scripting layer [1].

# Citations

[1] [xsofy repository](https://github.com/nooga/xsofy)
[2] [Play xsofy in the browser](https://nooga.github.io/xsofy/)
[3] [let-go repository at b82588292b](https://github.com/nooga/let-go/tree/b82588292b58ac70908895cc6d9b05e68401e261)
[4] [xsofy repository at 0c38395422](https://github.com/nooga/xsofy/tree/0c38395422): `Makefile`, `.let-go-version`, `tools/`, `.github/workflows/`, `.github/actions/build-wasm/`
[5] [nooga/let-go#837: fix(wasm): resolve wasm_exec from active Go toolchain](https://github.com/nooga/let-go/pull/837)
[6] [nooga/xsofy#193: ci: key lg cache on exact Go version](https://github.com/nooga/xsofy/pull/193)
