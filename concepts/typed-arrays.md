---
type: Concept
category: concept
title: "Typed Arrays"
description: "vm.TypedArray, the mutable Go-slice-backed array behind aget/aset: its one-slice-per-kind layout, the [:array K] lattice kind that lets AOT lowering index it natively, and the VM's AGET/ASET opcodes."
tags: [runtime, vm, compiler, go]
resource: "https://github.com/nooga/let-go/blob/main/pkg/vm/typed_array.go"
sources:
  - "repo: nooga/let-go pkg/vm/typed_array.go, pkg/rt/core/ir/lattice.lg, pkg/rt/lang.go @ a044ead1, 2026-09-17"
  - "lg scripts/lg-compile on an aget/aset kernel @ 9172aa24, 2026-09-15"
  - "pr: nooga/let-go#821 (typed-array backing slices preserved at the reflection boundary), #778 (collections cross the Go boundary as native values); issue #358 (native homogeneous collections, open), 2026-09-17"
  - "repo: nooga/let-go pkg/vm/typed_array.go, pkg/vm/vm.go, pkg/rt/core/ir/lattice.lg, pkg/rt/core/ir/lower_go.lg @ 8673d88a, 2026-10-17"
  - "lg scripts/lg-compile on a ^doubles sum-arr kernel, lg built @ 8673d88a, 2026-10-17"
  - "pr: nooga/let-go#1057 (lattice array kind and native accessors, closes #1055), #1058 (OP_AGET/OP_ASET, fixes #1045), #1060 (IR builtin ops for qualified core heads), merged 2026-10-17"
created: "2026-09-17"
updated: "2026-10-17"
status: stable
---

# Typed Arrays

let-go has mutable, element-typed arrays alongside the persistent collections:
`byte-array`, `int-array`, `long-array`, `float-array`, `double-array` and
`object-array`, read and written with `aget`/`aset` and sized with
`alength`/`aclone`. Unlike a vector, an array is backed by a real Go slice and
mutates in place. Since #1057 the [type lattice](type-inference.md) can name an
array's element kind, so a numeric kernel written against a hinted array lowers
under [AOT](go-backend.md) to a native slice access instead of a boxed call, and
since #1058 the bytecode VM has dedicated `AGET`/`ASET` opcodes for the
interpreted path.

## The representation

`vm.TypedArray` is a kind tag plus one typed slice per kind, of which exactly
one is live:

```go
type TypedArray struct {
	kind   ArrayKind
	bytes  []byte
	ints   []int64
	floats []float64
	objs   []Value
}
```

Six constructors map onto four kinds: `float-array` is an alias for
`double-array`, and `int-array` and `long-array` both land on `[]int64`. Each
kind coerces on write, so `aset` on a `byte-array` truncates to a byte and on a
`double-array` widens an int to a float.

Before #1057 the slice sat in a single `data any` field, and every access paid
an interface assertion. The split exists for the typed accessors lowered code
calls: `AtFloat64`/`SetFloat64`, `AtInt64`/`SetInt64`, `AtByte`/`SetByte` and
`AtValue`/`SetValue`. Each is one unsigned bounds compare and the access, with
error construction in a cold path, so each stays under the Go inliner's budget
of 80; with the assertion it cost 88. The kind check comes free: a wrong-kind
array finds its slice for that kind nil, fails the bounds compare, and the cold
path reports `double-array expected, got int-array`.

```go
func (a *TypedArray) AtFloat64(i int64) (float64, error) {
	if uint64(i) >= uint64(len(a.floats)) {
		return 0, a.accessError(i, ArrayFloat)
	}
	return a.floats[i], nil
}
```

The generic `Get`/`Set` still dispatch on the kind and box, and `Unbox()` still
returns the active slice. At the Go interop boundary the backing slice survives
rather than being copied: #821 made a compatible `[]byte`/`[]int64`/`[]float64`
cross as the same slice, so a host that writes into it is visible to let-go and
vice versa.

## The lattice kind

