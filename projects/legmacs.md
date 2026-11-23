---
type: Project
category: project
title: "legmacs"
description: "An Emacs-flavored terminal editor written in and scripted with let-go (about 10,000 lines of let-go) — same language for implementation and config, no separate plugin API."
tags: [tooling, lisp]
resource: "https://github.com/nooga/legmacs"
sources: ["repo: nooga/legmacs README, 2026-07-02", "repo: nooga/legmacs main.lg legmacs/ examples/legmacs_init.example.lg build.sh build/main.go .let-go-version @ 187fea2, 2026-10-20", "repo: nooga/let-go README.md docs/lowering-census.md docs/typeinfer-census.md docs/guide/clojure-compatibility.md scripts/lg-compile test/e2e/lg_compile_emit_fail_contract_test.go pkg/rt/core/ir/lower_go.lg pkg/api/api.go @ b82588292b, 2026-10-20"]
created: "2026-07-02"
updated: "2026-10-20"
status: stable
---

# legmacs

legmacs is a terminal text editor written entirely in [let-go](../entities/let-go.md), delivering Emacs-style editing. The defining feature is that users configure and extend the editor using the same language that implements it—no separate scripting API or plugin system exists.

The README (2026-07-02) gives the size as approximately 4,000 lines. The README was later revised: to about 4,500 lines (2026-07-07, `a33b85e`), about 5,000 (2026-08-20, `953aeac`), and about 5,300 (2026-08-20, `eecf820`). At `187fea2` the README reads "About 5,300 lines of Lisp for the whole editor, bundled modes included" (README line 15). At legmacs `187fea2`, the implementation is 10,451 lines of `.lg`: 10,272 under `legmacs/` (including `modes/` and `extensions/`) and 179 in `main.lg`. The test suite (`test/`) is a further 5,884 lines.

Line references below are to legmacs at `187fea2` unless marked as let-go.

# Using let-go

legmacs demonstrates [let-go](../entities/let-go.md)'s use as both an implementation language and a user-facing scripting layer:

- **Single-language stack** — implementation and configuration are both let-go. Commands are defined with `defcommand`, a macro in `legmacs/keymap.lg:30`, and bound with `bind-key!`, a function in `legmacs/keymap.lg:68`. `legmacs/commands.lg` defines 66 commands with `defcommand`. The example user init file, `examples/legmacs_init.example.lg`, uses the same two forms. `main.lg`'s header says `bin/legmacs` puts `~/.config/legmacs/` on the namespace search path so that `legmacs-init.lg` is picked up.
- **In-process evaluation** — the let-go mode keymap in `legmacs/modes/letgo.lg` binds `C-x C-e` to `eval-last-sexp`, `C-j` to `eval-print-last-sexp`, and `C-c C-e` to `eval-buffer` (lines 786–792). The header comment of that file says evaluation runs in the editor's own process and namespace. These bindings apply in let-go-mode buffers, not globally.
- **Structural editing** — `expand-region` is a `defcommand` in `legmacs/modes/letgo.lg:766`, bound to `C-c e`; its companion command undoes the last expansion step. `legmacs/lisp_syntax.lg` supplies the bracket and string scanning that expansion uses. The 187fea2 source defines no `kill-sexp`.
- **Footprint** — `legmacs/buffers.lg` keeps the kill ring as global state shared across buffers (comment at line 6), and `legmacs/buffer.lg` defines `yank` and `kill-word`. `legmacs/windows.lg` defines `split-leaf`. `legmacs/modes/prog.lg` has 23 `register-prog-mode!` registrations, each registering a mode with syntax highlighting for a language or language family (for example, `javascript-mode` covers JavaScript/TypeScript at line 387 and `html-mode` covers HTML, XML and SVG at line 613), in addition to the let-go and other modes under `legmacs/modes/`.

# Idioms

