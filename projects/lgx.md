---
type: Project
category: project
title: "lgx"
description: "A git-based dependency manager, runner, build tool, test runner, scaffolder, and task runner for let-go in one binary (config in lgx.edn)."
tags: [tooling, lisp]
resource: "https://github.com/abogoyavlensky/lgx"
sources: ["repo: abogoyavlensky/lgx README, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# lgx

lgx is a comprehensive project manager for [let-go](../entities/let-go.md) that unifies dependency management, task execution, testing, scaffolding, and REPL management into a single binary. Projects declare configuration in EDN format via `lgx.edn`, and lgx handles everything from fetching git-based dependencies to building standalone executables.

# Using let-go

lgx is the de facto build and dependency system for [let-go](../entities/let-go.md) projects, showcasing the language's practical ecosystem needs:

- **EDN configuration** — projects express their structure in native let-go data literals (EDN), keeping configuration close to the language itself.
- **Transitive dependency resolution** — implements breadth-first, first-wins dependency resolution with git URLs pinned by tag or SHA, avoiding the package manager bloat present in other ecosystems.
- **Context-driven environments** — supports named overlays (`:dev`, `:test`) that apply environment-specific paths and dependencies automatically, enabling clean separation of development and production concerns.
- **Integrated task system** — custom tasks combine shell commands and let-go invocations with typed positional arguments, REPL support, and reference binding.

# Idioms

- **Single binary, multiple roles** — lgx consolidates build, test, dependency, and task management without spawning external tools for each concern, reducing cognitive load and toolchain complexity.
- **Git-native dependencies** — by using git repositories directly (with optional subdirectory paths) rather than a centralized registry, projects avoid package manager lock-in and can depend on unreleased work or internal repositories.

# Citations

[1] [lgx repository](https://github.com/abogoyavlensky/lgx)
