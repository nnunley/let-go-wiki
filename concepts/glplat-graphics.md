---
type: Concept
category: concept
title: "glplat Graphics Layer"
description: "The experimental graphics platform layer: two backends behind build tags, a default build where every native reports no backend, and the backend contract Norman has not settled yet."
tags: [graphics, runtime, go, tooling]
resource: "https://github.com/nooga/let-go/tree/main/pkg/glplat"
sources:
  - "repo: nooga/let-go pkg/glplat/{glplat,init,ebitenboot,font}.go, pkg/glplat/internal/, pkg/rt/interop_glplat.go @ 36b13f79, 2026-09-20"
  - "doc: nooga/let-go docs/design/glplat-backend-contract.md (status: planning, decision requested) @ 36b13f79, 2026-09-20"
  - "pr: nooga/let-go#744 (glplat merged provisionally), #874 (backend contract + experimental scoping), #789 (untagged builds gated off GL/Ebitengine), #392 (the re-scope this defers to), 2026-09-20"
  - "lg -e transcript on lg 1.13.0 (369e2a69): untagged (glplat/Init 320 240 \"t\") reports `glplat: no backend registered for Init`, 2026-09-20"
created: "2026-09-20"
updated: "2026-09-20"
status: speculative
---

# glplat Graphics Layer

**Treat this as experimental, and treat this page as provisional.** `glplat`
merged in #744 as a deliberately narrow landing, and the design that governs it
is still open — see [What is not settled](#what-is-not-settled).

`glplat` is a platform layer for windowed graphics: create a window, poll input,
submit textured triangles, present a frame. It is the first peer capability to
land alongside the terminal I/O seam that
[I/O host decoupling](io-host-decoupling.md) predicted.

## Two backends, selected by build tag

| Tag | Backend | Reaches |
|---|---|---|
| *(none)* | no backend registered | every native returns an error |
| `glplat` | GLFW / OpenGL | cgo-native only |
| `glplat_ebiten` | Ebitengine | native, browser, Metal |
| `glplat_fonts` | font primitives | opt-in, independent of the two above |

The font tag is separate on purpose: #392's direction required the font
primitives be opt-in regardless of which backend is chosen, and that part is
settled.

## The default build is safe

A plain `go build ./...` links no graphics dependency at all. #789 gated the
untagged build off the GL and Ebitengine subsystems, so `x/image` and `x/text`
no longer land in every binary.

The `glplat` namespace still exists in that build, which surprises people. Its
natives are registered unconditionally from `pkg/rt/interop_glplat.go`, a
generated `lginterop` file with no build tag; only the *backend* is gated. So
the namespace loads and each call reports the missing backend rather than
failing to resolve:

```
(require '[glplat])
(glplat/Init 320 240 "t")
;=> glplat: no backend registered for Init
```

That is the designed behaviour, and it is what makes headless CI and
`go build ./...` work without a graphics toolchain.

## The native surface

Names are Go-cased, not kebab-cased, because they come straight through
`lginterop` from the `pkg/glplat` Go API: `glplat/Init`, `glplat/ShouldClose`,
`glplat/PollEvents`, `glplat/PollInputEvents`, `glplat/BeginFrame`,
`glplat/EndFrame`, `glplat/SubmitTriangles`, `glplat/SetMatrix`,
`glplat/LoadTextureFile`, `glplat/LoadTextureRGBA`, `glplat/TextureSize`,
`glplat/WindowSize`, `glplat/Time`, `glplat/Terminate`, `glplat/Screenshot`.

Anyone writing against these should expect the spelling to change — see below.

## What is not settled

`docs/design/glplat-backend-contract.md` is `status: planning` and carries an
explicit **decision requested** from nnunley. Two numbered proposals are
awaiting a yes, no, or amendment:

- **§2** — bind the backend as a host capability at a dynamic var, on the #572
  `surface` model, and retire the package-level registry.
- **§3** — a backend-independent contract covering frame orientation,
  depth and occlusion, resize, input events and modifiers, and lifecycle.

#744 landed ahead of that answer with the registry under `internal/` and the
namespace marked experimental, and #874 moved the seam and the
behaviour-changing rules to #392's re-scope. So the concrete risk to a caller is
that adopting §2 may rename natives and change `Init`'s signature.

## Open questions for this page

Written from the code and the design doc rather than from use. Not covered here,
and worth filling in by someone who has run it:

- What a minimal working program looks like under each backend.
- Whether the Ebitengine browser path composes with the existing WASM bundle
  model in [WASM compilation](wasm-compilation.md).
- The input-event vocabulary `PollInputEvents` returns.
