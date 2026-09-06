---
type: Concept
category: concept
title: "Reader"
description: "How let-go turns text into forms: the dispatch tables, reader conditionals with the :lg/:clj/:bb feature switches, the VOID sentinel for no-value forms, number literals, tagged literals, and the places its behaviour diverges from Clojure's reader."
tags: [compiler, clojure, lisp]
resource: "https://github.com/nooga/let-go/blob/main/pkg/compiler/reader.go"
sources:
  - "repo: nooga/let-go pkg/compiler/reader.go, pkg/compiler/eval.go (read-string, read-all-string, load-string, set-read-clj!, set-read-bb!), docs/guide/clojure-compatibility.md @ 0911118, 2026-09-05"
  - "pr: nooga/let-go#736 (set literals as data, open), #770 (custom data readers, open), #768 (raw #go fragments, open), 2026-09-05"
  - "issue: nooga/let-go#801 (map metadata and a discard in value position, filed 2026-09-06), 2026-09-06"
  - "lg -e transcripts on lg 1.12.3-0.20260904132133 (0911118), 2026-09-05"
created: "2026-09-05"
updated: "2026-09-06"
status: stable
---

# Reader

The reader is the first stage of every [compile path](compile-paths.md): `LispReader` in `pkg/compiler/reader.go` turns a character stream into `vm.Value` forms, and everything downstream (macros, the direct compiler, the IR pipeline) sees only those forms. It is a hand-written recursive reader in Go with two dispatch tables, one for the macro characters and one for what follows `#`. It also records where each collection and function literal came from, keyed by form identity in `vm.FormSource`, which is how [debug info](debug-info.md) gets file and line for a chunk.

## Dispatch

`Read` skips whitespace (a comma counts as whitespace, as in Clojure), then: a digit starts a number; a macro character dispatches through the table; `+` or `-` followed by a digit is a number; anything else is a token, interpreted as a symbol, keyword, `nil`, `true`, or `false`.

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
| `#{...}` | set literal (see divergences) |
| `#"..."` | regex |
| `#?(...)` and `#?@(...)` | reader conditional, plain and splicing |
| `##Inf` `##-Inf` `##NaN` | symbolic float values |
| `#tag form` | tagged literal: `#uuid` and `#inst` are built in; any other tag returns its form unchanged |

`IsTokenBoundary` is exported so the REPL completer scans a line with the reader's own rule for where a symbol ends, rather than an approximation that could drift.

### No-value forms and VOID

A line comment, a `#_` discard, and a reader conditional with no matching branch all read as the `VOID` sentinel rather than as nothing. This is load-bearing: the collection readers call `Read` in element position and rely on seeing `VOID` to drop an orphaned map key or splice nothing, so `{:a #_ 1 :b 2}` reads as `{:b 2}`. The skip covers an orphaned entry, not a form inside one: a discard between a key and its value, `{:a #_[:x] 1}`, fails with `map literal must contain even number of forms` at 0911118, and `reader.go` is unchanged through ee55803. Norman filed that gap, with metadata on map literals, as #801 (2026-09-06). `ReadSkipNoValue` is the single-form entry point `read-string` uses; it loops past leading no-value forms and never returns `VOID`.

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

An unmatched branch is skipped, not read, by `skipReaderForm`, which counts balanced delimiters and knows the prefix forms (`^meta x`, `'x`, `#tag x`) consume the form after them. It has to, because a skipped `:clj` branch may hold syntax let-go cannot parse, and each of those prefix cases was once a bug where the trailing form desynchronised the surrounding conditional and swallowed the rest of the file. A comment between a branch key and its value is tolerated for the same reason.

## Numbers

`readNumber` handles, in this order: a `N` suffix for `BigInt` and `M` for `BigDecimal`, hex (`0x1F`, promoted to `BigInt` past `Long/MAX_VALUE` as on the JVM), octal with a leading zero (`0377` is 255), radix literals `2r101` through base 36, ratios (`1/2` reads as a `Ratio`, simplified when it reduces to an integer), then plain integers with promotion to `BigInt` on overflow, and floats.

```
$ lg -e '[0x1F 2r101 36rZZ 1N 1.5M (type 1/2) 0377 ##Inf]'
[31 5 1295 1N 1.5M let-go.lang.Ratio 255 +Inf]
```

## Where it diverges from Clojure

These hold at `0911118` (2026-09-05); three are the subject of open PRs.

- **Set literals read as a call.** `'#{1 2 3}` reads as `(hash-set 3 2 1)`, so `(set? (read-string "#{1}"))` is false. Evaluation is unaffected. #736 (open) makes `#{}` read as a set, as maps and vectors already do.
- **Metadata reads as a form.** `'^:foo bar` reads as `(with-meta bar {:foo true})` rather than the symbol `bar` carrying metadata, so `(meta (eval ''^:foo bar))` is `nil`. Consumers that need the name, such as `defn` and the wiki's own enumeration tooling, unwrap that form. #801 (2026-09-06) reports the same behaviour on map literals, where `(meta (read-string "^{:doc 1} {:a 1}"))` is `nil`, as a bug for configuration data read with `read-string`.
- **Unknown tags pass through.** `#foo/bar 1` reads as `1`; there is no `*data-readers*` or `*default-data-reader-fn*`. #770 (open) adds a Clojure-compatible `*data-readers*` and a per-compiler registry for embedders, and #768 (open; depends on #770 and carries its commits, though its PR base is `main`) adds a raw `#go{...}` reader that preserves Go source verbatim.
- **Namespaced map syntax is not supported.** `#:a{:b 1}` fails with `invalid hash macro`.
- **Duplicate map keys do not throw.** `'{:a 1 :a 2}` reads as `{:a 2}`; Clojure rejects the literal.
- **A leading zero that is not valid octal falls through to decimal.** `08` reads as `8`; Clojure rejects it.

## Entry points

`read-string` reads one form (skipping no-value forms), `read-all-string` reads every form, and `load-string` reads and evaluates; all three are defined in `pkg/compiler/eval.go` beside `set-read-clj!` and `set-read-bb!`. Embedders get the same reader through the compiler API, and `lg -e`, scripts, and the REPL feed it the same way.

## Citations

**Resource:** [pkg/compiler/reader.go](https://github.com/nooga/let-go/blob/main/pkg/compiler/reader.go): the reader, both dispatch tables, `readConditional`, `skipReaderForm`, `readNumber`, `readTaggedLiteral`  
**Related:**
- [pkg/compiler/eval.go](https://github.com/nooga/let-go/blob/main/pkg/compiler/eval.go): `read-string`, `read-all-string`, `load-string`, `set-read-clj!`, `set-read-bb!`
- [docs/guide/clojure-compatibility.md](https://github.com/nooga/let-go/blob/main/docs/guide/clojure-compatibility.md): the tagged-literal and numeric-tower notes
- PRs (open at 2026-09-05): [#736](https://github.com/nooga/let-go/pull/736) set literals, [#770](https://github.com/nooga/let-go/pull/770) custom data readers, [#768](https://github.com/nooga/let-go/pull/768) raw Go fragments

See also: [Bytecode Compiler](bytecode-compiler.md), [Clojure Compatibility](../references/clojure-compat.md), [let-go](../entities/let-go.md)