`[:array K]`, for K in `:byte :int :float :object`, mirrors `vm.ArrayKind`
(`pkg/rt/core/ir/lattice.lg`). The kind is **declared, never inferred from the
elements**, which is what makes arrays the tractable half of
[#358](https://github.com/nooga/let-go/issues/358):

- `typeinfer` types the six constructors, with `long-array` and `float-array`
  landing on the 64-bit kinds they construct.
- A parameter hint `^doubles`, `^floats`, `^longs`, `^ints`, `^bytes` or
  `^objects` declares the kind on a param, next to `^double`/`^long`.
- `aget` types as the element kind, `alength` as `:int`, `aset` as its value,
  and `aclone` as its argument.

Like `:dtype` it is non-maskable and survives the threaded state as a keyword
fact. Joins are strict: two different array kinds, or an array against
anything else, join to `:any`.

## What the lowering does with an array

Every array kind lowers to the Go type `*vm.TypedArray`. It implements
`vm.Value`, so an array local boxes by interface conversion, and lowered and
interpreted code share the same backing store. A kernel written with a hint:

```clojure
(defn sum-arr [^doubles a n]
  (loop [i 0 s 0.0]
    (if (>= i n) s (recur (inc i) (+ s (aget a i))))))
```

lowers to a function that takes the array as `*vm.TypedArray`, keeps `i` and
`s` native, and reads each element through the typed accessor (excerpt of
`lg scripts/lg-compile` output):

```go
func SumArr(ec *vm.ExecContext, arg0 *vm.TypedArray, arg1 int64) (float64, error) {
	...
	for {
		...
			if rt.NativePrimsIntact() {
				arg__1, callErr = arg0.AtFloat64(i)
				...
			} else {
				tb16, callErr = ec.Invoke2(rt.CachedVarFnEC(ec, &__v_clojure_core_aget, "clojure.core", "aget"), arg0, vm.Int(i))
				...
			}
			i = i + 1
			s = s + arg__1
			continue
	...
```

As with other [native primitives](native-primitives.md), the typed access sits
behind `rt.NativePrimsIntact()`, with the trampoline through the `aget` var as
the other branch; `NativePrimsIntact` inlines to one atomic load since #1057. Before #1057 the
same kernel called `rt.CoreAgetf(arg0, vm.Int(i))` on every access, boxing the
index and the element and running the accumulator on `rt.AddValue`. On the
PR's indicative runs (three runs on one machine, not ratchet results) the loop
went from roughly 30 times slower than hand-written Go over `[]float64` to
within a few percent of it.

Calls carry the kind too. The Go spec `*vm.TypedArray` does not say which kind,
so direct-call registry entries record lattice `:param-types` beside their Go
`:param-specs`:

- a proven array of the matching kind passes straight through;
- a different kind, or a proven non-array, bails that call to the trampoline,
  which is what bytecode does (the hint is ignored there, and `aget` works on
  any array);
- an unproven `vm.Value` argument gets the scalar guard's shape with
  `&& tg.Kind() == vm.ArrayFloat` in the condition.

A self-recursive function whose `recur` passes a different or unproven array
kind into a hinted param does not lower natively; it is dropped from the
direct-call registry and its callers reach it through its var.

## The interpreted path

Under the bytecode VM, `(aget a i)` compiles to `OP_AGET` and `(aset a i v)` to
`OP_ASET` (#1058), in the same shape as `OP_ADD`: assert `*vm.TypedArray` and
`Int`, bounds-check, index the typed slice. Every other input produces the
error the `clojure.core` fn would, with the same text, so a program cannot tell
which path ran. They are emitted only for those exact arities, and, like every
fast opcode, only when the head resolves to the `clojure.core` var itself (see
[stack VM](stack-vm.md)). Binding is at compile time: redefining `aget` after a
caller compiled does not reach the opcode, the existing policy for `+`.

On the same `sum-arr` kernel the opcodes took the VM from roughly 300 to 200
ms per rep (#1058's measurement, under load). What remains in that profile is
operand shuffling and `Float` boxing, which needs a frame-level change rather
than another opcode.

## Where it stops

- **A boxed index.** The accessor needs a native `int64` index; a `vm.Value`
  index keeps the boxed `rt.CoreAgetf` path.
- **Nested access.** `(aget a i j)` and anything else that does not line up
  (unknown kind, mismatched index) falls through to the generic path, in both
  engines.
- **`*ir-compile*` bytecode.** That path builds bytecode from IR ops, and `aget`
  has no IR op, so it emits a call rather than `OP_AGET`.
- **Hoisting.** Not done, and not needed: once the accessors inline, a
  per-access and a hoisted form time the same.
- **Other collections.** Vectors, transients and strings, whose element type
  would have to be inferred rather than declared, remain the open half of
  [#358](https://github.com/nooga/let-go/issues/358).

## Citations

**Resource:** [pkg/vm/typed_array.go](https://github.com/nooga/let-go/blob/main/pkg/vm/typed_array.go): the struct, constructors, and the typed accessors  
**Related:**
- [pkg/rt/core/ir/lattice.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lattice.lg): `array-type?`, `array-elem-kinds`, the join rule
- [pkg/rt/core/ir/lower_go.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg): `array-intrinsic-call-stmts`, `array-accessors`, the kind guard on direct calls, `recur-fn-arg-expr`
- [pkg/vm/vm.go](https://github.com/nooga/let-go/blob/main/pkg/vm/vm.go): `OP_AGET`, `OP_ASET`
- PRs and issues: [#1057](https://github.com/nooga/let-go/pull/1057), [#1058](https://github.com/nooga/let-go/pull/1058), [#1055](https://github.com/nooga/let-go/issues/1055), [#1045](https://github.com/nooga/let-go/issues/1045), [#821](https://github.com/nooga/let-go/pull/821), [#358](https://github.com/nooga/let-go/issues/358)

See also: [Go Backend](go-backend.md), [Type Inference](type-inference.md), [Stack VM](stack-vm.md), [Value Representation](value-representation.md)
