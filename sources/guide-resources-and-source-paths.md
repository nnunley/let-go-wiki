---
type: Source
category: source
title: Resources and Source Paths
description: Guide to let-go resource loading and namespace resolution via `-resource-paths` and `-source-paths` flags.
tags:
  - runtime
  - tooling
  - reference
resource: https://github.com/nooga/let-go/blob/main/docs/guide/resources-and-source-paths.md
sources:
  - "repo: nooga/let-go docs/guide/resources-and-source-paths.md, 2026-07-03"
created: 2026-07-03
updated: 2026-07-03
status: stable
---

## Overview

This guide documents two path-list mechanisms in [let-go](../entities/let-go.md) that control file loading: resource roots (for non-source data) and source roots (for `require`d namespaces). Both accept `:` (Unix) or `;` (Windows) separated paths, and support embedding into bundled binaries.

## Key takeaways

- **`io/resource`** reads templates, assets, and data files from configured resource roots; returns `nil` if absent
- **Resource roots** are set via `-resource-paths` flag or `LG_RESOURCE_PATHS` env var; multiple roots use first-match semantics
- **Binary bundling** (`-b`) embeds all resource-root files into the binary; a bundled binary reads only embedded resources (no filesystem fallback)
- **Source paths** resolve `require`d namespaces; default is `.` (current directory) unless overridden
- **Source path configuration** via `-source-paths` or `LG_SOURCE_PATHS`; explicit paths are complete (`.` not implicit unless listed); empty value means "no source paths"
- **Search path independence**: the script passed on the command line always loads by its literal path

This mechanism enables self-contained, predictable deployments and controls the namespace search hierarchy.

## Derived pages

[let-go](let-go-readme.md) · [runtime-image](design-runtime-image.md)

## Citations

—
