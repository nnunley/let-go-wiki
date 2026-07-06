---
type: Reference
category: reference
title: "lgx.edn Configuration"
description: "Top-level keys and schema for lgx.edn project configuration files."
tags: [tooling, clojure, lisp]
resource: "https://github.com/abogoyavlensky/lgx/blob/master/README.md"
sources:
  - "repo: abogoyavlensky/lgx README.md, Configuration: lgx.edn section (lines 191–385), 2026-07-05"
created: "2026-07-05"
updated: "2026-07-05"
status: stable
---

# lgx.edn Configuration

**lgx.edn** is the [Let-Go](../entities/let-go.md) project configuration file, placed at the project root. All keys are optional; a minimal valid file is `{}`. This reference covers all top-level keys, their types, and behavior.

See [lgx commands](lgx-commands.md) for how to invoke `lgx` with these configurations, and [lgx build model](../concepts/lgx-build-model.md) for how they interact.

## Structure Overview

Each top-level key controls a different aspect of the project:

```edn
{:paths               ["src"]              ; source dirs
 :resource-paths     ["resources"]        ; embedded resource roots
 :main               "main.lg"            ; default entry point
 :lg-version         "1.11.0"             ; version constraint
 :deps               {...}                ; dependencies
 :targets            {:bin {:out "..."}}  ; build outputs
 :tasks              {...}                ; custom commands
 :contexts           {...}}               ; named overlays
```

## Top-Level Keys

### `:paths`, `:main`, `:resource-paths`

**`:paths`** — vector of source directory names (relative to project root). Prepended to dependency paths, so project namespaces shadow libraries with the same name. Prepended, not appended.

```edn
:paths ["src" "src/main"]
```

Missing entries print a warning. Default is effectively `[]`.

**`:main`** — string name of the default entry point (relative to project root). Used by `lgx run` when no script is given, and bundled by `lgx build`. Does not need to be under `:paths`.

```edn
:main "main.lg"
```

**`:resource-paths`** — vector of resource directory names. Passed to `lg` as `-resource-paths` for run/test, and **embedded into the binary** by `lgx build`, so `(io/resource "…")` works in bundled apps without the original files. Only comes from your project, never from dependencies.

```edn
:resource-paths ["resources" "assets"]
```

Missing entries print a warning.

### `:lg-version`

String pinning the [Let-Go](../entities/let-go.md) runtime version this project targets. When set:

- On `lgx run` / `lgx nrepl` — warns if the `lg` on PATH differs.
- On `lgx build` / `lgx test` — fails if versions mismatch (wrong runtime or test verdict matters).
- A dev or unparseable installed version is skipped.
- `LGX_SKIP_VERSION_CHECK` env var bypasses the check entirely.
- With `LGX_FETCH_LET_GO_SOURCE=1`, `lgx install` also fetches matching let-go **source** (not binary) into `$LGX_HOME/let-go/source/<version>/` for editor diagnostics.

```edn
:lg-version "1.11.0"
```

### `:deps`

Map of dependency coordinates. Each key is a qualified name (symbol), and the value specifies a source.

**Git source** — fetch from a Git URL via HTTPS, pinned by tag or commit SHA:

```edn
:deps {
  some-user/lib-a {:git/url "https://github.com/some-user/lib-a"
                   :git/tag "v0.2.0"}
  some-user/lib-b {:git/url "https://github.com/some-user/lib-b"
                   :git/sha "0123456789abcdef0123456789abcdef01234567"}
  org.example/lib-c {:git/url "https://github.com/org-example/lib-c"
                     :git/tag "v1.0"
                     :deps/root "src/main/clojure"}}
```

- `:git/url` (required) — HTTPS-only repository URL.
- `:git/tag` or `:git/sha` (one required) — immutable pin.
- `:deps/root` (optional) — source subdirectory inside the repo. Defaults to `src` if present, else repo root. Matches `tools.deps` behavior.

**Local source** — reference a local directory (no gitlibs cache):

```edn
:deps {
  my/lib {:local/root "../my-lib"}
}
```

Never mix `:git/*` and `:local/root` on the same coord.

**Transitive resolution** — lgx reads each dep's own `lgx.edn` and resolves its `:deps` recursively. Only `:deps` are inherited; a dep's `:paths`, `:main`, `:tasks` are ignored. Resolution is breadth-first, and **first-wins**: the first coord seen for a lib name wins, and a later differing coord is skipped with a warning. Your direct deps override transitively-pulled deps.

### `:targets`

Map of build output specifications. Currently only `:bin` is supported:

```edn
:targets {:bin {:out "bin/myapp"}}
```

- `:bin {:out "path/to/binary"}` — path relative to project root. Parent directories are created if missing. Invoked by `lgx build`.

### `:tasks`

Map of custom commands. Run with `lgx <name> [args...]`. A task defines one step (a bare map) or many steps (a vector); each step is `:sh` (shell) or `:run` (let-go script).

**Simple task (single step):**

```edn
:tasks {
  fmt {:doc "Lint the project"
       :do  {:sh "cljfmt fix"}}
}
```

**Multi-step task (stops at first failure):**

```edn
:tasks {
  ci {:doc "Lint, then test"
      :do  [{:sh  "cljfmt check"}
            {:run "scripts/check.lg"}]}
}
```

**Task with positional arguments:**

