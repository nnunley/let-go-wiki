---
type: Project
category: project
title: "legmacs"
description: "An Emacs-flavored terminal editor written in and scripted with let-go (~4,000 lines) — same language for implementation and config, no separate plugin API."
tags: [tooling, lisp]
resource: "https://github.com/nooga/legmacs"
sources: ["repo: nooga/legmacs README, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# legmacs

legmacs is a terminal text editor written entirely in [let-go](../entities/let-go.md), delivering Emacs-style editing in approximately 4,000 lines of Lisp code. The defining feature is that users configure and extend the editor using the same language that implements it—no separate scripting API or plugin system exists.

# Using let-go

legmacs demonstrates [let-go](../entities/let-go.md)'s suitability as both an implementation language and a user-facing scripting layer:

- **Single-language stack** — implementation and configuration are indistinguishable; users modify behavior via `defcommand` and `bind-key!` functions identical to those the editor itself uses.
- **In-process evaluation** — the editor includes a live REPL (`C-x C-e`, `C-j`) enabling real-time experimentation and configuration testing without restarting.
- **Structural manipulation** — implements s-expression-aware editing (expand-region, kill-sexp) naturally in a Lisp-based editor where syntax and structure are unified.
- **Compact footprint** — 4,000 lines of let-go provide kill ring, regions, multi-buffer support, window splitting, syntax highlighting for 20+ languages, and extensible major/minor modes.

# Idioms

- **Homoiconicity as a feature** — because let-go code and let-go data are the same, configuration becomes a form of live programming; users don't "configure an application" but rather "compose a program."
- **Emacs idioms in let-go** — kill ring, regions, keymaps, and mode hierarchies (shadowing keymaps) translate directly from Emacs, showing how Lisp design patterns port cleanly across implementations.

# Citations

[1] [legmacs repository](https://github.com/nooga/legmacs)