- **Code as data** — let-go is a Clojure dialect ([let-go README](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/README.md)) whose `clojure.core` includes macros ([clojure compatibility](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/guide/clojure-compatibility.md)). legmacs configuration is let-go code evaluated in the running editor, so users change behavior by writing forms rather than by configuring an application.
- **Emacs idioms in let-go** — kill ring, regions, keymaps, and mode hierarchies (shadowing keymaps) are Emacs concepts implemented in let-go. `legmacs/keymap.lg:119` describes a mode adding `C-x C-e` without taking `C-x C-s` from the global map.

# How legmacs is built

- `.let-go-version` pins the let-go source ref that legmacs builds against: `a6657612002b`. The file calls it the single source of truth for both CI workflows and `build.sh`.
- `build.sh` builds `lg` from a let-go checkout, runs let-go's `scripts/lg-compile` over `legmacs/*.lg`, compiles `main.lg` into the bytecode bundle `build/legmacs.lgb` with `lg -c`, and runs `go build` on `build/main.go`. `main.lg` is left interpreted; its `(main)` call is guarded so the AOT compile does not start the editor.
- `build/main.go` embeds `legmacs.lgb` and boots it through let-go's `api.NewLetGo`, which creates the compiler and resolver ([pkg/api/api.go at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/api/api.go)). The standalone binary therefore includes the compiler, so `eval` should be available to let-go-mode buffers. This is source-level only: no run was done, and the bundle and runtime path were not read.

# Let-go side

let-go's census docs record lowering and type-inference runs against legmacs. The figures below are as recorded in let-go's docs at the commits named there, not at b82588292b.

- **Lowering to Go** — [docs/lowering-census.md](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/lowering-census.md) records a run on 2026-10-05 against legmacs `187fea2` with let-go `dbaf59cb`: 29 namespaces, 672 units lowered, 0 fallbacks (100.0%). The run took about 45 seconds.
- **Type inference** — [docs/typeinfer-census.md](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/typeinfer-census.md) records a run on 2026-10-09 against legmacs `187fea2` with let-go `a47a81b`: 672 functions, 45,581 instructions, 6,585 typed (14.4%), 36,485 `:unknown`, 2,511 `:any`, no `:bottom`. The run was from the legmacs checkout root with `--follow . main.lg`.
- **Build exit status** — The `lg.compiler` driver (`write-packages!`) prints `EMIT-FAIL` lines for functions that do not lower. [scripts/lg-compile](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/scripts/lg-compile) runs that driver and passes its exit status through; it exits non-zero only when `lg.compiler/exit-code` returns a positive code. Its comment states that legmacs' `set -e` build keeps going through an `EMIT-FAIL`. [test/e2e/lg_compile_emit_fail_contract_test.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/test/e2e/lg_compile_emit_fail_contract_test.go) pins this; its comment states that only an entry-arity error exits non-zero.
- **Reserved Go identifiers** — [pkg/rt/core/ir/lower_go.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/lower_go.lg) lists `ec` and `callErr` among the fixed Go identifiers the lowering emits into every generated function. Its comment gives a legmacs `end-column` local destructured as `ec` as the case the list guards against.

# Citations

[1] [legmacs repository](https://github.com/nooga/legmacs)

[2] [legmacs at 187fea2](https://github.com/nooga/legmacs/tree/187fea2b6e8e6e65a05edafbf93f179726eef4c7)

[3] [let-go lowering census, at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/lowering-census.md)

[4] [let-go type inference census, at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/typeinfer-census.md)

[5] [let-go scripts/lg-compile, at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/scripts/lg-compile)

[6] [let-go lg-compile EMIT-FAIL contract test, at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/test/e2e/lg_compile_emit_fail_contract_test.go)

[7] [let-go pkg/rt/core/ir/lower_go.lg, at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/lower_go.lg)

[8] [let-go pkg/api/api.go, at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/api/api.go)

[9] [let-go README, at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/README.md)

[10] [let-go clojure compatibility guide, at b82588292b](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/guide/clojure-compatibility.md)