```edn
:tasks {
  deploy {:doc "Deploy the app"
          :args [{:name :env
                  :type [:enum "prod" "staging"]}
                 {:name    :version
                  :type    :string
                  :default "latest"}]
          :do   [{:sh  ["./deploy.sh" :arg/env :arg/version]}
                 {:run ["notify.lg" :arg/env]}
                 {:sh  "echo deploying v{{version}}"}]}
}
```

**Arguments** (`:args`):

- `:name` — required, an unqualified keyword. Placeholder is `:arg/<name>`.
- `:type` — `:string` (default), `:int`, or `[:enum "v1" "v2" ...]`.
- `:default` — optional; if present, all later args must also have defaults.
- Arity is strict: missing required arg, wrong type, or surplus args prints usage and exits 1.

Reference args two ways:
- **`:arg/<name>` keywords** in vector-form steps (quoted in `:sh` for shell safety, verbatim in `:run`).
- **`{{name}}` templates** in any step string (raw splice; quote if spaces).

**Step formats:**

- `:sh` — shell command, string or vector. Vector form is more precise.
  ```edn
  {:sh "cljfmt fix"}
  {:sh ["sh" "-c" "echo $HOME"]}
  ```
- `:run` — let-go script with this project's basis. String splits on whitespace; vector is explicit argv.
  ```edn
  {:run "scripts/check.lg"}
  {:run ["scripts/check.lg" "--verbose"]}
  ```

**Task-level overlays** — `:extra-paths`, `:extra-resource-paths`, `:extra-deps` (same grammar as project-level). Applied to `:run` steps only; `:sh` steps are plain shell. Appended after project-level and de-duplicated.

```edn
:tasks {
  console {:doc "Custom REPL with dev tooling"
           :with [:dev]
           :extra-paths ["repl"]
           :extra-deps {some-extra {:git/url "..." :git/tag "v1"}}
           :do [{:run "dev/repl.lg"}]}
}
```

**Constraints:** Task names are symbols and cannot shadow built-ins (`install`, `run`, `nrepl`, `build`, `test`, `new`, `help`, `version`, plus reserved `add`, `update`, `tasks`). Only keys `:doc`, `:args`, `:do`, `:with`, `:extra-paths`, `:extra-resource-paths`, `:extra-deps` are allowed; typos (e.g. `:extra-dep`) fail loudly.

### `:contexts`

Named, reusable overlays of `:extra-paths`, `:extra-resource-paths`, and `:extra-deps`. Applied globally via `lgx --with <names>` or per-task via `:with`. Deduplication and layering rules apply.

```edn
:contexts {
  :dev  {:extra-paths ["dev"]
         :extra-resource-paths ["dev-resources"]
         :extra-deps {nrepl {:git/url "https://github.com/x/nrepl"
                             :git/tag "v1"}}}
  :test {:extra-paths ["test-support"]}
}
```

**Default contexts (auto-applied):**

- `:dev` auto-applies to `lgx run` and `lgx nrepl`.
- `:test` auto-applies to `lgx test` and `lgx nrepl`.
- `lgx build` and `lgx install` never auto-apply contexts (keep dev/test deps out of binaries).
- Task `:run` steps don't inherit contexts unless the task explicitly `:with` them.

**Layering precedence** (lowest to highest; most specific wins):

1. Project `:deps`, `:paths`, `:resource-paths`
2. Auto-applied contexts (`:dev`, `:test`)
3. Task `:with` contexts (in order)
4. CLI `--with` contexts (in order)
5. Task inline `:extra-deps`, `:extra-paths`, `:extra-resource-paths`

Source and resource paths concatenate project-first (project shadows libraries) and de-duplicate. Resource paths never pick up dependency directories.

## Minimal Example

```edn
{}
```

A completely empty file is valid; all keys default to sensible values.

## Real-World Example

```edn
{:paths ["src"]
 :resource-paths ["resources"]
 :main "main.lg"
 :lg-version "1.11.0"
 :targets {:bin {:out "bin/myapp"}}

 :deps
 {askonomm/ruuter {:git/url "https://git.nmm.ee/asko/ruuter"
                   :git/tag "v2.1.1"}}

 :contexts
 {:dev  {:extra-paths ["dev"]}
  :test {:extra-paths ["test"]}}

 :tasks
 {fmt   {:doc "Format code"
         :do  {:sh "cljfmt fix"}}
  test  {:doc "Run tests"
         :do  {:run "test/runner.lg"}}}}
```

## Related

- [Let-Go](../entities/let-go.md) — the runtime and language.
- [lgx Commands](lgx-commands.md) — command-line interface (`lgx run`, `lgx build`, etc.).
- [lgx Build Model](../concepts/lgx-build-model.md) — how configuration drives builds.
- [Let-Go Projects](../projects/lgx.md) — example projects using lgx.

# Citations

**Resource:** [lgx README.md — Configuration: lgx.edn](https://github.com/abogoyavlensky/lgx/blob/master/README.md)

Lines 191–385 cover all top-level keys (`:paths`, `:main`, `:resource-paths`, `:lg-version`, `:deps`, `:tasks`, `:targets`, `:contexts`), their shapes, and behavior.

Examples in `/examples/hello/lgx.edn`, `/examples/server/lgx.edn`, and the root `lgx.edn` illustrate minimal and real-world configurations.
