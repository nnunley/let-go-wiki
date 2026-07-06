---
type: Project
category: project
title: "lgx"
description: "A git-based dependency manager, runner, build tool, test runner, scaffolder, and task runner for let-go in one binary (config in lgx.edn)."
tags: [tooling, lisp]
resource: "https://github.com/abogoyavlensky/lgx"
sources: ["repo: abogoyavlensky/lgx README.md, 2026-07-05"]
created: "2026-07-02"
updated: "2026-07-05"
status: active
---

# lgx

lgx is the unified project manager and build system for [let-go](../entities/let-go.md), combining dependency management, task execution, testing, scaffolding, and REPL integration into a single binary. Projects configure their structure in EDN format via `lgx.edn` at the project root; lgx handles everything from fetching git-based dependencies to compiling and bundling standalone executables.

## What lgx is

**Dogfooding note:** lgx is itself written in let-go ([lgx.lg](https://github.com/abogoyavlensky/lgx/blob/master/lgx.lg)), showcasing let-go's readiness for systems tooling.

lgx consolidates roles that would otherwise require separate tools:

- **Build tool** — compiles [let-go](../entities/let-go.md) source via `lg -b` and bundles the result into standalone binaries (see [lgx-build-model](../concepts/lgx-build-model.md)).
- **Dependency manager** — fetches git-based dependencies (pinned by tag or SHA), caches them under `$LGX_HOME/gitlibs/`, and resolves transitive deps breadth-first with first-wins conflict resolution.
- **Test runner** — walks `test/` for `*_test.lg` / `*_test.cljc` / `*_test.clj` files, generates a one-shot test harness, and runs all `deftest` declarations against the project's resolved source paths.
- **Task runner** — executes custom shell and let-go tasks from `lgx.edn`, with typed positional arguments, step chaining, and variable binding.
- **Scaffolder** — `lgx new` creates projects from built-in templates (`base`, `cli`) or custom git URLs, using the `projectname` token to substitute project names.
- **REPL integrator** — `lgx repl` starts `lg`'s built-in REPL; `lgx nrepl` starts an nREPL server for editor tooling (both auto-apply `:dev` and `:test` contexts).

## Key capabilities

**Configuration:** [lgx.edn](../references/lgx-edn.md) lives at the project root and defines `:paths`, `:main`, `:deps`, `:targets`, `:contexts`, and `:tasks`. See [references/lgx-edn](../references/lgx-edn.md) for the full annotated reference.

**Common workflows:**
- `lgx new myapp` — scaffold a project from a template.
- `lgx install` — fetch all `:deps` into the gitlibs cache (idempotent, useful for editor navigation).
- `lgx run [args...]` — resolve `:main`, fetch deps, and run it via `lg` with inherited stdio (for interactive programs).
- `lgx test [file]` — run all tests, or a single file if specified.
- `lgx build [args...]` — bundle `:main` into a binary at `:targets/:bin/:out`.
- `lgx repl` / `lgx nrepl [--port N]` — start a REPL with the project's deps on the source path.
- `lgx <task> [args...]` — run a custom task from `lgx.edn` with optional typed arguments.

See [references/lgx-commands](../references/lgx-commands.md) for the complete command reference and options.

**Contexts and overlays:** Named `:contexts` (e.g., `:dev`, `:test`) apply environment-specific `:extra-paths`, `:extra-deps`, and `:extra-resource-paths`. Apply them with `lgx --with dev,test <cmd>` or a task's `:with`; `:dev` auto-applies to `run`, `:test` to `test`, and both to `nrepl`. This keeps dev/test dependencies out of release binaries.

**Transitive dependencies:** After fetching a dep, lgx reads its `lgx.edn` and recursively resolves `:deps` (breadth-first, first-wins). A coord you list directly overrides the same lib pulled in transitively.

**Task system:** Tasks replace ad-hoc Makefiles. Define them under `:tasks` with `:doc`, `:do` (steps), `:args` (typed positional params), `:with` (contexts), and task-private `:extra-*` overlays. Steps are `:sh` (shell) or `:run` (let-go with project basis); the first non-zero exit stops the chain.

## Design philosophy

- **Single binary, multiple roles** — consolidates build, test, dependency, and task management without spawning external tools for each concern, reducing cognitive load and toolchain complexity.
- **Git-native dependencies** — uses git repositories directly (with optional `:deps/root` subdirectory) rather than a centralized registry, avoiding lock-in and enabling dependency on unreleased work or internal repos.
- **Language-native config** — `lgx.edn` uses let-go data literals (EDN), keeping configuration close to the language itself.
- **Zero package-manager bloat** — projects depend directly on what they need; no transitive explosion of unused packages, no registry uptime risks.

## Build model and architecture

For details on how lgx compiles and bundles let-go programs, see [concepts/lgx-build-model](../concepts/lgx-build-model.md). For bytecode compilation and runtime details, see [concepts/lg-compile](../concepts/lg-compile.md), [concepts/bytecode-compiler](../concepts/bytecode-compiler.md), and [concepts/runtime-image](../concepts/runtime-image.md).

# Citations

[1] [lgx repository](https://github.com/abogoyavlensky/lgx) — README.md, 2026-07-05.
