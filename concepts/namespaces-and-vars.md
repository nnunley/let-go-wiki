---
type: Concept
category: concept
title: "Namespaces and Vars"
description: "How names resolve in let-go: the Namespace's five maps and its lookup order, the Var's lock-free root and its two binding chains, refer and alias semantics including the core short-name aliases, the guarded-root fast path for native primitives, and the shadow warning that never fired."
tags: [runtime, vm, clojure, compiler]
resource: "https://github.com/nooga/let-go/blob/main/pkg/vm/namespace.go"
sources:
  - "repo: nooga/let-go pkg/vm/{namespace,var,binding_stack,root_bindings}.go, pkg/rt/lang.go (nsAliases, LookupOrRegisterNSNoLoad), pkg/rt/core/core.lg (ns macro) @ 0911118, 2026-09-05"
  - "pr: nooga/let-go#548 (alias before core shortcut), #610 (alias guard by name), #734 (core-shadow warning, merged 2026-09-06 as 928c217), #781 (lazy var metadata, merged 2026-09-06 as b0397f6), 2026-09-05"
  - "repo: nooga/let-go pkg/vm/namespace.go @ ee55803 (re-verified for #734/#781), 2026-09-06"
  - "lg -e transcripts on lg 1.12.3-0.20260904132133 (0911118), 2026-09-05"
created: "2026-09-05"
updated: "2026-09-06"
status: stable
---

# Namespaces and Vars

A var is the unit of definition and the boundary every [compile path](compile-paths.md) agrees on: bytecode, IR-compiled, and Go-lowered code all resolve a name to a `*vm.Var` and read its root. A namespace is the table that resolves the name. Both live in `pkg/vm`, and the [execution context](exec-context.md) owns the dynamic bindings that used to live on the var.

## Namespace

`vm.Namespace` is a name plus five maps behind one `RWMutex`: `registry` (the vars this namespace owns), `refers` (vars visible unqualified from other namespaces), `aliases` (`(:require [x :as y])`), `excludes` (names kept out of the `clojure.core` auto-refer), and `unmapped` (names removed with `ns-unmap`, hidden from refers too). The governing invariant is that no code holds one namespace's lock while taking another's, so cross-namespace reads snapshot or use the target's own brief accessors and the lock graph has no cycles.

### Lookup order

`Lookup` takes a symbol and follows Clojure's precedence:

1. **Unqualified**: the namespace's own var, then explicit refers (`:refer [syms]`, `:refer :all`, `use`), then the auto-referred baseline (`clojure.core` and `let-go.core`) only when no explicit refer provides the name. An explicit refer therefore shadows core.
2. **Alias-qualified** (`s/join`): the aliased namespace's own var, then that namespace's refers. An alias may point at a placeholder created before its source finished loading; on a miss the lookup re-resolves the namespace by name through the runtime's loader, caches the real one on the alias, and retries.
3. **Fully qualified**: the global namespace registry, via the `nsLookup` hook `pkg/rt` installs.

Privacy is enforced only on bare qualified references. `LookupIncludingPrivate` backs the `var` special form, so `#'ns/sym` reaches a private var in any namespace, as in Clojure.

```
$ lg -e "(do (require '[clojure.string :as core]) (core/join \",\" [1 2]))"
"1,2"
```

That transcript is #548's regression: the compiler used to short-circuit any symbol whose namespace part was literally `core` to `clojure.core` before consulting aliases, so `core/join` failed to resolve. Aliases now win, and the core shortcut remains only as a fallback for `(ns ...)` expansion before refers exist. #610 fixed the sibling guard: a require-alias collision is detected by comparing namespace names, because two loads of the same namespace can present distinct pointers.

### Short names for the standard namespaces

The canonical name of `clojure.core` is `core`. `pkg/rt` keeps a table (`nsAliases`) mapping `clojure.core`, `clojure.string`, `clojure.test`, `clojure.set`, `clojure.walk`, `clojure.edn`, `clojure.zip`, and `clojure.data` to `core`, `string`, and so on; both names resolve to the same `*Namespace`. `LookupOrRegisterNS` resolves the alias before touching the registry, which matters for the generated [primitive registrar](native-primitives.md): it registers under `"clojure.core"`, and without canonicalisation it would create a second, invisible namespace. The short name is what the runtime prints:

```
$ lg -e "(resolve 'inc)"
#'core/inc
$ lg -e "(find-ns 'clojure.string)"
<ns string>
```

### The `ns` macro

`ns` is a macro in `core.lg`. It strips a metadata wrapper or docstring from the namespace symbol, hoists `(:refer-clojure :exclude [...])` into `exclude-in-current-ns` before any body form so the shadow check sees it, and expands each `:require` entry into `require` (load without referring), then `alias` for `:as`, `refer` for `:refer :all`, `refer-list` for `:refer [syms]`, and a rename step. Loading before referring is deliberate: `use` refers everything, which would leak every public of an `:as`-aliased library into the unqualified namespace.

### The shadow warning

