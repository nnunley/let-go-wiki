---
type: Concept
category: concept
title: "Namespaces and Vars"
description: "How names resolve in let-go: the Namespace's five maps and its lookup order, the Var's lock-free root and its two binding chains, refer and alias semantics including the core short-name aliases, the guarded-root fast path for native primitives, and the core-shadow warning (silent until #734)."
tags: [runtime, vm, clojure, compiler]
resource: "https://github.com/nooga/let-go/blob/main/pkg/vm/namespace.go"
sources:
  - "repo: nooga/let-go pkg/vm/{namespace,var,binding_stack,root_bindings}.go, pkg/rt/lang.go (nsAliases, LookupOrRegisterNSNoLoad), pkg/rt/core/core.lg (ns macro) @ 0911118, 2026-09-05"
  - "repo: nooga/let-go pkg/vm/{namespace,var}.go, pkg/rt/lang.go (nsAliases, referBaselines), pkg/rt/host_jvm_statics.go (referStaticNamespaces), pkg/rt/native_prims_lifecycle.go (NativePrimsIntact), pkg/rt/core/ir/lower_go.lg (rt.NativePrimsIntact guards), pkg/rt/core/edn.lg, pkg/rt/core/core.lg (ns macro), pkg/rt/golower_runtime.go (attachVarNSMeta), pkg/rt/native_direct_install.go (native-prims-intact?), pkg/bytecode/tags.go (TagDefMetaPairs) @ b82588292b, 2026-10-19"
  - "pr: nooga/let-go#974 (host-class namespaces refer clojure.core, merged 2026-10-06 as ed1258f10), #1020 (Intern keeps the existing Var, merged 2026-10-09 as 986f9503c), #1057 (typed-array accessors under the same guard, merged 2026-10-17 as faa26aea2), #863 (clojure.test port, namespace metadata and :ns attachment, merged 2026-09-18 as cffc09e10), 2026-10-19"
  - "pr: nooga/let-go#548 (alias before core shortcut), #610 (alias guard by name), #734 (core-shadow warning, merged 2026-09-06 as 928c217), #781 (lazy var metadata, merged 2026-09-06 as b0397f6), 2026-09-05"
  - "repo: nooga/let-go pkg/vm/namespace.go @ ee55803 (re-verified for #734/#781), 2026-09-06"
  - "lg -e transcripts on lg 1.12.3-0.20260904132133 (0911118), 2026-09-05"
  - "run: lg dev (b825882) at nooga/let-go b82588292b, 2026-10-20 (core-shadow warning and (meta #'map) output)"
created: "2026-09-05"
updated: "2026-10-19"
status: stable
---

# Namespaces and Vars

A var is the unit of definition and the boundary every [compile path](compile-paths.md) agrees on: bytecode, IR-compiled, and Go-lowered code all resolve a name to a `*vm.Var` and read its root. A namespace is the table that resolves the name. Both live in `pkg/vm`, and the [execution context](exec-context.md) owns the dynamic bindings that used to live on the var.

## Namespace

