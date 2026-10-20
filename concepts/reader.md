---
type: Concept
category: concept
title: "Reader"
description: "How let-go turns text into forms: the dispatch tables, reader conditionals with the :lg/:clj/:bb feature switches, the VOID sentinel for no-value forms, number literals, tagged literals, and the places its behaviour diverges from Clojure's reader."
tags: [compiler, clojure, lisp]
resource: "https://github.com/nooga/let-go/blob/main/pkg/compiler/reader.go"
sources:
  - "repo: nooga/let-go pkg/compiler/reader.go, pkg/compiler/compiler.go, pkg/compiler/tagged_reader.go, pkg/compiler/eval.go (read-string, read-all-string, load-string, set-read-clj!, set-read-bb!), pkg/rt/core/core.lg (-read-tagged, *default-data-reader-fn*), pkg/rt/core/edn.lg, pkg/gofragments, pkg/cli/gofragments.go @ b82588292b, 2026-10-19"
  - "repo: nooga/let-go docs/guide/clojure-compatibility.md @ 0911118, 2026-09-05"
  - "pr: nooga/let-go#736 (set literals read as sets, merged as 7fff498b9, 2026-09-30), #768 (raw #go fragments, merged as 747132e0a, 2026-09-30), #770 (custom data readers, merged as e3c3b0a78, 2026-09-11), @ b82588292b, 2026-10-19"
  - "pr: nooga/let-go#819 (metadata on read-string data, 63a619a81, 2026-09-27), #854 (clojure.edn data semantics for #801 and #823, da8cbc440, 2026-09-11), #787 (# _ skips a comment before the form it drops, 681672c86, 2026-09-06), #967 (#! first line, a141e4065, 2026-09-29), #985 (unknown tags throw, *default-data-reader-fn*, c87c8ef87, 2026-10-17; fixes #981), #986 (clojure.edn read-string options, 432c5f2ab, 2026-10-17; fixes #980), @ b82588292b, 2026-10-19"
  - "issue: nooga/let-go#801 (map metadata and a discard in value position, filed 2026-09-06), 2026-09-06"
  - "lg -e transcripts on lg 1.13.0 (369e2a69): *data-readers* default, a bound reader, and an unregistered tag, 2026-09-20; lg -e transcripts on lg 1.12.3-0.20260904132133 (0911118), 2026-09-05. Not re-run at b82588292b"
  - "run: lg dev (b825882) at nooga/let-go b82588292b, 2026-10-20 (#go reader presence in the default build)"
created: "2026-09-05"
updated: "2026-10-19"
status: stable
---

# Reader

The reader is the first stage of every [compile path](compile-paths.md): `LispReader` in `pkg/compiler/reader.go` turns a character stream into `vm.Value` forms, and everything downstream (macros, the direct compiler, the IR pipeline) sees only those forms. It is a hand-written recursive reader in Go with two dispatch tables, one for the macro characters and one for what follows `#`. It also records where each collection and function literal came from, keyed by form identity in `vm.FormSource`, which is how [debug info](debug-info.md) gets file and line for a chunk.

