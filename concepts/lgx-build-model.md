---
type: Concept
category: concept
title: "lgx Build & Dependency Model"
description: "How lgx resolves git-pinned dependencies via a gitlibs cache, invokes let-go compilation, bundles executables, and runs tests."
tags: [tooling, compiler, lisp]
resource: "https://github.com/abogoyavlensky/lgx/blob/master/docs/ARCHITECTURE.md"
sources:
  - "repo: abogoyavlensky/lgx README.md, 2026-07-05"
  - "repo: abogoyavlensky/lgx docs/ARCHITECTURE.md, 2026-07-05"
created: "2026-07-05"
updated: "2026-07-05"
status: stable
---

# lgx Build & Dependency Model

[lgx](../projects/lgx.md) is a package and project manager for [let-go](../entities/let-go.md) that orchestrates three key responsibilities: **dependency resolution** via git-based coords and local paths, **compilation and execution** by invoking the `lg` runtime with resolved source paths, and **artifact bundling** through let-go's `-b` (build) flag. This page covers how lgx resolves dependencies, drives compilation, manages state, and runs programs—everything needed to understand the workflow from `lgx install` through `lgx build`.

## Dependency Resolution

### Git-based and Local Coordinates

lgx dependencies are declared in `lgx.edn` under `:deps` as a map of lib names to **coordinates**. Each coord is either:

- **Git source**: `:git/url "https://github.com/owner/repo"` plus one of `:git/sha` (specific commit) or `:git/tag` (semantic version tag). HTTPS only; SSH forms are not supported.
- **Local path**: `:local/root "../my-lib"` (relative to project root for direct deps, or relative to the declaring dependency for transitive ones). Local coords bypass the gitlibs cache entirely.

Both forms support `:deps/root <relative-path>` to name a source subdirectory inside the dependency (defaults to `src` if present, else the repo root). This matches the Clojure `tools.deps` convention and handles libraries that ship sources under non-standard locations like `org.clojure/tools.cli` with `:deps/root "src/main/clojure"`.

### Gitlibs Cache and Atomic Cloning

When lgx encounters a git coord, it computes a cache reference:
- For `:git/sha` coords, the ref is the commit SHA itself
- For `:git/tag` coords, the ref is the tag name with `/` replaced by `_`

lgx checks `$LGX_HOME/gitlibs/<host>/<owner>/<repo>/<ref>/` for an existing cache entry. If present, it reuses the cached directory (idempotent—calling `lgx install` twice on the same deps does not re-clone). If missing, it clones atomically: clone into a temp directory, check out the SHA or tag, drop the `.git/` directory, and rename atomically to the final cache path. This atomic approach ensures no partial states are visible to concurrent operations.

Local deps are never cached; they resolve directly from disk.

### Transitive Dependency Resolution

After fetching a dep, lgx reads its own `lgx.edn` (if present) and resolves only the `:deps` entries recursively—never `:paths`, `:main`, `:tasks`, or other top-level keys. Resolution is **breadth-first and first-wins**: the first coord seen for a library name is kept, and a later different coord is skipped with a warning. Direct deps override transitive ones of the same name. This strategy is identical to Clojure's `tools.gitlibs` and prevents diamond-dependency conflicts.

Cycles are detected and terminated by the seen-libs set, so a circular dependency chain does not cause infinite recursion.

## Compilation and Execution

### Invoking the lg Runtime

lgx never compiles or executes user code itself. Instead, it shells out to the `lg` binary—either on `PATH` or pointed to by the `LGX_LG` environment variable—and invokes it with resolved source and resource paths. Two separate `lg` runtimes coexist:

1. **Embedded runtime**: The lgx binary itself is a let-go bytecode bundle (`lg -b lgx.lg bin/lgx`), embedding a pinned `lg` VM. This runs lgx's own project-management logic.
2. **User runtime**: A separate `lg` binary (user-supplied or from PATH) executes the user's script with the resolved dependency paths.

This separation decouples lgx's release cycle from let-go's: upgrading let-go does not force rebuilding lgx, and vice versa.

### Source and Resource Path Resolution

