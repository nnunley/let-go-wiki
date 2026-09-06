---
type: Source
category: source
title: "Regenerating generated artifacts after .lg edits"
description: "The contributor rule that .lg edits do nothing until make generate runs, why staleness is content-hashed rather than mtime-based, where a stale artifact is caught, and the git merge drivers for the binary bundle and the digest."
tags: [tooling, runtime, reference]
resource: "https://github.com/nooga/let-go/blob/main/docs/regenerating-generated-artifacts.md"
sources: ["doc: https://github.com/nooga/let-go/blob/main/docs/regenerating-generated-artifacts.md, 2026-09-05"]
created: "2026-09-05"
updated: "2026-09-05"
status: active
---

# Regenerating generated artifacts after .lg edits

Active doc (last-verified 2026-06-13). Editing any `pkg/rt/core/**/*.lg` file requires regenerating the artifacts the runtime loads instead of source; skip it and the edit silently has no effect.

## Key takeaways

- **Two artifacts from one command:** `core_compiled.lgb` (default runtime) and `core_go_lowered/` (`-tags gogen_ir`); `make generate` refreshes both plus the manifest, `make check-generated` verifies.
- **Why not mtimes:** VCS checkouts write arbitrary mtimes, so a stale bundle can look newer than its sources; `pkg/genmanifest` hashes content into `generated.sums` instead.
- **Where staleness is caught:** `TestGeneratedArtifactsAreFresh`, `make check-generated`, and an optional pre-commit hook (`scripts/pre-commit`, symlinked by hand; `jj` runs no git hooks).
- **Merge drivers:** `make install-hooks` registers `merge.lgb` and `merge.sums` so a rebase touching `core.lg` regenerates rather than conflicting on binary.
- **`go build` cannot regenerate:** only `make generate` or `go generate ./cmd/lgbgen` do.

## Derived pages

[generated-artifacts](../concepts/generated-artifacts.md) · [runtime-image](../concepts/runtime-image.md)

# Citations

[1] https://github.com/nooga/let-go/blob/main/docs/regenerating-generated-artifacts.md