`vm.Namespace` is a name plus five maps behind one `RWMutex`: `registry` (the vars this namespace owns), `refers` (vars visible unqualified from other namespaces), `aliases` (`(:require [x :as y])`), `excludes` (names kept out of the `clojure.core` auto-refer), and `unmapped` (names removed with `ns-unmap`, hidden from refers too). A sixth field, the namespace metadata, is not a map of symbols: `Meta()` and `AlterMeta()` read and replace it under the same lock, and `AlterMeta` runs its function outside the lock (`pkg/vm/namespace.go`, added with the `clojure.test` port, #863). The governing invariant is that no code holds one namespace's lock while taking another's, so cross-namespace reads snapshot or use the target's own brief accessors and the lock graph has no cycles.

### Lookup order

`Lookup` takes a symbol and follows Clojure's precedence:

1. **Unqualified**: the namespace's own var, then explicit refers (`:refer [syms]`, `:refer :all`, `use`), then the auto-referred baselines (`clojure.core`, and the lg baselines `let-go.core` and `let-go.types`) only when no explicit refer provides the name. An explicit refer therefore shadows them. Baselines are the namespaces `isBaselineNS` recognises. Every namespace `pkg/rt` creates gets the `clojure.core` refer, except host-class namespaces, which get it from `referStaticNamespaces` (see below). `referBaselines` (`pkg/rt/lang.go`) adds the lg baselines to it, except that `clojure.core` itself gets none.
2. **Alias-qualified** (`s/join`): the aliased namespace's own var, then that namespace's refers. An alias may point at a placeholder created before its source finished loading; on a miss the lookup re-reads the registry by the target's canonical name through the `nsLookup` hook (which does not invoke the loader), caches the result on the alias, and retries.
3. **Fully qualified**: the global namespace registry, via the `nsLookup` hook `pkg/rt` installs.

Privacy hides a private var from an alias-qualified reference, and from a fully qualified reference made outside its own namespace; a fully qualified reference from inside the owning namespace still resolves, so a macro can expand to a call to its own private helper. Refers skip private vars. `LookupIncludingPrivate` backs the `var` special form, so `#'ns/sym` reaches a private var in any namespace, as in Clojure.

Host-class namespaces (`Float`, `Long`, `Math`, and so on) are created from Go by `defStaticNS` (`pkg/rt/host_jvm_statics.go`). They receive their `clojure.core` and baseline refers only after the host installers have filled them, through `referStaticNamespaces`, which `installClojureCompatAliases` calls last. Refers added earlier would print a shadow warning for every member named like a core var, so this ordering keeps startup silent. That is #974: before it, `(in-ns 'Float)` followed by `(inc 1)` failed to resolve.

Transcript from 0911118, not re-run at b82588292b:

```
$ lg -e "(do (require '[clojure.string :as core]) (core/join \",\" [1 2]))"
"1,2"
```

That transcript is #548's regression: the compiler used to short-circuit any symbol whose namespace part was literally `core` to `clojure.core` before consulting aliases, so `core/join` failed to resolve. Aliases now win, and the core shortcut remains only as a fallback for `(ns ...)` expansion before refers exist. #610 fixed the sibling guard: `Namespace.Alias` warns when an alias is repointed to a different namespace, and it compares namespace names rather than pointers, because two loads of the same namespace can present distinct pointers. Re-aliasing to the same name is silent.

### Short names for the standard namespaces

The canonical name of `clojure.core` is `core`. `pkg/rt` keeps a table (`nsAliases`, `pkg/rt/lang.go`) mapping `clojure.core`, `clojure.test`, `clojure.string`, `clojure.set`, `clojure.walk`, `clojure.edn`, `clojure.zip`, `clojure.data`, and `clojure.test.tap` to `core`, `test`, `string`, `set`, `walk`, `edn`, `zip`, `data`, and `test.tap`; both names resolve to the same `*Namespace`. `resolveNSAlias` applies the table, and the registry lookups (`LookupNS`, `DefNSBare`, `LookupOrRegisterNSNoLoad`) call it before touching the registry, which matters for the generated [primitive registrar](native-primitives.md): it registers under `"clojure.core"`, and without canonicalisation it would create a second, invisible namespace. The short name is what the runtime prints (transcript from 0911118, not re-run at b82588292b):

```
$ lg -e "(resolve 'inc)"
#'core/inc
$ lg -e "(find-ns 'clojure.string)"
<ns string>
```

### The `ns` macro

`ns` is a macro in `core.lg`. It strips a metadata wrapper (`with-meta`) from the namespace symbol, and drops a docstring or attribute map from the body before the forms are emitted. It hoists `(:refer-clojure :exclude [...])` into `exclude-in-current-ns` before any body form so the shadow check sees it. A vector `:require` entry expands to `require` (load without referring), then `core/alias` for `:as`, `core/refer` for `:refer :all`, `core/refer-list` for `:refer [syms]`, and a rename step that defs each renamed name to the referred var. A bare-symbol `:require` entry expands to `use` instead, which refers every public. Loading before referring is deliberate for the vector form: `use` refers everything, which would leak every public of an `:as`-aliased library into the unqualified namespace.

### The shadow warning

`warnOnCoreShadow` prints Clojure's `WARNING: x already refers to: #'clojure.core/x`, which at `b82588292b` ends with ` in namespace: user, being replaced by: #'user/x` when a definition shadows a name referred in from core, with guards for core itself, `:exclude`, unmapped names, and a suppression flag. Both intern paths call it: `Def`, the Go-side path, and `LookupOrAdd`, which the `def` special form uses. Until #734 (merged 2026-09-06, 928c217) only `Def` checked, so the warning had never fired for user code. The transcript below is from 0911118, before the fix:

```
$ lg -e '(do (def inc 5) inc)'
5
```

No warning was printed. #734 factored the check into `warnOnCoreShadow`, calls it from both intern paths, matches Clojure JVM in warning only on shadow-of-refer (a namespace that never referred the name stays silent), and declares the one intentional shadow it uncovered (`edn/read-string`, `pkg/rt/core/edn.lg`) with `:refer-clojure :exclude`. The check also skips a core var that is private, and a name the namespace already defines locally, so only the first definition warns.

The two interning methods differ in what they do to an existing Var. `Def` always creates a new Var and replaces the registry entry, so code compiled against the old Var keeps the old one. `Namespace.Intern`, the Go-side path embedders use, keeps the existing Var and sets its root, so compiled code sees the new value. `Intern` goes through `LookupOrAdd`, which rechecks the registry under the write lock, so concurrent first-time calls share one Var (#1020, `pkg/vm/namespace.go`).

## Var

`vm.Var` holds the root binding in an `atomic.Pointer`, so `Deref`, the hottest var operation, is a lock-free load. Around it: the owning namespace and name, metadata and watches behind a mutex, an atomic `isDynamic` flag (read on the hot path while a concurrent `binding` may set it), a private flag, and two things worth explaining.

### Two binding chains

Dynamic bindings no longer live on the var. Each [`ExecContext`](exec-context.md) owns a `bindingStack`: a persistent stack of immutable `(var, value)` frames behind an atomic head. A `binding` pushes a frame; the topmost frame for a var is its current value and the frames beneath are the shadowed outer bindings. Readers walk the chain from an atomically loaded head without locking, and a child context shares its parent's chain by pointer, which is how bindings convey into `future` and `go` blocks (see [concurrency model](concurrency-model.md)). The root context keeps a second, per-var chain (`rootBind`) for bindings established outside any child context, plus a registry of vars with a live root binding so a snapshot can enumerate them without walking anything on the deref path.

Transcripts from 0911118, not re-run at b82588292b:

```
$ lg -e "(do (def ^:dynamic *x* 1) (defn f [] *x*) [(f) (binding [*x* 2] (f)) (f)])"
[1 2 1]
$ lg -e "(do (defn g [] 1) [(with-redefs [g (fn [] 2)] (g)) (g)])"
[2 1]
$ lg -e "(do (def y 1) (alter-var-root #'y inc) y)"
2
```

### Guarded roots

Lowered Go code may call a native primitive directly instead of dereferencing its var, which is only correct while the var still holds the native. `GuardRoot` records a var's canonical root, `GuardDeviated` says whether the current root differs, and `SetRoot` keeps a process-wide deviation counter (`GuardedRootsIntact`, one atomic load) that any `with-redefs`, `alter-var-root`, or re-`def` of a guarded var moves off zero and restoring the root moves back. Lowered call sites consult the counter. An earlier version of this section said the only reader was the `rt/native-prims-intact?` diagnostic; that was wrong at `0911118`, where `pkg/rt/core/ir/lower_go.lg` (around line 1956) already emitted the guard. At `b82588292b` the lowering in `pkg/rt/core/ir/lower_go.lg` guards each native-module call with `rt.NativePrimsIntact()`, and #1057 added the typed-array accessors under the same guard, a wrapper over `vm.GuardedRootsIntact` in `pkg/rt/native_prims_lifecycle.go`: the baked direct call runs while it returns true, and the var-dispatch trampoline, which re-reads the root, runs otherwise. Lowered let-go siblings (not `:native?`) keep an unguarded direct call. Generated primitives are guarded when they are bound (`defGeneratedPrimitive`), and `setPrimitiveRoot` rebinds an existing Var in place so compiled references keep the same Var. The `rt/native-prims-intact?` diagnostic reads the same value, and when it returns false `LG_GUARD_DEBUG` prints which guarded vars deviated. The switch that disables direct calls wholesale is `*direct-calls-disabled?*`, which the lowering checks at lowering time. See [native primitives](native-primitives.md) and [compile paths](compile-paths.md).

### Metadata

Vars defined from source carry `:line`, `:file`, and `:column`; embedded core vars report `<embedded:core>` as their file. `:arglists` is not attached to the embedded core's vars at `0911118`:

```
$ lg -e "(meta #'map)"
{:line 374 :file "<embedded:core>" :column 1}
```

That transcript is from `0911118`, before #863. At `b82588292b` the map also carries `:name` and `:ns`, the namespace object. Measured at `b82588292b`, 2026-10-20 (run: lg dev (b825882) at nooga/let-go b82588292b, 2026-10-20):

```
$ lg -e "(meta #'map)"
{:line 402 :column 1 :file "<embedded:core>" :name map :ns <ns core>}
```

#781 (merged 2026-09-06, b0397f6) changed how that metadata is stored in the core bundle. Before it, `InitFromLGB` eagerly built a map for each of the 485 vars that carried metadata at 0911118; now the bundle writes the pairs under the version-1 `TagDefMetaPairs` tag (`pkg/bytecode/tags.go`; see [.lgb format](lgb-bytecode-format.md)) and `Var.Meta` builds the map on first access (`materializeMetaLocked` in `pkg/vm/var.go`). `MetaDeferred` reports whether a var is still in the pairs form. The `:ns` key (the namespace object) is attached by `attachVarNSMeta` when metadata is applied to a def (`pkg/rt/golower_runtime.go`). For bundle vars, which keep their pairs lazy, `materializeMetaLocked` adds `:ns` when the map is built, so building it does not force every var's map to exist at bundle init. #863 introduced this `:ns` attachment.

## Citations

**Resource:** [pkg/vm/namespace.go](https://github.com/nooga/let-go/blob/main/pkg/vm/namespace.go): the five maps, `lookup`, refer and alias precedence, `Def` and the shadow check  
**Related:**
- [pkg/vm/var.go](https://github.com/nooga/let-go/blob/main/pkg/vm/var.go): `Var`, the atomic root, `GuardRoot` and `GuardedRootsIntact`
- [pkg/vm/binding_stack.go](https://github.com/nooga/let-go/blob/main/pkg/vm/binding_stack.go) and [root_bindings.go](https://github.com/nooga/let-go/blob/main/pkg/vm/root_bindings.go): the two binding chains
- [pkg/rt/lang.go](https://github.com/nooga/let-go/blob/main/pkg/rt/lang.go): `nsAliases`, `LookupOrRegisterNSNoLoad`, `NameCoreNS`
- [pkg/rt/core/core.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg): the `ns` macro
- [pkg/rt/host_jvm_statics.go](https://github.com/nooga/let-go/blob/main/pkg/rt/host_jvm_statics.go): `defStaticNS` and `referStaticNamespaces`
- [pkg/rt/golower_runtime.go](https://github.com/nooga/let-go/blob/main/pkg/rt/golower_runtime.go): `attachVarNSMeta`, the `:ns` attachment
- [pkg/rt/native_direct_install.go](https://github.com/nooga/let-go/blob/main/pkg/rt/native_direct_install.go): the `native-prims-intact?` diagnostic
- [pkg/rt/native_prims_lifecycle.go](https://github.com/nooga/let-go/blob/main/pkg/rt/native_prims_lifecycle.go): `NativePrimsIntact`, `defGeneratedPrimitive`, `setPrimitiveRoot`
- [pkg/rt/core/ir/lower_go.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg): the `rt.NativePrimsIntact()` guard on lowered native call sites
- PRs: [#548](https://github.com/nooga/let-go/pull/548), [#610](https://github.com/nooga/let-go/pull/610) alias resolution; [#734](https://github.com/nooga/let-go/pull/734) shadow warning (merged); [#781](https://github.com/nooga/let-go/pull/781) lazy var metadata (merged); [#863](https://github.com/nooga/let-go/pull/863) clojure.test port, namespace metadata and `:ns` attachment; [#974](https://github.com/nooga/let-go/pull/974) host-class namespaces refer `clojure.core`; [#1020](https://github.com/nooga/let-go/pull/1020) `Intern` keeps the existing Var

See also: [Execution Context](exec-context.md), [Concurrency Model](concurrency-model.md), [Runtime Image](runtime-image.md), [let-go](../entities/let-go.md)
