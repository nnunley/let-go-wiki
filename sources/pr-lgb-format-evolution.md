---
type: Source
category: source
title: ".lgb format evolution (PRs #443, #608, #622, #501, #502, #745, #624)"
description: "mparrett's 2026-07 to 2026-09 changes to the bytecode container: the opcode-set capability and its named reject messages, opt-in DEFLATE bodies as format 3, func-chunk identity, and split debug companions."
tags: [bytecode, vm, runtime]
resource: "https://github.com/nooga/let-go/pull/624"
sources: ["pr: https://github.com/nooga/let-go/pull/624, 2026-09-05"]
created: "2026-09-05"
updated: "2026-09-05"
status: active
---

# .lgb format evolution (PRs #443, #608, #622, #501, #502, #745, #624)

Seven PRs by Matt Parrett (mparrett), merged 2026-07-11 to 2026-09-04.

## Key takeaways

- **#443:** `CapOpcodeSet`: the bundle carries the producer's opcode count and an FNV-64a signature; a mismatch fails at decode with a message naming the cause instead of `unknown instruction op=37` deep in execution.
- **#608 and #622:** actionable capability-reject messages, a capability registry with `since` versions, and `lg -v` printing format, capabilities, and the opcode signature.
- **#501 and #502:** `-z` writes a version-3 bundle whose body is one raw DEFLATE stream behind a plaintext header; declared size capped at 256 MiB; the embedded core can be compressed at `lgbgen` time, off by default.
- **#745:** function constants bind to chunks by the builder's live pointer index, not by scanning for identical bytecode, so identical functions keep their own source maps.
- **#624:** `-strip` moves source maps and local-variable tables into a SHA-256-bound `.debug` companion loaded from beside the artifact or `LG_DEBUG_FILE`; fib sample 1,565 to 1,421 bytes plus a 201-byte companion.

## Derived pages

[lgb-bytecode-format](../concepts/lgb-bytecode-format.md) · [debug-info](../concepts/debug-info.md)

# Citations

[1] https://github.com/nooga/let-go/pull/624
