---
type: Source
category: source
title: Known Clojure divergences
description: let-go's ledger of behavioral differences from Clojure JVM, intentional and temporary, with the shared-suite overrides each one owns.
tags: [clojure, runtime, lisp]
resource: "https://github.com/nooga/let-go/blob/main/docs/KNOWN_DIVERGENCES.md"
sources: ["repo: nooga/let-go docs/KNOWN_DIVERGENCES.md @ 638b4a6a (added by #771, 7aa1ab1a, 2026-09-06; in-doc last-verified 2026-08-23), 2026-09-07", "nooga/let-go#764 (merged 2026-09-07), nooga/let-go#812 (closed 2026-09-06)", "lg -e transcripts on let-go a6763e77, 2026-09-08"]
created: "2026-09-07"
updated: "2026-09-08"
status: active
---

## What this source is

`docs/KNOWN_DIVERGENCES.md` is the ledger of known behavioral differences between let-go and Clojure JVM. Each entry is classified as an intentional language decision or a temporary compatibility mismatch: intentional entries say why let-go does not follow Clojure and how portable code should behave; temporary entries state the intended contract and what resolves them. It is separate from the engine-differential ledgers (`test/parity-divergence.txt` for bytecode-versus-gogen output, `test/gogen_aot_xfail.txt` for gogen fixture divergences), which compare let-go with itself. Added to let-go by #771 on 2026-09-06.

## Key takeaways

**Intrinsic map traversal order** (intentional). Traversal order for map literals and `hash-map` is unspecified at every size, on purpose: a generic map should not acquire an ordering contract because its current representation happens to be small, and the insertion-order side table was removed while optimizing the AOT/IR pipeline in #397. Order comes from an explicitly ordered type: `sorted-map` today, `array-map` once the mismatch below is resolved. The order-independent `:lg` expectations in the shared suite (`cons`, `cycle`, `mapcat` tests) entered through jank-lang/clojure-test-suite#927.

**"Temporary `array-map` mismatch"** (temporary, as written). The ledger records that `array-map` was routed through the unordered persistent map, and states the intended contract: a directly constructed `array-map` stays array-backed and insertion ordered regardless of size, and a ninth distinct entry promotes a smaller array map to the intrinsic unordered map. It notes that #763's acceptance criteria did not match that contract.

**Character model for supplementary Unicode** (intentional). A let-go character is one Unicode scalar value (Go's rune model), so `(char 65895)` yields U+10167 where JVM Clojure throws, and supplementary characters are single characters rather than surrogate pairs. Valid ranges are U+0000 to U+D7FF and U+E000 to U+10FFFF. Two validation defects are recorded as temporary: surrogate-range `Int`/`BigInt` inputs pass `char`'s range check, and a `BigInt` is truncated with `Int64()` before validation, so `(int (char 18446744073709551681N))` gives `65`. No issue tracks them; the ledger is the record. The shared-suite override is jank-lang/clojure-test-suite#939.

**Possible compatibility controls.** A sketch, not a design: runtime features could turn on strict randomized traversal for unspecified-order collections as a diagnostic, and build features could opt into heavyweight compatibility such as a JVM bridge, keeping the default binary lean.

**Maintenance rule.** Every `:lg` override in the pinned shared suite must map to an entry here; the ledger is updated in the same let-go change that consumes the override, and resolved temporary entries are removed. Audit with `git -C test/clojure-test-suite grep -n ':lg' -- '*.cljc'`.

## Since the ledger was written

The ledger's in-doc `last-verified` is 2026-08-23 and it has not been edited since #771 landed. Two things moved:

- **#764 merged on 2026-09-07 (`638b4a6a`), resolving #763.** `PersistentMap` gained an array-map mode behind the same `MapType`: maps with at most eight entries keep insertion order in a paired key/value slice, the ninth `assoc` promotes to the HAMT, and `dissoc` never demotes a non-empty map. Map literals, `array-map`, `assoc` chains, `zipmap`, `merge`, `select-keys`, and `into` preserve insertion order up to eight entries; `hash-map` order stays unspecified by contract and is incidentally insertion-ordered when small. `test/map_order_test.lg` pins this. It narrows the "Temporary `array-map` mismatch" entry rather than closing it: `(array-map ...)` with more than eight pairs is built through the same transient and promotes during construction, so `(keys (array-map :i 1 :h 2 :g 3 :f 4 :e 5 :d 6 :c 7 :b 8 :a 9))` comes back in hash order on `a6763e77` where Clojure keeps a directly constructed array map ordered at any size. The ledger still describes the pre-#764 state; nooga/let-go#826 rewrites the entry to that residual. The intentional entry above it stands: the contract is still "unspecified", and the small-map order is an implementation detail that #764 happens to make match Clojure's.
- **#812 closed as not planned on 2026-09-06.** Norman's report that `(count "😀")` is 1 in let-go and 2 in JVM Clojure was confirmed by the project owner as the accepted rune-counting divergence. That is the character-model entry applied to `count`, and a concrete example the ledger's entry lacks.

## Pages derived from this source

- [Clojure Compatibility](../references/clojure-compat.md), "Behavioral differences"

## Citations

[1] **docs/KNOWN_DIVERGENCES.md** — the ledger  
https://github.com/nooga/let-go/blob/main/docs/KNOWN_DIVERGENCES.md

[2] **PR #771** — docs: catalog known Clojure divergences (merged 2026-09-06)  
https://github.com/nooga/let-go/pull/771

[3] **PR #764** — feat(vm): insertion-ordered small maps matching Clojure array-map semantics (merged 2026-09-07)  
https://github.com/nooga/let-go/pull/764

[4] **Issue #812** — supplementary Unicode string count differs from JVM (closed, not planned, 2026-09-06)  
https://github.com/nooga/let-go/issues/812

[5] **test/map_order_test.lg** — the small-map ordering contract as tests  
https://github.com/nooga/let-go/blob/main/test/map_order_test.lg
