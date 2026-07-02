---
type: Project
category: project
title: "Xs of Y (xsofy)"
description: "A browser-and-terminal roguelike written in let-go where the magic system is a Lisp."
tags: [roguelike, wasm, lisp]
resource: "https://github.com/nooga/xsofy"
sources: ["repo: nooga/xsofy README.md, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
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

xsofy is a substantial real program — a complete game — which makes it a strong
"using let-go in anger" case study. It leans on let-go's core properties:

- **Persistent data structures all the way down** — the game state model is
  built on immutable, structurally-shared collections.
- **No dependencies** — the whole game is written against let-go and its standard
  library, with no external packages.
- **~6ms startup** — fast enough to boot inside a single frame.
- **Same source, two targets** — compiled to self-contained **WASM** for the
  browser and run **natively** in the terminal from the identical codebase.

# Idioms

- **Same-source browser + terminal via WASM.** Because let-go compiles to a
  self-contained WASM page *and* runs natively, a single program ships to both a
  web page and a terminal without a separate port — a repeatable pattern for
  let-go apps.
- **Data-as-code as a game mechanic.** Spells are s-expressions and runes are
  symbols: the game exposes the language's own homoiconicity to the player,
  using let-go values (symbols, lists) directly as the spell substrate rather
  than inventing a separate scripting layer.

# Citations

[1] [xsofy repository](https://github.com/nooga/xsofy)
[2] [Play xsofy in the browser](https://nooga.github.io/xsofy/)