The reader has two modes. Code reading (`NewLispReader`) is what the compiler and `lg -e` use, and it returns forms the compiler consumes. Data reading (`NewLispDataReader`, and the `data` field it sets) returns Clojure data, and is what `read-string`, `read-all-string` and `clojure.edn` use. The two modes differ in several places, described under [code and data reading](#code-and-data-reading) below.

## Dispatch

`Read` skips whitespace (a comma counts as whitespace, as in Clojure), then: a digit starts a number; a macro character dispatches through the table; `+` or `-` followed by a digit is a number; anything else is a token, interpreted as a symbol, keyword, `nil`, `true`, or `false`.

A `#!` first line is skipped before any form is read (`skipShebang`, `pkg/compiler/reader.go`), so a file that starts `#!/usr/bin/env lg` runs as a script. The check happens once per reader, at byte 0 of the input only. Anywhere else `#!` remains an invalid hash macro, and data reading never skips it. Added in [#967](https://github.com/nooga/let-go/pull/967) (merged as `a141e4065`, 2026-09-29).

| Character | Reads |
|---|---|
| `(` `[` `{` | list, vector, map (an unmatched closer is an error naming the delimiter) |
| `"` | string, with `\t \r \n \b \f \\ \"` and `\uXXXX` escapes |
| `\` | character: `\a`, `\newline`, `A` |
| `'` `` ` `` `~` `~@` `@` | `(quote x)`, syntax-quote, unquote, unquote-splicing, `(deref x)` |
| `;` | line comment (a no-value form, see below) |
| `^` | metadata prefix |
| `#` | second table |

| After `#` | Reads |
|---|---|
| `#'x` | `(var x)` |
| `#_form` | discard (a no-value form) |
| `#(...)` | anonymous function: `'#(+ % %2)` reads as `(fn* [%1 %2] (+ %1 %2))` |
| `#{...}` | set literal, read as a set value in both modes (see code and data reading) |
| `#"..."` | regex |
| `#?(...)` and `#?@(...)` | reader conditional, plain and splicing |
| `##Inf` `##-Inf` `##NaN` | symbolic float values |
| `#tag form` | tagged literal: resolved by the tag policy, and an unhandled tag throws (see [tagged literals](#tagged-literals)) |

`IsTokenBoundary` is exported so the REPL completer scans a line with the reader's own rule for where a symbol ends, rather than an approximation that could drift.

### No-value forms and VOID

A line comment, a `#_` discard, and a reader conditional with no matching branch all read as the `VOID` sentinel rather than as nothing. This is load-bearing: the collection readers call `Read` in element position and rely on seeing `VOID` to drop an orphaned map key or splice nothing. What happens to an orphaned key depends on the mode. Code reading drops the key, so `{:a #_ 1 :b 2}` reads as `{:b 2}`. Data reading follows Clojure and splices nothing, so the same input is an odd-count error, and `{:a #_[:x] 1}` reads as `{:a 1}`. Code reading has no such rule for a discard between a key and its value: `{:a #_[:x] 1}` fails there with `map literal must contain even number of forms` (`readMap`, `!r.data` branch; present at `a6763e77`, 2026-09-07, and unchanged at `b82588292b`). The data-mode rule is from `da8cbc440` ([#854](https://github.com/nooga/let-go/pull/854), for [#801](https://github.com/nooga/let-go/issues/801) and #823). Norman filed the map-interior gap, with metadata on map literals, as #801 (2026-09-06).

A `#_` discard also skips a line comment or a nested discard before the form it drops, so `[#_ ;; note\n [:x] [:y]]` reads as `[[:y]]` as in Clojure. This is `readFormComment` in `681672c86` ([#787](https://github.com/nooga/let-go/pull/787), 2026-09-06). `ReadSkipNoValue` is the single-form entry point `read-string` uses; it loops past leading no-value forms and never returns `VOID`.

The transcripts below were run on lg 1.12.3 (`0911118`). They have not been re-run at `b82588292b`.

```
$ lg -e "(read-string \";c\n(1)\")"
(1)
$ lg -e "'#_ignored 42"
42
```

## Reader conditionals

`#?(...)` reads its key/value pairs and takes the first key that matches: `:lg` always, `:default` always, `:clj` only when `LG_READ_CLJ` is set or `(set-read-clj! true)` has been called, and `:bb` under `LG_READ_BB` or `set-read-bb!`. The `:clj` opt-in exists because the `:clj` branch of many libraries reaches JVM-only code; the Clojure compatibility suite reads through the `:clj` lens, ordinary programs do not.

```
$ lg -e '#?(:lg :lg-branch :clj :clj-branch :default :dflt)'
:lg-branch
$ lg -e '(read-string "#?(:clj 1 :default 2)")'
2
$ lg -e '(do (set-read-clj! true) (read-string "#?(:clj 1 :default 2)"))'
1
```

An unmatched branch is skipped, not read, by `skipReaderForm`, which counts balanced delimiters and knows the prefix forms (`^meta x`, `'x`, `#tag x`) consume the form after them. It has to, because a skipped `:clj` branch may hold syntax let-go cannot parse, and each of those prefix cases was once a bug where the trailing form desynchronised the surrounding conditional and swallowed the rest of the file. A comment between a branch key and its value is tolerated for the same reason. `skipReaderForm` now returns an error, so a failing `*data-readers*` resolver on the skip path is reported as it is on the read path (`747132e0a`, [#768](https://github.com/nooga/let-go/pull/768)).

## Numbers

`readNumber` handles, in this order: a `N` suffix for `BigInt` and `M` for `BigDecimal`, hex (`0x1F`, promoted to `BigInt` past `Long/MAX_VALUE` as on the JVM), octal with a leading zero (`0377` is 255), radix literals `2r101` through base 36, ratios (`1/2` reads as a `Ratio`, simplified when it reduces to an integer), then plain integers with promotion to `BigInt` on overflow, and floats.

```
$ lg -e '[0x1F 2r101 36rZZ 1N 1.5M (type 1/2) 0377 ##Inf]'
[31 5 1295 1N 1.5M let-go.lang.Ratio 255 +Inf]
```

The transcript predates `b82588292b`. `readNumber` has since changed its integer width (`vm.MakeInt64` and `strconv.ParseInt(sn, 10, 64)`, `pkg/compiler/reader.go` around lines 705-739), but the behaviour of these literals is unchanged.

## Tagged literals

`readTaggedLiteral` reads the tag, then settles it in this order:

1. **Raw readers.** A raw reader consumes source text rather than a form. An explicit registration on the reader wins, then a raw `*data-readers*` entry. The `#go{...}` reader is raw (below).
2. **The form.** The following form is read with `ReadSkipNoValue`.
3. **The embedder's registry.** A Go `TaggedReaderRegistry` entry receives the form.
4. **`clojure.core/-read-tagged`** (`pkg/rt/core/core.lg`, the policy that `c87c8ef87` moved out of Go). It checks a `*data-readers*` entry; then `default-data-readers`, which holds `#inst` and `#uuid`; then `*default-data-reader-fn*`, called with the tag symbol and the unevaluated form. If none of these handles the tag, reading throws `No reader function for tag <tag>`.

`*data-readers*` is empty by default, and `#inst` and `#uuid` live in their own map, so rebinding `*data-readers*` keeps them. The bootstrap reader that reads `core.lg` itself has no policy yet, so it resolves only `#inst` and `#uuid` (`CoreReadBuiltinTagged`). `*data-readers*` and `*default-data-reader-fn*` are looked up through the calling `ExecContext`, so dynamic bindings apply to `read-string` and `read-all-string`. This is the unknown-tag behaviour added by [#985](https://github.com/nooga/let-go/pull/985) (merged as `c87c8ef87`, 2026-10-17; fixes #981). Before it, an unregistered tag read as its payload. [#770](https://github.com/nooga/let-go/pull/770) (merged as `e3c3b0a78`, 2026-09-11) added the `*data-readers*` lookup and the per-reader registry for embedders.

The `#go{...}` raw reader is no longer built into the reader. `pkg/gofragments` defines it, and its `init` installs it into `*data-readers*` (`pkg/gofragments/gofragments.go`). `pkg/cli/gofragments.go` imports that package unless the binary is built with `-tags lg_no_gofragments`. A program that does not import `pkg/gofragments` has no `#go` reader, so `#go{` is read as an ordinary form first (`readTaggedLiteral` calls `ReadSkipNoValue` before it consults the registry or the policy). The default build was observed with the reader installed: `(read-string "#go{ return 1 }")` returned the string `" return 1 "` (run: lg dev (b825882) at nooga/let-go b82588292b, 2026-10-20). The `-tags lg_no_gofragments` behavior described here is source-derived; that build was not run. Go source usually fails there with a reader error about the payload, such as `#go{ return 1 }` failing with `map literal must contain even number of forms`; the `No reader function for tag go` error appears only when the payload happens to parse as a form. The reader keeps the payload's Go source verbatim, and ignores braces inside Go strings, runes, raw strings and comments ([#768](https://github.com/nooga/let-go/pull/768), merged as `747132e0a`, 2026-09-30). The `reader.go` comment at `NewLispReaderWithTaggedReaders` still says `#go` is built in; that comment is stale.

## Code and data reading

`NewLispDataReader` sets `data`, and `read-string`, `read-all-string` and `ReadString` read with it (`eval.go`, `newDataReaderWithResolvers`; [#819](https://github.com/nooga/let-go/pull/819), `63a619a81`). Data reading differs from code reading in these ways:

- **Metadata attaches to the value.** Under data reading `^{:doc 1} [1 2]` yields a vector carrying the metadata, where code reading emits `(with-meta [1 2] {:doc 1})` (`readMeta`, the `r.data` branch). A value that cannot carry metadata falls back to the wrapper form. `vm.Symbol` is a plain string with no `IMeta`, so `^:foo bar` still reads as the `with-meta` form under either mode.
- **Set literals read as sets.** `readSet` builds a `PersistentSet` in both modes, and the reader never emits a `(hash-set …)` form. The compiler adds the `hash-set` call when it compiles a set value (`pkg/compiler/compiler.go:787`, the `vm.SetType` case of `compileForm`), so evaluation of a set literal is unchanged. Duplicate set elements are a reader error in both modes (`Duplicate key:`). [#736](https://github.com/nooga/let-go/pull/736) (merged as `7fff498b9`, 2026-09-30).
- **Duplicate map keys are an error.** `readMap` throws `duplicate key in map literal` in data mode. Code reading keeps last-wins, so existing sources are unaffected.
- **A discard inside a map splices nothing**, as described under no-value forms.

## Where it diverges from Clojure

These hold at `b82588292b` (2026-10-19).

- **Code reading keeps call forms.** The compiler's reader returns `(with-meta …)` for metadata, so `'^:foo bar` reads as `(with-meta bar {:foo true})` rather than the symbol `bar` carrying metadata, and `(meta (eval ''^:foo bar))` is `nil`. Consumers that need the name, such as `defn` and the wiki's own enumeration tooling, unwrap that form. Data reading returns the Clojure value, so `(set? (read-string "#{1}"))` is true and `(meta (read-string "^{:doc 1} {:a 1}"))` carries `{:doc 1}`. This is the read-string half of [#801](https://github.com/nooga/let-go/issues/801). The map-interior discard half is handled in data mode by `da8cbc440`; the `63a619a81` message says it remains open, which the code does not bear out.
- **Duplicate map keys in code reading do not throw.** `'{:a 1 :a 2}` reads as `{:a 2}`; Clojure rejects the literal. Data reading rejects it, as above.
- **Namespaced map syntax is not supported.** `#:a{:b 1}` fails with `invalid hash macro`.
- **A leading zero that is not valid octal falls through to decimal.** `08` reads as `8`; Clojure rejects it.

## Entry points

`read-string` reads one form as data, skipping no-value forms. `read-all-string` reads every form as data. `load-string` reads and evaluates. All three are defined in `pkg/compiler/eval.go` beside `set-read-clj!` and `set-read-bb!`. `read-string` and `read-all-string` take the caller's `ExecContext` for tag resolution (`execContextDataReaderResolver` in `pkg/compiler/tagged_reader.go`). Embedders get the reader through `NewLispReader` and `NewLispDataReader`, and through `ReadString` and `ReadDataString` for a single form. `lg -e`, scripts, and the REPL feed the same code reader.

`clojure.edn/read-string` (`pkg/rt/core/edn.lg`) takes an options map: `:readers`, a map from tag symbol to function; `:default`, a function of tag and form for any tag not in `:readers` and not `#inst` or `#uuid`; and `:eof`, the value an input with no form reads as. Without `:eof`, an empty input is an error when opts are given, and reads as nil when no opts are given. EDN never consults `*data-readers*` or `*default-data-reader-fn*`, as in Clojure. [#986](https://github.com/nooga/let-go/pull/986) (merged as `432c5f2ab`, 2026-10-17; fixes #980).

## Citations

**Resource:** [pkg/compiler/reader.go](https://github.com/nooga/let-go/blob/main/pkg/compiler/reader.go): the reader, both dispatch tables, `readConditional`, `skipReaderForm`, `skipShebang`, `readNumber`, `readMap`, `readSet`, `readMeta`, `readFormComment`, `readTaggedLiteral`  
**Related:**
- [pkg/compiler/tagged_reader.go](https://github.com/nooga/let-go/blob/main/pkg/compiler/tagged_reader.go): the tag resolver, the raw-reader type, `GoRawDataReader`, `InstallDataReader`
- [pkg/compiler/eval.go](https://github.com/nooga/let-go/blob/main/pkg/compiler/eval.go): `read-string`, `read-all-string`, `load-string`, `set-read-clj!`, `set-read-bb!`
- [pkg/rt/core/core.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg): `-read-tagged`, `*data-readers*`, `*default-data-reader-fn*`
- [pkg/rt/core/edn.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/edn.lg): `clojure.edn/read-string` and its options
- [pkg/gofragments](https://github.com/nooga/let-go/tree/main/pkg/gofragments): the `#go{...}` raw reader, installed by import
- [docs/guide/clojure-compatibility.md](https://github.com/nooga/let-go/blob/main/docs/guide/clojure-compatibility.md): the tagged-literal and numeric-tower notes (checked at `0911118`)
- PRs (merged): [#736](https://github.com/nooga/let-go/pull/736) set literals, [#770](https://github.com/nooga/let-go/pull/770) custom data readers, [#768](https://github.com/nooga/let-go/pull/768) raw Go fragments, [#819](https://github.com/nooga/let-go/pull/819) read-string metadata, [#854](https://github.com/nooga/let-go/pull/854) clojure.edn data semantics, [#967](https://github.com/nooga/let-go/pull/967) shebang, [#985](https://github.com/nooga/let-go/pull/985) unknown tags throw, [#986](https://github.com/nooga/let-go/pull/986) clojure.edn options

See also: [Bytecode Compiler](bytecode-compiler.md), [Clojure Compatibility](../references/clojure-compat.md), [let-go](../entities/let-go.md)