For commands that run or test (`lgx run`, `lgx test`, `lgx repl`, `lgx nrepl`), lgx:

1. Resolves `:paths` from `lgx.edn` (project source directories, relative to project root) to absolute paths. Missing entries print a warning but are still passed to `lg`.
2. Appends the gitlibs cache paths from all resolved dependencies, maintaining project-first precedence (project namespaces shadow library namespaces).
3. Joins the paths with the OS separator and passes them to `lg` as the `-source-paths` argument.

Similarly, `:resource-paths` (asset roots for `io/resource "…"`) are resolved and passed as `-resource-paths`. Resource paths are project-only—dependencies never contribute resource directories—but are embedded into the binary by `lgx build` so bundled apps resolve resources with no files alongside the executable.

### The `lgx run` Workflow

`lgx run` resolves the project basis (deps + paths), then decides the `lg` invocation by parsing its arguments structurally:

- If args contain `--` before any positional, the user is driving `lg` (e.g., `lgx run other.lg` or `lgx run -e '(...)'`); `:main` is not injected.
- If no `--` and `:main` is set, lgx injects `:main` and any postional args become `*command-line-args*` in the script.
- If no `--`, no `:main`, and args remain, lgx errors (`lgx run: -- forwards args to :main, but no :main is set …`).
- If bare `lgx run` with no `:main`, lgx errors and suggests `lgx repl`.

lgx execs `lg -source-paths <paths> -resource-paths <roots> [args...]` via inherited stdio (using let-go ≥ 1.10.0's `os/exec*`), so live output and interactive programs (REPL, prompts) work. The spawned process sees `LGX_RUN=1`, allowing code to detect dev mode.

### Build and Bundling

`lgx build` performs a similar basis resolution, then:

1. Reads `:main` and `:targets/:bin` from `lgx.edn`. Both are required; missing either causes a clear error.
2. Verifies the `:main` script exists on disk.
3. Creates the parent directory of `:targets/:bin/:out` (recursive, idempotent).
4. Execs `lg -source-paths <paths> -resource-paths <roots> [forwarded-args...] -b <abs-out> <abs-main>`.

The `-b` flag instructs `lg` to bundle the script into a standalone executable: the let-go VM and compiled bytecode are embedded in one binary, along with all resources under `:resource-paths`. The result is a portable executable that requires no separate `lg` binary or source files.

Extra arguments before `-b` (e.g., `-bundle-base /path/to/lg` for cross-OS builds) are forwarded verbatim to `lg`, allowing fine-grained control over bundling.

### Testing with Generated Harness

`lgx test` walks `test/` recursively for `*_test.lg`, `*_test.cljc`, and `*_test.clj` files, generates a one-shot test harness, and runs every `deftest` against the project's resolved source paths.

The harness is written to `$LGX_HOME/test-runner/lgx-test-<version>.lg` and:

1. `:require`s every discovered test namespace plus core test utilities.
2. Defines a test plan (file → namespace mapping).
3. Iterates each namespace's entries in `*registered-tests*` (let-go's built-in registry).
4. Runs each `deftest` under `with-out-str` (suppresses assertion chatter) while tracking results.
5. Prints a summary: `N tests, M assertions, K failures`.
6. Exits 0 if all pass, 1 if any fail.

If a test file fails to load (compile/syntax/runtime error), `lg` prints a diagnostic to stderr but does not throw. lgx detects this by scanning stderr for `error: failed to load <path>: …` before the harness-ready marker, and forces a failure exit if found (otherwise the harness would report 0 failures).

## State Layout

lgx organizes all persistent state under `$LGX_HOME` (default `~/.lgx`):

```
$LGX_HOME/
  gitlibs/<host>/<owner>/<repo>/<ref>/
    src/                      (when :deps/root "src" or default probing finds it)
    ...                       (or other :deps/root directory)
  templates/<host>/<owner>/<repo>/<sha>/
    ...                       (cached template checkout, reused by `lgx new`)
  test-runner/
    lgx-test-<version>.lg     (generated test harness, rewritten on each `lgx test`)
  let-go/source/<version>/    (optional; populated by LGX_FETCH_LET_GO_SOURCE)
```

