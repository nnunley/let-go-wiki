---
type: Reference
category: reference
title: "lgx Commands"
description: "Common lgx subcommands for managing, running, building, and testing let-go projects."
tags: [tooling, clojure, lisp]
resource: "https://github.com/abogoyavlensky/lgx/blob/master/README.md"
sources: ["repo: abogoyavlensky/lgx README.md, 2026-07-05"]
created: "2026-07-05"
updated: "2026-07-05"
status: stable
---

# lgx Commands

lgx is a git-based package and project manager for [let-go](../entities/let-go.md), bundling dependency resolution, execution, REPL access, binary building, test running, scaffolding, and task automation into a single CLI. This reference documents the primary commands and their usage patterns.

## Quickstart

Create a project from the default template, then run it:

```sh
lgx new hello
cd hello
lgx run
```

`lgx new` scaffolds from the built-in base template (see [`new` templates](#new-templates) below); `lgx run` resolves `:main` from `lgx.edn`, fetches dependencies into `$LGX_HOME/gitlibs/`, and runs the entry point through `lg`.

## Commands Overview

### `lgx new`

Scaffold a new let-go project into `./<name>` from a built-in template or a git URL.

**Usage:**
```sh
lgx new <name> [-t <tpl>]
```

**Key flags:**
- `-t`, `--template <tpl>` — select a template: a built-in name (`base`, `cli`) or a git HTTPS URL. Defaults to `base`.

**Example:**
```sh
lgx new myapp              # scaffold with base template
lgx new myapp -t cli       # use the cli template
lgx new myapp -t https://github.com/user/my-template
```

Templates substitute the token `projectname` with your chosen name (underscored in paths, hyphenated in file contents). URLs must use HTTPS; SSH forms are not supported.

#### `new` Templates

Built-in templates are pinned to a latest revision and cached under `$LGX_HOME/templates/`:

| Name | Repo | Purpose |
| --- | --- | --- |
| `base` | [lgx-template-base](https://github.com/abogoyavlensky/lgx-template-base) | Minimal let-go app. |
| `cli` | [lgx-template-cli](https://github.com/abogoyavlensky/lgx-template-cli) | Command-line app skeleton. |

Custom templates live in HTTPS git repos and must place `projectname` as a literal token wherever the project name belongs.

### `lgx run`

Run the project's `:main` entrypoint (from `lgx.edn`) through `lg`, with project sources and dependencies on the path.

**Usage:**
```sh
lgx run [args...]
```

**Key behaviors:**
- With no `:main` defined and no explicit script, errors. Use [`lgx repl`](#lgx-repl) for an interactive session.
- Sets `LGX_RUN=1` in the spawned process, so code can detect dev vs. bundled-binary mode.
- Inherits lgx's stdio, so live output and interactive programs work.
- Program arguments go after `--` and arrive in `*command-line-args*` (requires `lg` >= 1.11.0).

**Examples:**
```sh
lgx run                    # run :main with no args
lgx run -- foo bar         # run :main with args ("foo" "bar")
lgx run other.lg           # run an explicit script instead of :main
lgx run other.lg -- bar    # explicit script with an arg
lgx run -e '(...)'         # eval a let-go expression
```

**Argument forms:**
- `lgx run` → `lg <paths> <main>` (`*command-line-args*` is `nil`)
- `lgx run -- foo bar` → `lg <paths> <main> foo bar` → `*command-line-args*` is `("foo" "bar")`
- `lgx run other.lg` → `lg <paths> other.lg` (no `:main` needed)
- `lgx run other.lg -- bar` → `lg <paths> other.lg bar` → `*command-line-args*` is `("bar")`
- `lgx run -e '(...)'` → `lg <paths> -e '(...)'` (no `:main`)
- `lgx run -- a -- b` → `*command-line-args*` is `("a" "--" "b")` (first `--` is the separator)

### `lgx repl`

Start `lg`'s built-in REPL with the project's dependencies and source paths loaded, auto-applying the `:dev` and `:test` contexts when defined.

**Usage:**
```sh
lgx repl
```

**Key behaviors:**
- Zero-footprint REPL entry point; no port binding or `.nrepl-port` file.
- Auto-applies `:dev` and `:test` contexts if defined in `lgx.edn`.
- For a scratch script or `lg` flags with dependencies on the path, use `lgx run <script>` instead.

**Example:**
```sh
lgx repl
# (+ 1 2)
# 3
```

### `lgx nrepl`

Start an nREPL server on a free OS-assigned port (or a specified port), with project dependencies and source paths loaded, auto-applying the `:dev` and `:test` contexts when defined.

**Usage:**
```sh
lgx nrepl [--port N]
```

**Key behaviors:**
- Writes the bound port to `.nrepl-port` for editor tooling (e.g., Calva for Clojure) to discover.
- Auto-applies `:dev` and `:test` contexts.
- Ideal when an editor or IDE needs to connect to a REPL server.

**Example:**
```sh
lgx nrepl --port 7888
# Wrote port 7888 to .nrepl-port
# nREPL server listening on 127.0.0.1:7888
```

### `lgx build`

Bundle `:main` into a standalone binary, written to the path specified in `lgx.edn`'s `:targets/:bin/:out`.

**Usage:**
```sh
lgx build [args...]
```

**Key behaviors:**
- Shortcut for `lg <paths> [extra-args...] -b <:out> <:main>`.
- Both `:main` and `:targets/:bin` are required; errors otherwise.
- Extra arguments go before `-b`, enabling cross-OS bundling (e.g., `-bundle-base /path/to/lg`).
- Resource paths are embedded into the binary, so `(io/resource "…")` works without external files.

**Example:**
```sh
lgx build
# => Building…
# bin/myapp

lgx build -bundle-base /path/to/lg  # cross-compile
```

See [lgx build model](../concepts/lgx-build-model.md) for details on what happens during build.

### `lgx test`

Run all `*_test.lg`, `*_test.cljc`, or `*_test.clj` files under `test/`, generating a one-shot test harness and printing summary results.

**Usage:**
```sh
lgx test [file]
```

**Key behaviors:**
- Walks `test/` recursively for test files.
- With `<file>`, runs only that test file.
- Auto-applies the `:test` context if defined.
- Executes every `deftest` against the project's resolved source paths.

**Example:**
```sh
lgx test
# Running tests…
# Ran 5 tests: 5 passed, 0 failed

lgx test test/core_test.lg   # run one file
```

## Global Options

Both `--with` and `--verbose` are placed before the subcommand.

### `--with`

Apply one or more named contexts to the command. Contexts are overlays of extra paths, dependencies, and resource roots defined in `lgx.edn`.

**Usage:**
```sh
lgx --with <a,b,...> <command>
```

**Works with:** `run`, `repl`, `nrepl`, `build`, `test`, `install`, and user tasks.

**Example:**
```sh
lgx --with dev,test run     # apply dev and test contexts to run
lgx --with dev build        # add dev dependencies during build
```

By convention, `:dev` auto-applies to `lgx run`, `:test` to `lgx test`, and `lgx nrepl` applies both automatically—no `--with` needed. See [lgx-edn](lgx-edn.md) for context definition.

### `--verbose`

Print the resolved `lg` invocation before running. Shows:

1. A `+ lg <version> (<path>)` line naming the `lg` binary version and full path (reflects `LGX_LG` overrides).
2. A `+ env …` line listing environment variables lgx sets.

**Works with:** `run`, `repl`, `nrepl`, `build`, `test`, and user tasks.

**Example:**
```sh
lgx --verbose run
# + lg 1.11.0 (/usr/local/bin/lg)
# + env LGX_RUN=1
# (program output follows)
```

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `LGX_LG` | `lg` on `PATH` | Path to the `lg` binary. Useful for testing unreleased builds. |
| `LGX_RUN` | _(set by lgx)_ | Set to `1` by `lgx run`. Read it to detect dev mode vs. bundled binary. |
| `LGX_HOME` | `~/.lgx` | State root: gitlibs cache, let-go source cache, template cache, test harness. |
| `LGX_SKIP_VERSION_CHECK` | _(unset)_ | Set to any non-empty value to bypass `:lg-version` compatibility checks. |
| `LGX_FETCH_LET_GO_SOURCE` | _(unset)_ | Set to `1` to make `lgx install` fetch the let-go source matching `:lg-version`. Feeds editor LSP diagnostics. |
| `LGX_NO_COLOR` | _(unset)_ | Set to any non-empty value to disable colored status headers. |
| `LGX_TEMPLATE_BASE_URL` | template repo URL | Override the source repo of the built-in `base` template. |
| `LGX_TEMPLATE_BASE_SHA` | pinned sha | Override the revision of the built-in `base` template. |

## Other Commands

- `lgx install` — Fetch dependencies from `:deps` into the gitlibs cache. Idempotent; useful for editor navigation.
- `lgx <task> [args...]` — Run a custom task defined under `:tasks` in `lgx.edn`, binding declared positional args.
- `lgx help` or `lgx` — Show usage and project tasks.
- `lgx version` — Print lgx version.
- `lgx completion <shell>` — Print shell completions for bash, zsh, or fish.

## Related Pages

- [lgx Configuration (`lgx.edn`)](lgx-edn.md) — Define projects, dependencies, contexts, and tasks.
- [lgx Build Model](../concepts/lgx-build-model.md) — How `lgx build` bundles binaries.
- [lg Compilation](../concepts/lg-compile.md) — Let-go compiler internals.
- [let-go Project](../entities/let-go.md) — The let-go language and runtime.

# Citations

**Resource:** [lgx README.md](https://github.com/abogoyavlensky/lgx/blob/master/README.md) on GitHub, branch `master`.

All commands, flags, and behaviors sourced from the "Quickstart" and "Commands" sections of the README, including subsections "lgx new templates", "lgx run details", "lgx repl details", "lgx build details", and "lgx test details".