`warnOnCoreShadow` prints Clojure's `WARNING: x already refers to: #'clojure.core/x` when a definition shadows a name referred in from core, with guards for core itself, `:exclude`, unmapped names, and a suppression flag. Both intern paths call it: `Def`, the Go-side path, and `LookupOrAdd`, which the `def` special form uses. Until #734 (merged 2026-09-06, 928c217) only `Def` checked, so the warning had never fired for user code. The transcript below is from 0911118, before the fix:

```
$ lg -e '(do (def inc 5) inc)'
5
```

No warning was printed. #734 factored the check into `warnOnCoreShadow`, calls it from both intern paths, matches Clojure JVM in warning only on shadow-of-refer (a namespace that never referred the name stays silent), and declares the one intentional shadow it uncovered (`edn/read-string`) with `:refer-clojure :exclude`.

## Var

`vm.Var` holds the root binding in an `atomic.Pointer`, so `Deref`, the hottest var operation, is a lock-free load. Around it: the owning namespace and name, metadata and watches behind a mutex, an atomic `isDynamic` flag (read on the hot path while a concurrent `binding` may set it), a private flag, and two things worth explaining.

### Two binding chains

Dynamic bindings no longer live on the var. Each [`ExecContext`](exec-context.md) owns a `bindingStack`: a persistent stack of immutable `(var, value)` frames behind an atomic head. A `binding` pushes a frame; the topmost frame for a var is its current value and the frames beneath are the shadowed outer bindings. Readers walk the chain from an atomically loaded head without locking, and a child context shares its parent's chain by pointer, which is how bindings convey into `future` and `go` blocks (see [concurrency model](concurrency-model.md)). The root context keeps a second, per-var chain (`rootBind`) for bindings established outside any child context, plus a registry of vars with a live root binding so a snapshot can enumerate them without walking anything on the deref path.

```
$ lg -e "(do (def ^:dynamic *x* 1) (defn f [] *x*) [(f) (binding [*x* 2] (f)) (f)])"
[1 2 1]
$ lg -e "(do (defn g [] 1) [(with-redefs [g (fn [] 2)] (g)) (g)])"
[2 1]
$ lg -e "(do (def y 1) (alter-var-root #'y inc) y)"
2
```

### Guarded roots

Lowered Go code may call a native primitive directly instead of dereferencing its var, which is only correct while the var still holds the native. `GuardRoot` records a var's canonical root, `GuardDeviated` says whether the current root differs, and `SetRoot` keeps a process-wide deviation counter (`GuardedRootsIntact`, one atomic load) that any `with-redefs`, `alter-var-root`, or re-`def` of a guarded var moves off zero and restoring the root moves back. The comment above it describes emitted direct-call sites consulting it and falling back to the trampoline; at `0911118` that is aspiration, since the only reader is the runtime's `rt/native-prims-intact?` diagnostic, and when that returns false `LG_GUARD_DEBUG` makes it print which guarded vars deviated. The switch that actually governs direct calls is `*direct-calls-disabled?*` at lowering time. See [native primitives](native-primitives.md) and [compile paths](compile-paths.md).

### Metadata

Vars defined from source carry `:line`, `:file`, and `:column`; embedded core vars report `<embedded:core>` as their file. `:arglists` is not attached to the embedded core's vars at `0911118`:

```
$ lg -e "(meta #'map)"
{:line 374 :file "<embedded:core>" :column 1}
```

#781 (merged 2026-09-06, b0397f6) changed how that metadata is stored in the core bundle. Before it, `InitFromLGB` eagerly built a map for each of the 485 vars that carried metadata at 0911118; now the bundle writes the pairs under the version-1 `TagDefMetaPairs` tag (see [.lgb format](lgb-bytecode-format.md)) and the map is built on first use, which its measurement put at about half the boot allocations.

## Citations

**Resource:** [pkg/vm/namespace.go](https://github.com/nooga/let-go/blob/main/pkg/vm/namespace.go): the five maps, `lookup`, refer and alias precedence, `Def` and the shadow check  
**Related:**
- [pkg/vm/var.go](https://github.com/nooga/let-go/blob/main/pkg/vm/var.go): `Var`, the atomic root, `GuardRoot` and `GuardedRootsIntact`
- [pkg/vm/binding_stack.go](https://github.com/nooga/let-go/blob/main/pkg/vm/binding_stack.go) and [root_bindings.go](https://github.com/nooga/let-go/blob/main/pkg/vm/root_bindings.go): the two binding chains
- [pkg/rt/lang.go](https://github.com/nooga/let-go/blob/main/pkg/rt/lang.go): `nsAliases`, `LookupOrRegisterNSNoLoad`, `NameCoreNS`
- [pkg/rt/core/core.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg): the `ns` macro
- PRs: [#548](https://github.com/nooga/let-go/pull/548), [#610](https://github.com/nooga/let-go/pull/610) alias resolution; [#734](https://github.com/nooga/let-go/pull/734) shadow warning (merged); [#781](https://github.com/nooga/let-go/pull/781) lazy var metadata (merged)

See also: [Execution Context](exec-context.md), [Concurrency Model](concurrency-model.md), [Runtime Image](runtime-image.md), [let-go](../entities/let-go.md)