- **`gitlibs/` cache**: Read-only worktree per coord. Each leaf is the checked-out dependency at the specified ref (sha or tag). The `src/` probe applies the default source-root logic.
- **`templates/` cache**: Sha-pinned template checkouts, reused after first clone by `lgx new`. Parallels gitlibs structure but uses only sha keying.
- **`test-runner/` harness**: Single generated harness file per lgx version, overwritten on each test run.
- **`let-go/source/` source cache** (optional): Populated when `LGX_FETCH_LET_GO_SOURCE=1` is set during `lgx install`, enabling editor LSP navigation into let-go's standard library.

All paths are portable (no shell-specific characters) and idempotent. Missing `.git/` in cached repos prevents accidental git operations on the cached checkouts.

## Contexts: Layered Path and Dependency Overlays

The `:contexts` map in `lgx.edn` defines named overlays of `:extra-paths`, `:extra-resource-paths`, and `:extra-deps`. These allow projects to layer dev/test dependencies without polluting production artifacts.

**Auto-context convention**:
- `:dev` context (if defined) auto-applies to `lgx run` only.
- `:test` context (if defined) auto-applies to `lgx test` only.
- Both `:dev` and `:test` auto-apply to `lgx repl` and `lgx nrepl`.
- `lgx build` and `lgx install` never auto-apply contexts; use `lgx --with dev build` to explicitly apply contexts to build.

Contexts can also be applied manually via `lgx --with dev,test <command>` or via a task's `:with` vector. The layering order (lowest to highest precedence) is:

1. Project `:deps` / `:paths` / `:resource-paths`
2. Auto context (if applicable)
3. Task `:with` contexts (in order)
4. CLI `--with` contexts (in order)
5. Task `:extra-deps` / `:extra-paths` / `:extra-resource-paths` (highest)

Deps follow last-wins precedence (a higher layer's coord replaces a lower one's). Paths concatenate in order (project first, so project namespaces shadow library ones) and deduplicate keep-first. Resource paths layer identically but never pick up dependency directories.

## External Dependencies

lgx depends on:

- **`git` on `PATH`**: Used for clone, fetch, and checkout operations. lgx never bundles git.
- **`lg` binary**: On `PATH` or `LGX_LG`. `lgx run` fails loudly if `lg` is missing; `lgx install` does not require it. lgx sets `LG_READ_CLJ=1` before every `lg` invocation to enable `.clj` library file resolution and Clojure reader conditionals.
- **Default template repo**: `lgx new` pulls from `https://github.com/abogoyavlensky/lgx-template-base` (sha-pinned), overridable via `LGX_TEMPLATE_BASE_URL` and `LGX_TEMPLATE_BASE_SHA`.

## Component Architecture

The lgx source is organized into stateless helper namespaces:

- **`lgx.main`**: Entry point and subcommand dispatch; wires basis/overlay resolution.
- **`lgx/cli.lg`**: Pure argv parsing (program-prefix strip, leading `--verbose`/`--with`, nrepl `--port`).
- **`lgx/config.lg`**: Schema-as-data validation, `lgx.edn` loading and normalization (runs once per invocation).
- **`lgx/cache.lg`**: Gitlibs cache layout and fetch orchestration via `git`.
- **`lgx/runner.lg`**: Locates `lg`, invokes with `-source-paths` / `-resource-paths`, handles interactive vs. captured stdio.
- **`lgx/tasks.lg`**: Executes project tasks from `:tasks` in `lgx.edn`.
- **`lgx/new.lg`**: Scaffolds new projects from templates (built-in or URL).

These modules are stateless and deterministic: the same `lgx.edn` + CLI args always produce the same invocation, cache layout, and exit code.

---

# Citations

- **Primary resource**: [Architecture — abogoyavlensky/lgx](https://github.com/abogoyavlensky/lgx/blob/master/docs/ARCHITECTURE.md) — Runtime model, Components, Data flow, State layout, External dependencies sections detail lgx's invocation strategy, dependency resolution, and cache layout.
- **README** — [lgx](https://github.com/abogoyavlensky/lgx) — Command reference and `lgx.edn` configuration grammar.
